import re
import time
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

import requests
import yt_dlp

import config
from services.base import BaseMusicService, TrackInfo
from utils.downloader import download_stream

logger = logging.getLogger(__name__)

FALLBACK_CLIENT_IDS = [
    "Pb72ranhoyt6gw7hM7TkzUItXlMWSNSo",
    "b0bS838Z1ZqG656rVv98KjYt6N3Z341k",
    "a3dd183a357981fe32829ee0e6c99824",
]


class SoundCloudService(BaseMusicService):
    """
    Music service provider for SoundCloud.
    Supports canonical URLs, mobile links (m.soundcloud.com), and short URLs (on.soundcloud.com).
    Extracts direct progressive MP3 streams when available, or routes HLS streams via yt-dlp.
    """

    def __init__(self):
        self._cached_client_id: Optional[str] = None
        self._client_id_expires_at: float = 0.0
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    def can_handle(self, url: str) -> bool:
        """Check if URL belongs to SoundCloud."""
        if not url:
            return False
        patterns = [
            r"https?://(?:www\.|m\.|on\.)?soundcloud\.com/[^\s]+",
            r"soundcloud\.com/[^\s]+",
        ]
        return any(re.search(p, url, re.IGNORECASE) for p in patterns)

    def get_client_id(self) -> str:
        """
        Get a valid SoundCloud client_id.
        Tries in-memory cached ID (12h TTL), then dynamic harvesting, then config / fallbacks.
        """
        now = time.time()
        if self._cached_client_id and now < self._client_id_expires_at:
            return self._cached_client_id

        # 1. Try config override if explicitly configured
        if config.SOUNDCLOUD_CLIENT_ID:
            self._cached_client_id = config.SOUNDCLOUD_CLIENT_ID
            self._client_id_expires_at = now + 86400  # 24h
            return self._cached_client_id

        # 2. Dynamic client_id harvesting from soundcloud.com asset scripts
        try:
            resp = requests.get("https://soundcloud.com", headers=self._headers, timeout=config.NETWORK_TIMEOUT)
            scripts = re.findall(r'https://a-v2\.sndcdn\.com/assets/[^"\'>]+\.js', resp.text)
            for script_url in reversed(scripts):
                try:
                    s_resp = requests.get(script_url, headers=self._headers, timeout=10)
                    matches = re.findall(r'client_id[:=]["\']?([a-zA-Z0-9]{32})["\']?', s_resp.text)
                    if matches:
                        harvested_id = matches[0]
                        self._cached_client_id = harvested_id
                        self._client_id_expires_at = now + (12 * 3600)  # 12 hours
                        logger.info(f"Dynamically harvested SoundCloud client_id: {harvested_id}")
                        return harvested_id
                except Exception as ex:
                    logger.debug(f"Failed inspecting script {script_url}: {ex}")
        except Exception as e:
            logger.warning(f"Error during dynamic SoundCloud client_id harvesting: {e}")

        # 3. Fallbacks
        for fallback_id in FALLBACK_CLIENT_IDS:
            self._cached_client_id = fallback_id
            self._client_id_expires_at = now + 3600
            return fallback_id

        raise ValueError("Could not obtain a SoundCloud client_id.")

    def resolve_url(self, raw_url: str) -> str:
        """Extract and resolve shortlinks (e.g. on.soundcloud.com) into canonical URLs."""
        url_match = re.search(r"https?://[^\s]+", raw_url)
        target = url_match.group(0) if url_match else raw_url
        if "on.soundcloud.com" in target:
            try:
                resp = requests.get(target, allow_redirects=True, headers=self._headers, timeout=config.NETWORK_TIMEOUT)
                return resp.url
            except Exception as e:
                logger.warning(f"Failed to follow on.soundcloud.com redirect: {e}")
        return target

    def fetch_track(self, raw_url: str) -> TrackInfo:
        """Fetch metadata and stream/download URL for a SoundCloud track."""
        canonical_url = self.resolve_url(raw_url)
        client_id = self.get_client_id()

        resolve_endpoint = f"https://api-v2.soundcloud.com/resolve?url={requests.utils.quote(canonical_url)}&client_id={client_id}"
        resp = requests.get(resolve_endpoint, headers=self._headers, timeout=config.NETWORK_TIMEOUT)

        if resp.status_code == 401:
            # Stale client_id, refresh and retry once
            self._cached_client_id = None
            client_id = self.get_client_id()
            resolve_endpoint = f"https://api-v2.soundcloud.com/resolve?url={requests.utils.quote(canonical_url)}&client_id={client_id}"
            resp = requests.get(resolve_endpoint, headers=self._headers, timeout=config.NETWORK_TIMEOUT)

        if resp.status_code != 200:
            raise ValueError(f"SoundCloud track not found or inaccessible (HTTP {resp.status_code}).")

        data = resp.json()
        kind = data.get("kind")
        if kind == "playlist":
            raise ValueError("Playlists/sets are not supported yet. Please provide a direct link to an individual track.")
        elif kind != "track":
            raise ValueError(f"Unsupported SoundCloud content type: {kind}")

        title = data.get("title") or "Unknown Title"
        user_info = data.get("user") or {}
        artist = user_info.get("username") or "SoundCloud Artist"

        # Album artwork: upgrade -large.jpg to -t500x500.jpg for high resolution
        raw_art = data.get("artwork_url") or user_info.get("avatar_url")
        cover_url = raw_art.replace("-large.", "-t500x500.") if raw_art else None

        duration_ms = data.get("duration", 0)
        duration_sec = duration_ms // 1000 if duration_ms else None

        created_at = data.get("created_at")
        year = str(created_at)[:4] if created_at else None

        permalink = data.get("permalink_url") or canonical_url
        plays = data.get("playback_count")
        likes = data.get("likes_count")

        # Inspect media transcodings
        transcodings: List[Dict[str, Any]] = data.get("media", {}).get("transcodings", [])
        download_url = ""

        # 1. Prefer progressive HTTP MP3 stream for direct chunk downloading
        for t in transcodings:
            fmt = t.get("format", {})
            if fmt.get("protocol") == "progressive" and "audio/mpeg" in fmt.get("mime_type", ""):
                stream_api_url = t.get("url")
                if stream_api_url:
                    try:
                        s_resp = requests.get(
                            f"{stream_api_url}?client_id={client_id}",
                            headers=self._headers,
                            timeout=config.NETWORK_TIMEOUT
                        )
                        if s_resp.status_code == 200:
                            s_data = s_resp.json()
                            direct_stream = s_data.get("url")
                            if direct_stream:
                                download_url = direct_stream
                                break
                    except Exception as e:
                        logger.warning(f"Error fetching progressive stream URL: {e}")

        # 2. Fallback: if no progressive stream, store canonical URL for yt-dlp HLS assembly
        if not download_url:
            download_url = permalink

        return TrackInfo(
            title=title,
            artist=artist,
            download_url=download_url,
            album="SoundCloud",
            duration=duration_sec,
            year=year,
            format="mp3",
            cover_url=cover_url,
            lyrics=data.get("description"),
            source="SoundCloud",
            share_url=permalink,
            plays=plays,
            likes=likes,
        )

    def download_track(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> int:
        """
        Download track. If download_url is a direct progressive stream, use standard HTTP streaming.
        If it requires HLS assembly, use yt-dlp.
        """
        # If it's a direct progressive media stream from SoundCloud CDN
        if "sndcdn.com" in track.download_url or "cf-media" in track.download_url:
            return download_stream(track.download_url, target_path, on_progress=on_progress)

        # Otherwise route through yt-dlp (handles HLS m3u8 streams and segment concatenation)
        target_stem = str(target_path.with_suffix(""))
        out_tmpl = f"{target_stem}.%(ext)s"

        def progress_hook(d):
            if d.get("status") == "downloading" and on_progress:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                percent = int((downloaded / total) * 100) if total > 0 else 0
                try:
                    on_progress(downloaded, total, percent)
                except Exception:
                    pass

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "ffmpeg_location": config.FFMPEG_PATH,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        # Source URL can be track share_url or track download_url
        source_url = track.share_url or track.download_url
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source_url])

        if target_path.exists():
            if on_progress:
                try:
                    size = target_path.stat().st_size
                    on_progress(size, size, 100)
                except Exception:
                    pass
            return target_path.stat().st_size

        candidate = Path(f"{target_stem}.mp3")
        if candidate.exists():
            if candidate != target_path:
                candidate.rename(target_path)
            return target_path.stat().st_size

        raise RuntimeError(f"yt-dlp finished but output file was not found at {target_path}")
