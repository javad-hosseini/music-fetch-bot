import os
import re
import logging
from telebot import TeleBot
from telebot.types import Message

import config
from services import find_service
from utils.filesystem import safe_filename, temporary_work_dir
from utils.downloader import download_stream
from utils.audio import apply_metadata
from bot.formatters import format_caption, format_progress_bar

logger = logging.getLogger(__name__)


def register_handlers(bot: TeleBot) -> None:
    """Register all message and callback handlers on the bot instance."""

    @bot.message_handler(commands=["start", "help"])
    def handle_start(message: Message):
        text = (
            "👋 <b>Welcome to Music Downloader Bot!</b>\n\n"
            "Send me a music or podcast link from supported platforms, and I'll download it for you with full metadata and album artwork.\n\n"
            "📌 <b>Supported Services:</b>\n"
            "• <b>Radio Javan</b> (Songs & Podcasts)\n"
            "• <b>SoundCloud</b> (Tracks)\n"
            "• <b>Spotify</b> (Tracks)\n\n"
            "Just paste the link below! 🎧"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML")

    @bot.message_handler(func=lambda msg: msg.text and bool(re.search(r"https?://|spotify:track:", msg.text)))
    def handle_music_link(message: Message):
        raw_text = message.text.strip()
        service = find_service(raw_text)

        if not service:
            # Not a recognized service link
            return

        status_msg = bot.send_message(message.chat.id, "🔍 <i>Analyzing link...</i>", parse_mode="HTML")

        try:
            # 1. Fetch metadata and stream link
            track = service.fetch_track(raw_text)
            bot.edit_message_text(
                f"📥 <i>Found: {track.artist} - {track.title}</i>\n⏳ Starting download...",
                message.chat.id,
                status_msg.message_id,
                parse_mode="HTML"
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
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass  # Silently ignore rate-limiting edits during download

                service.download_track(
                    track,
                    file_path,
                    on_progress=progress_callback
                )

                file_size = os.path.getsize(file_path)

                # 3. Check Telegram 50MB upload limit
                if file_size > config.MAX_AUDIO_BYTES:
                    size_mb = file_size / (1024 * 1024)
                    fallback_link = track.share_url or (track.download_url if track.download_url.startswith("http") else raw_text)
                    warning_text = (
                        f"⚠️ <b>File is too large for Telegram upload!</b>\n\n"
                        f"Size: <b>{size_mb:.1f} MB</b> (Telegram bot limit is 50 MB).\n"
                        f"Link to listen or download:\n"
                        f"🔗 <a href='{fallback_link}'>Direct Link</a>"
                    )
                    bot.edit_message_text(
                        warning_text,
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="HTML"
                    )
                    return

                # 4. Apply metadata tags
                try:
                    bot.edit_message_text(
                        "🏷 <i>Applying metadata & artwork...</i>",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="HTML"
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
                        parse_mode="HTML"
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
                        duration=int(track.duration) if track.duration else None
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
                    parse_mode="HTML"
                )
            except Exception:
                bot.send_message(message.chat.id, f"❌ <b>Error:</b> {str(e)}", parse_mode="HTML")
