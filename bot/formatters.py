import html
from typing import Optional
from services.base import TrackInfo


def get_service_badge(source: Optional[str]) -> str:
    """Return an attractive service badge for a given source platform."""
    if not source:
        return "🎵 Music"
    lower = source.lower()
    if "radio javan" in lower or "rj" in lower:
        return "📻 Radio Javan"
    elif "soundcloud" in lower:
        return "☁️ SoundCloud"
    elif "spotify" in lower:
        return "🟢 Spotify"
    return f"📡 {source}"


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if not seconds or not isinstance(seconds, (int, float)):
        return "N/A"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    mins, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def format_progress_bar(
    percent: int,
    length: int = 10,
    downloaded_bytes: int = 0,
    total_bytes: int = 0,
) -> str:
    """
    Generate visual ASCII progress bar with size indicators:
    [████░░░░░░] 40% • 6.2 MB / 15.5 MB
    """
    percent = max(0, min(100, int(percent)))
    filled_len = int(length * percent // 100)
    bar = "█" * filled_len + "░" * (length - filled_len)

    if total_bytes > 0:
        dl_mb = downloaded_bytes / (1024 * 1024)
        tot_mb = total_bytes / (1024 * 1024)
        return f"[{bar}] {percent}% • {dl_mb:.1f} / {tot_mb:.1f} MB"
    elif downloaded_bytes > 0:
        dl_mb = downloaded_bytes / (1024 * 1024)
        return f"[{bar}] {percent}% • {dl_mb:.1f} MB"
    else:
        return f"[{bar}] {percent}%"


def format_caption(track: TrackInfo) -> str:
    """
    Builds safe HTML caption for Telegram audio message.
    Includes service badges, ID3 metadata fields, duration, and optional lyrics.
    Ensures all entities are escaped and caption stays within Telegram's 1024 character limit.
    """
    title = html.escape(track.title or "Unknown")
    artist = html.escape(track.artist or "Unknown")
    album = html.escape(track.album or "Single")
    duration_str = format_duration(track.duration)
    year = html.escape(str(track.year or "N/A"))
    source_badge = get_service_badge(track.source)

    base_caption = (
        f"🎵 <b>{title}</b>\n"
        f"👤 <b>Artist:</b> {artist}\n"
        f"💿 <b>Album:</b> {album}\n"
        f"⏱ <b>Duration:</b> {duration_str}\n"
        f"📅 <b>Year:</b> {year}\n"
        f"📡 <b>Source:</b> {source_badge}\n"
    )

    if track.plays or track.likes:
        stats_line = "📊 "
        if track.plays:
            stats_line += f"▶️ {html.escape(str(track.plays))}  "
        if track.likes:
            stats_line += f"👍 {html.escape(str(track.likes))}"
        base_caption += f"{stats_line}\n"

    # Handle lyrics with length limits (keeping total caption < 1024 characters)
    if track.lyrics:
        current_len = len(base_caption)
        # Allocate character budget for lyrics preview
        remaining_budget = max(0, 950 - current_len - 100)
        clean_lyrics = track.lyrics.strip()
        if len(clean_lyrics) > remaining_budget:
            preview_lyrics = clean_lyrics[:remaining_budget].strip() + "..."
        else:
            preview_lyrics = clean_lyrics

        escaped_lyrics = html.escape(preview_lyrics)
        base_caption += f"\n📝 <b>Lyrics:</b>\n<pre>{escaped_lyrics}</pre>\n"

    if track.share_url:
        base_caption += f"\n🔗 <a href='{html.escape(track.share_url)}'>Listen / Source Link</a>"

    return base_caption
