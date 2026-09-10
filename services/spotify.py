import re
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

import requests
import yt_dlp

import config
from services.base import BaseMusicService, TrackInfo

logger = logging.getLogger(__name__)


class SpotifyService(BaseMusicService):
    """
    Music service provider for Spotify.
    Supports canonical URLs, localized URLs (open.spotify.com/intl-*/track/*),
    short URLs (spotify.link/*), and Spotify URIs (spotify:track:*).
    
    Extracts high-fidelity metadata (using Spotipy or zero-credential web embed extraction),
    and downloads matched audio streams via yt-dlp.
    """

    def __init__(self):
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        self._sp_client = None
        self._init_spotipy()

    def _init_spotipy(self) -> None:
        """Initialize spotipy client if credentials are configured."""
        if config.SPOTIPY_CLIENT_ID and config.SPOTIPY_CLIENT_SECRET:
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials

                auth_manager = SpotifyClientCredentials(
                    client_id=config.SPOTIPY_CLIENT_ID,
                    client_secret=config.SPOTIPY_CLIENT_SECRET,
                )
                self._sp_client = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Spotipy client authenticated with developer credentials.")
            except Exception as e:
                logger.warning(f"Failed to initialize Spotipy client: {e}")
                self._sp_client = None

    def can_handle(self, url: str) -> bool:
        """Check if URL belongs to Spotify."""
        if not url:
            return False
        patterns = [
            r"spotify\.com",
            r"spotify\.link",
            r"spotify:track:",
        ]
        return any(re.search(p, url, re.IGNORECASE) for p in patterns)

    def extract_track_id(self, raw_url: str) -> str:
        """Resolve shortlinks and extract the 22-character Spotify track ID."""
        url_match = re.search(r"https?://[^\s]+|spotify:track:[a-zA-Z0-9]+", raw_url)
        target = url_match.group(0) if url_match else raw_url

        # Follow shortlink redirects (e.g. spotify.link)
        if "spotify.link" in target:
            try:
                resp = requests.get(target, allow_redirects=True, headers=self._headers, timeout=config.NETWORK_TIMEOUT)
                target = resp.url
            except Exception as e:
                logger.warning(f"Could not resolve spotify.link redirect: {e}")

        # Match track ID from web URL or URI
        id_match = re.search(r"(?:/track/|spotify:track:)([a-zA-Z0-9]{22})", target)
        if id_match:
            return id_match.group(1)

        raise ValueError("Invalid Spotify track link or track ID could not be parsed.")

    def fetch_track(self, raw_url: str) -> TrackInfo:
        """Fetch metadata for a Spotify track."""
        track_id = self.extract_track_id(raw_url)
        canonical_share_url = f"https://open.spotify.com/track/{track_id}"

        # 1. Try Spotipy official API if credentials exist
        if self._sp_client:
            try:
                data = self._sp_client.track(track_id)
                title = data.get("name", "Unknown Title")
                artists = ", ".join(a["name"] for a in data.get("artists", [])) or "Unknown Artist"
                album_obj = data.get("album", {})
                album_name = album_obj.get("name")
                release_date = album_obj.get("release_date")
                year = release_date[:4] if release_date else None
                duration_ms = data.get("duration_ms", 0)
                duration_sec = duration_ms // 1000 if duration_ms else None

                images = album_obj.get("images", [])
                cover_url = images[0].get("url") if images else None

                return TrackInfo(
                    title=title,
                    artist=artists,
                    download_url=canonical_share_url,
                    album=album_name,
                    duration=duration_sec,
                    year=year,
                    format="mp3",
                    cover_url=cover_url,
                    lyrics=None,
                    source="Spotify",
                    share_url=canonical_share_url,
                )
            except Exception as e:
                logger.warning(f"Spotipy API fetch failed, falling back to web scraper: {e}")

        # 2. Fallback: Zero-credential metadata extraction via Spotify embed page
        return self._fetch_from_embed(track_id, canonical_share_url)

    def _fetch_from_embed(self, track_id: str, share_url: str) -> TrackInfo:
        """Zero-credential metadata scraping via Spotify embed and oEmbed endpoints."""
        embed_url = f"https://open.spotify.com/embed/track/{track_id}"
        resp = requests.get(embed_url, headers=self._headers, timeout=config.NETWORK_TIMEOUT)

        if resp.status_code == 200:
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', resp.text)
            if match:
                try:
                    payload = json.loads(match.group(1))
                    entity = payload.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
                    title = entity.get("name") or entity.get("title") or "Unknown Title"
                    artist_list = entity.get("artists", [])
                    artists = ", ".join(a.get("name") for a in artist_list if a.get("name")) or "Unknown Artist"
                    
                    duration_ms = entity.get("duration", 0)
                    duration_sec = duration_ms // 1000 if duration_ms else None

                    rel_date = entity.get("releaseDate", {}).get("isoString")
                    year = rel_date[:4] if rel_date else None

                    cover_url = None
                    images = entity.get("visualIdentity", {}).get("image", [])
                    if images and images[0].get("url"):
                        # Upgrade standard thumbnail to high-res 640x640 cover
                        cover_url = images[0]["url"].replace("00001e02", "0000b273")

                    return TrackInfo(
                        title=title,
                        artist=artists,
                        download_url=share_url,
                        album="Spotify",
                        duration=duration_sec,
                        year=year,
                        format="mp3",
                        cover_url=cover_url,
                        lyrics=None,
                        source="Spotify",
                        share_url=share_url,
                    )
                except Exception as e:
                    logger.warning(f"Failed parsing __NEXT_DATA__ from embed: {e}")

        # 3. Fallback to oEmbed if embed page fails
        oembed_url = f"https://open.spotify.com/oembed?url={share_url}"
        o_resp = requests.get(oembed_url, headers=self._headers, timeout=config.NETWORK_TIMEOUT)
        if o_resp.status_code == 200:
            data = o_resp.json()
            title = data.get("title", "Unknown Title")
            artist = data.get("author_name", "Spotify Artist")
            thumbnail = data.get("thumbnail_url")
            cover_url = thumbnail.replace("00001e02", "0000b273") if thumbnail else None

            return TrackInfo(
                title=title,
                artist=artist,
                download_url=share_url,
                album="Spotify",
                duration=None,
                year=None,
                format="mp3",
                cover_url=cover_url,
                lyrics=None,
                source="Spotify",
                share_url=share_url,
            )

        raise ValueError(f"Could not retrieve track metadata from Spotify (HTTP {resp.status_code}).")

    def download_track(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> int:
        """
        Download matched audio for a Spotify track using yt-dlp and YouTube Music/YouTube.
        """
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

        # Search candidates on YouTube / YouTube Music
        search_query = f"ytsearch3:{track.artist} - {track.title} audio"
        best_video_url = None

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as probe_ydl:
            try:
                info = probe_ydl.extract_info(search_query, download=False)
                entries = info.get("entries", []) if info else []
                if entries:
                    best_entry = entries[0]
                    # If target duration is known, pick entry with lowest duration discrepancy
                    if track.duration:
                        for entry in entries:
                            entry_duration = entry.get("duration")
                            if entry_duration and abs(entry_duration - track.duration) <= 12:
                                best_entry = entry
                                break
                    video_id = best_entry.get("id") or best_entry.get("url")
                    best_video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id and not video_id.startswith("http") else video_id
            except Exception as e:
                logger.warning(f"yt-dlp probe search error: {e}")

        # Fallback to direct search query if probe failed
        download_target = best_video_url or f"ytsearch1:{track.artist} - {track.title} audio"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([download_target])

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

        raise RuntimeError(f"Could not extract audio for '{track.artist} - {track.title}'.")
