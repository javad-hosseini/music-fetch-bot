import os
import re
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs

import yt_dlp

import config
from services.base import BaseMusicService, TrackInfo
from utils.lyrics import fetch_lyrics, clean_query_term

logger = logging.getLogger(__name__)

ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

YOUTUBE_URL_REGEX = re.compile(
    r"https?://(?:(?:www\.|m\.|music\.)?youtube\.com/(?:watch\?v=|shorts/|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})",
    re.IGNORECASE,
)


def _is_valid_youtube_url(url: str) -> bool:
    """Validate that URL belongs strictly to trusted YouTube or YouTube Music domains."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        if hostname not in ALLOWED_YOUTUBE_HOSTS and not any(
            hostname.endswith("." + h) for h in ALLOWED_YOUTUBE_HOSTS
        ):
            return False
        return bool(YOUTUBE_URL_REGEX.search(url))
    except Exception:
        return False


def parse_title_artist(raw_title: str, uploader: str = "") -> Tuple[str, str]:
    """
    Intelligently split common YouTube titles (e.g. 'Adele - Hello (Official Video)')
    into clean (artist, title).
    """
    clean_raw = clean_query_term(raw_title)

    # Common delimiter pattern: "Artist - Title" or "Artist – Title" or "Artist: Title"
    match = re.split(r"\s+[-–—:|]\s+", clean_raw, maxsplit=1)
    if len(match) == 2:
        artist_candidate, title_candidate = match[0].strip(), match[1].strip()
        if artist_candidate and title_candidate:
            return clean_query_term(title_candidate), clean_query_term(artist_candidate)

    # Fallback to uploader as artist if available
    artist = clean_query_term(uploader.replace(" - Topic", "").strip()) or "YouTube"
    title = clean_raw
    return title, artist


class YouTubeMusicService(BaseMusicService):
    """
    Music service provider for YouTube and YouTube Music.
    Extracts high-fidelity audio streams and metadata via yt-dlp,
    fetches lyrics via Genius/LRCLIB, and outputs universal MP3s.
    """

    def can_handle(self, url: str) -> bool:
        """Return True if URL is a recognized YouTube or YouTube Music link."""
        if not url:
            return False
        match = re.search(r"https?://[^\s]+", url)
        target = match.group(0) if match else url.strip()
        return _is_valid_youtube_url(target)

    def extract_canonical_url(self, raw_url: str) -> Tuple[str, str, bool]:
        """
        Extract video ID, canonical URL, and boolean indicating if it's YouTube Music.
        """
        match = re.search(r"https?://[^\s]+", raw_url)
        target = match.group(0) if match else raw_url.strip()

        if not _is_valid_youtube_url(target):
            raise ValueError("Invalid YouTube or YouTube Music URL.")

        yt_match = YOUTUBE_URL_REGEX.search(target)
        if not yt_match:
            raise ValueError("Could not extract YouTube video ID from URL.")

        video_id = yt_match.group(1)
        is_music = "music.youtube.com" in target.lower()
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_id, canonical_url, is_music

    def fetch_track(self, url: str) -> TrackInfo:
        """
        Extract track metadata using yt-dlp and fetch lyrics.
        """
        video_id, canonical_url, is_music = self.extract_canonical_url(url)

        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": 15,
        }
        if config.PROXY_URL:
            ydl_opts["proxy"] = config.PROXY_URL

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(canonical_url, download=False)
            except Exception as e:
                logger.error(f"yt-dlp metadata extraction failed for {canonical_url}: {e}")
                raise RuntimeError(f"Failed to extract YouTube track info: {e}")

        if not info:
            raise RuntimeError("yt-dlp returned empty info for YouTube URL.")

        raw_title = info.get("title") or "Unknown Title"
        uploader = info.get("artist") or info.get("uploader") or info.get("channel") or ""

        # YouTube Music tracks often have explicit 'track' and 'artist' metadata
        if info.get("track"):
            title = info.get("track")
            artist = info.get("artist") or uploader
        else:
            title, artist = parse_title_artist(raw_title, uploader)

        album = info.get("album")
        duration = int(info.get("duration") or 0)
        year = None
        if info.get("release_year"):
            year = str(info.get("release_year"))
        elif info.get("upload_date") and len(info.get("upload_date")) >= 4:
            year = info.get("upload_date")[:4]

        # Best thumbnail
        thumbnail = info.get("thumbnail")
        if info.get("thumbnails"):
            thumbs = [t for t in info["thumbnails"] if t.get("url")]
            if thumbs:
                thumbnail = thumbs[-1]["url"]

        source_name = "YouTube Music" if is_music else "YouTube"

        # Fetch lyrics via multi-provider engine (Genius / LRCLIB)
        lyrics = None
        try:
            lyrics = fetch_lyrics(title, artist)
        except Exception as e:
            logger.debug(f"Lyrics fetching error for YouTube track: {e}")

        return TrackInfo(
            title=title,
            artist=artist,
            download_url=canonical_url,
            album=album,
            duration=duration,
            year=year,
            format="mp3",
            cover_url=thumbnail,
            lyrics=lyrics,
            source=source_name,
            share_url=canonical_url,
            plays=info.get("view_count"),
            likes=info.get("like_count"),
        )

    def download_track(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> int:
        """
        Download YouTube audio stream and convert to 192/320kbps MP3 via FFmpeg.
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

        ydl_opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "ffmpeg_location": config.FFMPEG_PATH,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 20,
            "retries": 3,
        }
        if config.PROXY_URL:
            ydl_opts["proxy"] = config.PROXY_URL

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ret_code = ydl.download([track.download_url])
            if ret_code != 0 and not target_path.exists():
                raise RuntimeError(f"yt-dlp download failed with exit code {ret_code}")

        # Ensure target file exists (sometimes yt-dlp saves with .mp3 directly)
        if not target_path.exists():
            mp3_candidate = Path(f"{target_stem}.mp3")
            if mp3_candidate.exists():
                mp3_candidate.rename(target_path)

        return target_path.stat().st_size if target_path.exists() else 0
