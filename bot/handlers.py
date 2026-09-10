import os
import re
import time
import logging
from telebot import TeleBot
from telebot.types import Message, CallbackQuery

import config
from services import find_service, SERVICES
from utils.filesystem import safe_filename, temporary_work_dir
from utils.audio import apply_metadata
from bot.formatters import format_caption, format_progress_bar
from bot.keyboards import (
    main_menu_keyboard,
    platforms_menu_keyboard,
    platform_detail_keyboard,
    back_to_main_keyboard,
    audio_action_keyboard,
    error_keyboard,
    oversized_file_keyboard,
)

logger = logging.getLogger(__name__)

TEXT_START = (
    "👋 <b>Welcome to Music Downloader Bot!</b>\n\n"
    "Send me any music or podcast link from our supported platforms, and I'll download "
    "it for you with full ID3 tags and high-resolution album artwork.\n\n"
    "📌 <b>Supported Services:</b>\n"
    "• <b>Radio Javan</b> (Songs & Podcasts)\n"
    "• <b>SoundCloud</b> (Tracks)\n"
    "• <b>Spotify</b> (Tracks)\n\n"
    "💡 <i>Tap a button below to explore features or check bot status:</i>"
)

TEXT_HELP = (
    "📖 <b>Bot Commands & Usage Guide</b>\n\n"
    "Simply paste a link into this chat! The bot automatically detects the platform and "
    "processes the audio.\n\n"
    "<b>Available Commands:</b>\n"
    "• /start — Launch the bot & main navigation menu\n"
    "• /help or /commands — Open this help & usage guide\n"
    "• /platforms — View supported platforms & link formats\n"
    "• /ping — Check bot response latency & health\n"
    "• /about — Version, licenses & repository details\n\n"
    "💡 <i>Select a platform below to see supported link formats:</i>"
)

TEXT_PLATFORMS = (
    "🎵 <b>Supported Music Platforms</b>\n\n"
    "The bot currently supports 3 major music platforms:\n\n"
    "1. 📻 <b>Radio Javan</b> — Full song and podcast downloads with ID3v2 tags.\n"
    "2. ☁️ <b>SoundCloud</b> — Progressive & HLS streams with 500x500 album art.\n"
    "3. 🟢 <b>Spotify</b> — Official metadata & 640x640 artwork matched with audio.\n\n"
    "<i>Tap a platform below to view specific URL examples:</i>"
)

TEXT_PLAT_RJ = (
    "📻 <b>Radio Javan Support</b>\n\n"
    "<b>Supported Link Formats:</b>\n"
    "• Songs: <code>https://www.radiojavan.com/mp3s/mp3/Artist-Track</code>\n"
    "• Web Player: <code>https://play.radiojavan.com/song/Artist-Track</code>\n"
    "• Podcasts: <code>https://www.radiojavan.com/podcasts/podcast/Episode</code>\n"
    "• Shortlinks: <code>https://rj.app/m/abcdef</code>\n\n"
    "✨ <i>Includes lyrics (when available) and high-resolution cover art.</i>"
)

TEXT_PLAT_SC = (
    "☁️ <b>SoundCloud Support</b>\n\n"
    "<b>Supported Link Formats:</b>\n"
    "• Canonical: <code>https://soundcloud.com/artist/track-title</code>\n"
    "• Mobile: <code>https://m.soundcloud.com/artist/track-title</code>\n"
    "• Shortlinks: <code>https://on.soundcloud.com/abcdef</code>\n\n"
    "✨ <i>Dynamic client ID extraction, 500x500 artwork, and progressive MP3 direct streaming.</i>"
)

TEXT_PLAT_SP = (
    "🟢 <b>Spotify Support</b>\n\n"
    "<b>Supported Link Formats:</b>\n"
    "• Web Tracks: <code>https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT</code>\n"
    "• Localized: <code>https://open.spotify.com/intl-de/track/...</code>\n"
    "• Shortlinks: <code>https://spotify.link/abcdef</code>\n"
    "• Spotify URIs: <code>spotify:track:4cOdK2wGLETKBW3PvgPWqT</code>\n\n"
    "✨ <i>Official Spotify metadata & 640x640 artwork matched with high quality audio.</i>"
)

TEXT_ABOUT = (
    "ℹ️ <b>About Music Downloader Bot</b>\n\n"
    "• <b>Version:</b> 1.1.0\n"
    "• <b>Framework:</b> Python 3 + pyTelegramBotAPI\n"
    "• <b>Audio Engine:</b> FFmpeg + Mutagen + yt-dlp\n"
    "• <b>License:</b> GNU General Public License v3.0\n\n"
    "Built for fast, seamless music and podcast downloads with complete metadata. 🎧"
)


def get_ping_text(latency_ms: int = 0) -> str:
    active_names = ", ".join(s.__class__.__name__.replace("Service", "") for s in SERVICES)
    ffmpeg_status = "Available ✅" if config.FFMPEG_PATH else "Missing ⚠️"
    return (
        "⚡ <b>Bot Status & Health</b>\n\n"
        f"• <b>Response Latency:</b> {latency_ms} ms\n"
        f"• <b>Active Providers ({len(SERVICES)}):</b> {active_names}\n"
        f"• <b>FFmpeg Engine:</b> {ffmpeg_status}\n"
        f"• <b>Upload Limit:</b> 50 MB (Telegram API)\n"
        f"• <b>Status:</b> All systems operational 🚀"
    )


def register_handlers(bot: TeleBot) -> None:
    """Register all message and callback handlers on the bot instance."""

    # 1. Command handlers
    @bot.message_handler(commands=["start"])
    def handle_start(message: Message):
        bot.send_message(
            message.chat.id,
            TEXT_START,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )

    @bot.message_handler(commands=["help", "commands"])
    def handle_help(message: Message):
        bot.send_message(
            message.chat.id,
            TEXT_HELP,
            parse_mode="HTML",
            reply_markup=platforms_menu_keyboard(),
        )

    @bot.message_handler(commands=["platforms"])
    def handle_platforms(message: Message):
        bot.send_message(
            message.chat.id,
            TEXT_PLATFORMS,
            parse_mode="HTML",
            reply_markup=platforms_menu_keyboard(),
        )

    @bot.message_handler(commands=["ping"])
    def handle_ping(message: Message):
        t0 = time.time()
        msg = bot.send_message(message.chat.id, "⚡ <i>Pinging...</i>", parse_mode="HTML")
        latency = int((time.time() - t0) * 1000)
        bot.edit_message_text(
            get_ping_text(latency),
            message.chat.id,
            msg.message_id,
            parse_mode="HTML",
            reply_markup=back_to_main_keyboard(),
        )

    @bot.message_handler(commands=["about"])
    def handle_about(message: Message):
        bot.send_message(
            message.chat.id,
            TEXT_ABOUT,
            parse_mode="HTML",
            reply_markup=back_to_main_keyboard(),
        )

    # 2. Callback Query handler for inline UI navigation
    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("ui_"))
    def handle_ui_callbacks(call: CallbackQuery):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        try:
            if data == "ui_main":
                bot.edit_message_text(
                    TEXT_START,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(),
                )
            elif data == "ui_help":
                bot.edit_message_text(
                    TEXT_HELP,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=platforms_menu_keyboard(),
                )
            elif data == "ui_platforms":
                bot.edit_message_text(
                    TEXT_PLATFORMS,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=platforms_menu_keyboard(),
                )
            elif data == "ui_plat_rj":
                bot.edit_message_text(
                    TEXT_PLAT_RJ,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=platform_detail_keyboard(),
                )
            elif data == "ui_plat_sc":
                bot.edit_message_text(
                    TEXT_PLAT_SC,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=platform_detail_keyboard(),
                )
            elif data == "ui_plat_sp":
                bot.edit_message_text(
                    TEXT_PLAT_SP,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=platform_detail_keyboard(),
                )
            elif data == "ui_ping":
                t0 = time.time()
                bot.edit_message_text(
                    "⚡ <i>Pinging...</i>",
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                )
                latency = int((time.time() - t0) * 1000)
                bot.edit_message_text(
                    get_ping_text(latency),
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=back_to_main_keyboard(),
                )
            elif data == "ui_about":
                bot.edit_message_text(
                    TEXT_ABOUT,
                    chat_id,
                    msg_id,
                    parse_mode="HTML",
                    reply_markup=back_to_main_keyboard(),
                )
        except Exception as e:
            logger.debug(f"Callback query edit suppressed: {e}")

    # 3. Music link processor
    @bot.message_handler(func=lambda msg: msg.text and bool(re.search(r"https?://|spotify:track:", msg.text)))
    def handle_music_link(message: Message):
        raw_text = message.text.strip()
        service = find_service(raw_text)

        if not service:
            # Unrecognized service link
            bot.reply_to(
                message,
                "⚠️ <b>Unrecognized Music Link!</b>\n\n"
                "Please send a valid link from <b>Radio Javan</b>, <b>SoundCloud</b>, or <b>Spotify</b>.",
                parse_mode="HTML",
                reply_markup=error_keyboard(),
            )
            return

        status_msg = bot.send_message(message.chat.id, "🔍 <i>Analyzing link...</i>", parse_mode="HTML")

        try:
            # 1. Fetch metadata and stream link
            track = service.fetch_track(raw_text)
            bot.edit_message_text(
                f"📥 <i>Found: {track.artist} - {track.title}</i>\n⏳ Starting download...",
                message.chat.id,
                status_msg.message_id,
                parse_mode="HTML",
            )

            # 2. Download in an isolated temporary directory
            with temporary_work_dir() as work_dir:
                filename = safe_filename(f"{track.artist} - {track.title}") + f".{track.format}"
                file_path = work_dir / filename

                def progress_callback(downloaded: int, total: int, percent: int):
                    bar = format_progress_bar(percent)
                    try:
                        bot.edit_message_text(
                            f"⏳ <b>Downloading...</b>\n{bar}",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass  # Silently ignore rate-limiting edits during download

                service.download_track(
                    track,
                    file_path,
                    on_progress=progress_callback,
                )

                file_size = os.path.getsize(file_path)

                # 3. Check Telegram 50MB upload limit
                if file_size > config.MAX_AUDIO_BYTES:
                    size_mb = file_size / (1024 * 1024)
                    fallback_link = track.share_url or (track.download_url if track.download_url.startswith("http") else raw_text)
                    warning_text = (
                        f"⚠️ <b>File is too large for Telegram upload!</b>\n\n"
                        f"Size: <b>{size_mb:.1f} MB</b> (Telegram bot limit is 50 MB).\n"
                        f"You can listen or download directly via browser:"
                    )
                    bot.edit_message_text(
                        warning_text,
                        message.chat.id,
                        status_msg.message_id,
                        reply_markup=oversized_file_keyboard(fallback_link),
                        parse_mode="HTML",
                    )
                    return

                # 4. Apply metadata tags
                try:
                    bot.edit_message_text(
                        "🏷 <i>Applying metadata & artwork...</i>",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

                apply_metadata(file_path, track)

                # 5. Upload audio to Telegram
                try:
                    bot.edit_message_text(
                        "📤 <i>Uploading to Telegram...</i>",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

                caption = format_caption(track)
                with open(file_path, "rb") as audio_fp:
                    bot.send_audio(
                        message.chat.id,
                        audio_fp,
                        caption=caption,
                        parse_mode="HTML",
                        title=track.title,
                        performer=track.artist,
                        duration=int(track.duration) if track.duration else None,
                        reply_markup=audio_action_keyboard(track),
                    )

                # 6. Delete progress message on success
                try:
                    bot.delete_message(message.chat.id, status_msg.message_id)
                except Exception:
                    pass

        except Exception as e:
            logger.exception(f"Error handling link {raw_text}: {e}")
            try:
                bot.edit_message_text(
                    f"❌ <b>Error:</b> {str(e)}",
                    message.chat.id,
                    status_msg.message_id,
                    reply_markup=error_keyboard(),
                    parse_mode="HTML",
                )
            except Exception:
                bot.send_message(
                    message.chat.id,
                    f"❌ <b>Error:</b> {str(e)}",
                    reply_markup=error_keyboard(),
                    parse_mode="HTML",
                )
