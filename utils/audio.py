import logging
import shutil
import subprocess
import requests
from pathlib import Path
from typing import Optional

from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT, TDRC, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from services.base import TrackInfo
import config

logger = logging.getLogger(__name__)


def convert_to_mp3(input_path: Path, output_path: Path, bitrate: str = "192k") -> Path:
    """
    Converts any audio file (M4A, AAC, OGG, WAV, etc.) to MP3 format using FFmpeg.
    Guarantees universal MP3 output across all services.
    """
    ffmpeg_bin = config.FFMPEG_PATH or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg executable not found. Cannot perform MP3 audio conversion.")

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", bitrate,
        str(output_path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        err_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise RuntimeError(f"FFmpeg MP3 conversion failed: {err_msg}")

    return output_path


def ensure_mp3(file_path: Path, bitrate: str = "192k") -> Path:
    """
    Verifies that the file at file_path is a valid MP3 file.
    If it is not an MP3 (e.g. M4A, AAC, Opus, OGG, or corrupt header),
    it converts the file to MP3 format using FFmpeg and returns the verified MP3 path.
    """
    if file_path.suffix.lower() == ".mp3":
        try:
            MP3(file_path)
            return file_path
        except Exception:
            logger.info(f"{file_path.name} lacks valid MP3 headers. Converting with FFmpeg...")

    temp_mp3 = file_path.with_name(f"converted_{file_path.stem}.mp3")
    convert_to_mp3(file_path, temp_mp3, bitrate=bitrate)

    target_mp3 = file_path.with_suffix(".mp3")
    if file_path.exists() and file_path != target_mp3:
        file_path.unlink(missing_ok=True)
    if temp_mp3.exists():
        temp_mp3.replace(target_mp3)
    return target_mp3


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
    """Detect file extension and apply appropriate metadata tags (strictly ID3 for MP3)."""
    ext = file_path.suffix.lower()
    try:
        if ext == ".mp3":
            apply_mp3_metadata(file_path, track)
        elif ext in [".m4a", ".mp4"]:
            apply_m4a_metadata(file_path, track)
        else:
            apply_mp3_metadata(file_path, track)
    except Exception as e:
        logger.error(f"Failed to apply metadata to {file_path.name}: {e}")
