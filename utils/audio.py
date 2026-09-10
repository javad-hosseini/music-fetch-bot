import logging
import requests
from pathlib import Path
from typing import Optional

from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT, TDRC, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from services.base import TrackInfo
import config

logger = logging.getLogger(__name__)


def _fetch_cover(url: Optional[str]) -> Optional[bytes]:
    """Safely download album cover art image bytes."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=config.NETWORK_TIMEOUT)
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception as e:
        logger.warning(f"Could not fetch cover art: {e}")
    return None


def apply_mp3_metadata(file_path: Path, track: TrackInfo) -> None:
    """Apply ID3v2.3 tags to an MP3 file."""
    try:
        audio = MP3(file_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
    except ID3NoHeaderError:
        audio = MP3(file_path)
        audio.add_tags()

    if track.title:
        audio.tags["TIT2"] = TIT2(encoding=3, text=str(track.title))

    if track.artist:
        audio.tags["TPE1"] = TPE1(encoding=3, text=str(track.artist))

    if track.album:
        audio.tags["TALB"] = TALB(encoding=3, text=str(track.album))

    if track.year:
        audio.tags["TDRC"] = TDRC(encoding=3, text=str(track.year))

    if track.lyrics:
        audio.tags["USLT"] = USLT(
            encoding=3,
            lang="eng",
            desc="Lyrics",
            text=str(track.lyrics)
        )

    cover_data = _fetch_cover(track.cover_url)
    if cover_data:
        audio.tags["APIC"] = APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,  # Front cover
            desc="Cover",
            data=cover_data
        )

    audio.save(v2_version=3)


def apply_m4a_metadata(file_path: Path, track: TrackInfo) -> None:
    """Apply MP4/M4A metadata tags."""
    audio = MP4(file_path)

    if track.title:
        audio["\xa9nam"] = str(track.title)

    if track.artist:
        audio["\xa9ART"] = str(track.artist)

    if track.album:
        audio["\xa9alb"] = str(track.album)

    if track.year:
        audio["\xa9day"] = str(track.year)

    if track.lyrics:
        audio["\xa9lyr"] = str(track.lyrics)

    cover_data = _fetch_cover(track.cover_url)
    if cover_data:
        audio["covr"] = [
            MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)
        ]

    audio.save()


def apply_metadata(file_path: Path, track: TrackInfo) -> None:
    """Detect file extension and apply appropriate metadata tags."""
    ext = file_path.suffix.lower()
    try:
        if ext == ".mp3":
            apply_mp3_metadata(file_path, track)
        elif ext in [".m4a", ".mp4"]:
            apply_m4a_metadata(file_path, track)
    except Exception as e:
        logger.error(f"Failed to apply metadata to {file_path.name}: {e}")
