"""
bot/keyboards.py - Inline keyboard builders for rich Telegram UI.
"""
import hashlib
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.base import TrackInfo

# Bounded in-memory store for interactive lyrics display
_LYRICS_CACHE = {}


def store_lyrics(title: str, artist: str, lyrics: str) -> str:
    """Cache lyrics for Telegram callback queries with bounded size."""
    key = hashlib.md5(f"{title}:{artist}".encode("utf-8", errors="ignore")).hexdigest()[:12]
    _LYRICS_CACHE[key] = {
        "title": title,
        "artist": artist,
        "lyrics": lyrics,
    }
    if len(_LYRICS_CACHE) > 500:
        first_key = next(iter(_LYRICS_CACHE))
        _LYRICS_CACHE.pop(first_key, None)
    return key


def get_cached_lyrics(key: str):
    """Retrieve cached lyrics payload by key."""
    return _LYRICS_CACHE.get(key)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Primary navigation keyboard shown on /start and main menu."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 Guide & Help", callback_data="ui_help"),
        InlineKeyboardButton("🎵 Supported Platforms", callback_data="ui_platforms"),
    )
    markup.add(
        InlineKeyboardButton("⚡ Bot Status", callback_data="ui_ping"),
        InlineKeyboardButton("ℹ️ About Bot", callback_data="ui_about"),
    )
    return markup


def platforms_menu_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for exploring supported platforms."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📻 Radio Javan", callback_data="ui_plat_rj"),
        InlineKeyboardButton("☁️ SoundCloud", callback_data="ui_plat_sc"),
    )
    markup.add(
        InlineKeyboardButton("🟢 Spotify", callback_data="ui_plat_sp"),
        InlineKeyboardButton("🔴 YouTube Music", callback_data="ui_plat_yt"),
    )
    markup.add(
        InlineKeyboardButton("🔙 Back to Main Menu", callback_data="ui_main"),
    )
    return markup


def platform_detail_keyboard() -> InlineKeyboardMarkup:
    """Navigation buttons when viewing a specific platform's link formats."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔙 Platforms List", callback_data="ui_platforms"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="ui_main"),
    )
    return markup


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Single back button to return to the main menu."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="ui_main"))
    return markup


def audio_action_keyboard(track: TrackInfo) -> InlineKeyboardMarkup:
    """Action buttons attached directly below delivered audio messages."""
    markup = InlineKeyboardMarkup(row_width=1)

    # Interactive full lyrics button
    if track.lyrics:
        lyr_id = store_lyrics(track.title or "Track", track.artist or "Artist", track.lyrics)
        markup.add(InlineKeyboardButton("📝 متن کامل ترانه (Full Lyrics)", callback_data=f"lyr_{lyr_id}"))

    # Direct source link
    if track.share_url:
        markup.add(InlineKeyboardButton("🔗 Listen on Source", url=str(track.share_url)))
    elif track.download_url and str(track.download_url).startswith("http"):
        markup.add(InlineKeyboardButton("🔗 Direct Link", url=str(track.download_url)))

    return markup


def error_keyboard() -> InlineKeyboardMarkup:
    """Actionable buttons when an error or unrecognized link is received."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎵 Supported Links", callback_data="ui_platforms"),
        InlineKeyboardButton("📖 Help Guide", callback_data="ui_help"),
    )
    return markup


def oversized_file_keyboard(direct_url: str) -> InlineKeyboardMarkup:
    """Buttons when audio exceeds Telegram's 50MB limit."""
    markup = InlineKeyboardMarkup(row_width=1)
    if direct_url and direct_url.startswith("http"):
        markup.add(InlineKeyboardButton("🌐 Download Directly (Browser)", url=direct_url))
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="ui_main"))
    return markup
