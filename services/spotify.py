import re
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from urllib.parse import urlparse
import requests
import yt_dlp

import config
from services.base import BaseMusicService, TrackInfo

logger = logging.getLogger(__name__)

ALLOWED_SPOTIFY_HOSTS = {
    "spotify.com",
    "open.spotify.com",
    "www.spotify.com",
    "spotify.link",
}


def _is_valid_spotify_url(url: str) -> bool:
    """Validate that URL belongs strictly to trusted Spotify domains or URI format."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if url.lower().startswith("spotify:track:"):
        return bool(re.match(r"^spotify:track:[a-zA-Z0-9]{22}$", url, re.IGNORECASE))
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        return (
            hostname in ALLOWED_SPOTIFY_HOSTS
            or hostname.endswith(".spotify.com")
            or hostname.endswith(".spotify.link")
        )
    except Exception:
        return False


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
        """Check if URL belongs strictly to Spotify."""
        if not url:
            return False
        match = re.search(r"https?://[^\s]+|spotify:track:[a-zA-Z0-9]+", url, re.IGNORECASE)
        candidate = match.group(0) if match else url.strip()
        return _is_valid_spotify_url(candidate)

    def extract_track_id(self, raw_url: str) -> str:
        """Resolve shortlinks and extract the 22-character Spotify track ID with SSRF protection."""
        url_match = re.search(r"https?://[^\s]+|spotify:track:[a-zA-Z0-9]+", raw_url)
        target = url_match.group(0) if url_match else raw_url.strip()

        if not _is_valid_spotify_url(target):
            raise ValueError("Invalid Spotify track link or track ID could not be parsed.")

        # Follow shortlink redirects only if domain is spotify.link
        try:
            parsed = urlparse(target)
            if (parsed.hostname or "").lower().endswith("spotify.link"):
                resp = requests.get(target, allow_redirects=True, headers=self._headers, timeout=config.NETWORK_TIMEOUT)
                if _is_valid_spotify_url(resp.url):
                    target = resp.url
                else:
                    logger.warning(f"Spotify shortlink redirected to non-Spotify domain: {resp.url}")
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

    def _try_radiojavan_fallback(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> bool:
        """
        Search Radio Javan for matching track and download directly.
        Provides a fast fallback for Persian and local music without requiring YouTube/proxy.
        """
        try:
            from radiojavanapi import Client
            from utils.downloader import download_stream
            from utils.audio import convert_to_mp3

            client = Client()
            clean_artists = [a.strip() for a in re.split(r"[,&/]+", track.artist) if a.strip()]
            first_artist = clean_artists[0] if clean_artists else track.artist

            queries = [
                f"{first_artist} {track.title}",
                f"{track.artist} {track.title}",
                track.title,
            ]

            norm_title = re.sub(r"[^\w]", "", track.title.lower())

            for q in queries:
                if not q.strip():
                    continue
                try:
                    res = client.search(q.strip())
                    songs = getattr(res, "songs", []) if res else []
                    for s in songs:
                        s_name = getattr(s, "name", None) or getattr(s, "title", "")
                        norm_s_name = re.sub(r"[^\w]", "", s_name.lower())
                        if norm_title and (norm_title in norm_s_name or norm_s_name in norm_title):
                            full_song = client.get_song_by_id(s.id)
                            if not full_song:
                                continue
                            dl_url = str(full_song.hq_link or full_song.lq_link or full_song.link or "")
                            if not dl_url:
                                continue

                            logger.info(f"Spotify fallback: Matched '{track.artist} - {track.title}' on Radio Javan (ID: {s.id})")
                            is_m4a = ".m4a" in dl_url.lower()
                            if is_m4a:
                                temp_m4a = target_path.with_suffix(".m4a")
                                try:
                                    download_stream(dl_url, temp_m4a, on_progress=on_progress)
                                    convert_to_mp3(temp_m4a, target_path)
                                    return target_path.exists()
                                finally:
                                    temp_m4a.unlink(missing_ok=True)
                            else:
                                download_stream(dl_url, target_path, on_progress=on_progress)
                                return target_path.exists()
                except Exception as ex:
                    logger.debug(f"Radio Javan fallback query '{q}' failed: {ex}")
        except Exception as e:
            logger.debug(f"Radio Javan fallback search error: {e}")

        return False

    def download_track(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> int:
        """
        Download matched audio for a Spotify track using yt-dlp (YouTube) or Radio Javan fallback.
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

        probe_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "socket_timeout": 5,
            "retries": 1,
        }
        if config.PROXY_URL:
            probe_opts["proxy"] = config.PROXY_URL

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
            "socket_timeout": 15,
            "retries": 2,
        }
        if config.PROXY_URL:
            ydl_opts["proxy"] = config.PROXY_URL

        # Candidate search queries for YouTube
        clean_artist_str = " ".join([a.strip() for a in re.split(r"[,&/]+", track.artist) if a.strip()])
        search_candidates = [
            f"ytsearch3:{clean_artist_str} - {track.title} audio",
            f"ytsearch3:{clean_artist_str} {track.title}",
            f"ytsearch3:{track.title} audio",
        ]

        best_video_url = None
        is_connection_error = False
        for sq in search_candidates:
            try:
                with yt_dlp.YoutubeDL(probe_opts) as probe_ydl:
                    info = probe_ydl.extract_info(sq, download=False)
                    entries = info.get("entries", []) if info else []
                    if entries:
                        best_entry = entries[0]
                        if track.duration:
                            for entry in entries:
                                entry_duration = entry.get("duration")
                                if entry_duration and abs(entry_duration - track.duration) <= 12:
                                    best_entry = entry
                                    break
                        video_id = best_entry.get("id") or best_entry.get("url")
                        best_video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id and not str(video_id).startswith("http") else video_id
                        if best_video_url:
                            break
            except Exception as e:
                logger.debug(f"yt-dlp probe error for '{sq}': {e}")
                err_str = str(e).lower()
                if "connection" in err_str or "10061" in err_str or "refused" in err_str or "timed out" in err_str:
                    is_connection_error = True
                    break

        # If YouTube search failed or connection blocked, try Radio Javan fallback immediately
        if not best_video_url:
            logger.info(f"YouTube probe unavailable/empty for '{track.artist} - {track.title}', trying Radio Javan fallback...")
            if self._try_radiojavan_fallback(track, target_path, on_progress):
                if target_path.exists():
                    if on_progress:
                        try:
                            size = target_path.stat().st_size
                            on_progress(size, size, 100)
                        except Exception:
                            pass
                    return target_path.stat().st_size

        download_target = best_video_url or (None if is_connection_error else search_candidates[0])
        if download_target:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([download_target])
            except Exception as dl_err:
                logger.warning(f"yt-dlp download failed: {dl_err}")

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

        # Fallback to Radio Javan if YouTube download did not produce a file
        logger.info(f"YouTube download did not produce file for '{track.artist} - {track.title}', attempting Radio Javan fallback...")
        if self._try_radiojavan_fallback(track, target_path, on_progress):
            if target_path.exists():
                if on_progress:
                    try:
                        size = target_path.stat().st_size
                        on_progress(size, size, 100)
                    except Exception:
                        pass
                return target_path.stat().st_size

        proxy_hint = ""
        if not config.PROXY_URL:
            proxy_hint = " If YouTube is restricted on your network, set PROXY_URL in .env (e.g. PROXY_URL=http://127.0.0.1:7890) or enable your VPN."

        raise RuntimeError(f"Could not extract audio for '{track.artist} - {track.title}'.{proxy_hint}")
