import os
import re
import time
import html
import logging
import threading
from pathlib import Path
from telebot import TeleBot
from telebot.types import Message, CallbackQuery

import config
from services import find_service, SERVICES
from utils.filesystem import safe_filename, temporary_work_dir
from utils.audio import apply_mp3_metadata, convert_to_mp3, ensure_mp3
from bot.formatters import format_caption, format_progress_bar, get_service_badge
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

_active_downloads = set()
_active_downloads_lock = threading.Lock()

TEXT_START = (
    "👋 <b>Welcome to Music Downloader Bot!</b>\n\n"
    "Send me any music or podcast link from our supported platforms, and I'll download "
    "it for you as a universal <b>MP3</b> with full ID3 tags and high-resolution album artwork.\n\n"
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
    "The bot currently supports 3 major music platforms (all converted strictly to MP3):\n\n"
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
    "✨ <i>Output: Strict 320/192kbps MP3 with lyrics & high-res artwork.</i>"
)

TEXT_PLAT_SC = (
    "☁️ <b>SoundCloud Support</b>\n\n"
    "<b>Supported Link Formats:</b>\n"
    "• Canonical: <code>https://soundcloud.com/artist/track-title</code>\n"
    "• Mobile: <code>https://m.soundcloud.com/artist/track-title</code>\n"
    "• Shortlinks: <code>https://on.soundcloud.com/abcdef</code>\n\n"
    "✨ <i>Output: Strict MP3 with dynamic client ID extraction & 500x500 artwork.</i>"
)

TEXT_PLAT_SP = (
    "🟢 <b>Spotify Support</b>\n\n"
    "<b>Supported Link Formats:</b>\n"
    "• Web Tracks: <code>https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT</code>\n"
    "• Localized: <code>https://open.spotify.com/intl-de/track/...</code>\n"
    "• Shortlinks: <code>https://spotify.link/abcdef</code>\n"
    "• Spotify URIs: <code>spotify:track:4cOdK2wGLETKBW3PvgPWqT</code>\n\n"
    "✨ <i>Output: Strict MP3 with official metadata & 640x640 artwork.</i>"
)

TEXT_ABOUT = (
    "ℹ️ <b>About Music Downloader Bot</b>\n\n"
    "• <b>Version:</b> 1.1.0\n"
    "• <b>Format:</b> Universal MP3 (ID3v2.3 tags)\n"
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
        f"• <b>Format Guarantee:</b> Strictly MP3 (ID3v2.3)\n"
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
        user_id = message.from_user.id if message.from_user else message.chat.id

        # Prevent duplicate concurrent downloads per user
        with _active_downloads_lock:
            if user_id in _active_downloads:
                bot.reply_to(
                    message,
                    "⏳ <b>Download in progress!</b>\n\n"
                    "You already have an active download in progress. Please wait for it to complete.",
                    parse_mode="HTML",
                )
                return
            _active_downloads.add(user_id)

        try:
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
                badge = get_service_badge(track.source)
                title_esc = html.escape(track.title or "Unknown Track")
                artist_esc = html.escape(track.artist or "Unknown Artist")

                bot.edit_message_text(
                    f"📥 <b>[{badge}]</b> <i>{artist_esc} - {title_esc}</i>\n⏳ Starting download...",
                    message.chat.id,
                    status_msg.message_id,
                    parse_mode="HTML",
                )

                # 2. Download in an isolated temporary directory with universal .mp3 extension
                with temporary_work_dir() as work_dir:
                    filename = safe_filename(f"{track.artist} - {track.title}") + ".mp3"
                    file_path = work_dir / filename

                    def progress_callback(downloaded: int, total: int, percent: int):
                        bar = format_progress_bar(percent, downloaded_bytes=downloaded, total_bytes=total)
                        try:
                            bot.edit_message_text(
                                f"📥 <b>[{badge}]</b> <i>{artist_esc} - {title_esc}</i>\n"
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

                    # Ensure target file exists and is strictly an MP3
                    if not file_path.exists():
                        # Check if service saved as non-mp3 or different stem in work_dir
                        candidates = list(work_dir.glob("*"))
                        audio_candidates = [c for c in candidates if c.is_file() and c != file_path]
                        if audio_candidates:
                            chosen = audio_candidates[0]
                            if chosen.suffix.lower() == ".mp3":
                                chosen.rename(file_path)
                            else:
                                convert_to_mp3(chosen, file_path)
                                chosen.unlink(missing_ok=True)
                        else:
                            raise RuntimeError(f"Downloaded file not found at {file_path}")

                    # Enforce universal MP3 audio format
                    file_path = ensure_mp3(file_path)

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

                    # 4. Apply ID3v2 metadata tags
                    try:
                        bot.edit_message_text(
                            f"🏷 <i>Applying ID3 metadata & album artwork...</i>",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

                    apply_mp3_metadata(file_path, track)

                    # 5. Upload audio to Telegram
                    try:
                        bot.edit_message_text(
                            "📤 <i>Uploading MP3 to Telegram...</i>",
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
                if isinstance(e, ValueError):
                    user_msg = html.escape(str(e))
                else:
                    user_msg = "An error occurred while processing this audio link. Please check the URL or try again later."

                try:
                    bot.edit_message_text(
                        f"❌ <b>Error:</b> {user_msg}",
                        message.chat.id,
                        status_msg.message_id,
                        reply_markup=error_keyboard(),
                        parse_mode="HTML",
                    )
                except Exception:
                    try:
                        bot.send_message(
                            message.chat.id,
                            f"❌ <b>Error:</b> {user_msg}",
                            reply_markup=error_keyboard(),
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
        finally:
            with _active_downloads_lock:
                _active_downloads.discard(user_id)
