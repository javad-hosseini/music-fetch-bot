"""
bot/keyboards.py - Inline keyboard builders for rich Telegram UI.
"""
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.base import TrackInfo


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
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("📻 Radio Javan", callback_data="ui_plat_rj"),
        InlineKeyboardButton("☁️ SoundCloud", callback_data="ui_plat_sc"),
        InlineKeyboardButton("🟢 Spotify", callback_data="ui_plat_sp"),
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
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []

    # Direct source link
    if track.share_url:
        buttons.append(InlineKeyboardButton("🔗 Listen on Source", url=track.share_url))
    elif track.download_url and track.download_url.startswith("http"):
        buttons.append(InlineKeyboardButton("🔗 Direct Link", url=track.download_url))

    if buttons:
        markup.add(*buttons)

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
