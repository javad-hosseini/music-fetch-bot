import os
import re
import requests
from telebot import TeleBot
from radiojavanapi import Client

# =====================
# CONFIG
# =====================
BOT_TOKEN = "YOUR_BOT_TOKEN"
bot = TeleBot(BOT_TOKEN)

client = Client()

# =====================
# LINK RESOLVER
# =====================
def resolve_link(url):
    """
    تبدیل هر نوع لینک رادیو جوان به لینک قابل استفاده
    """
    try:
        r = requests.get(url, allow_redirects=True, timeout=10)
        final_url = r.url

        # حذف deep link های اپ
        if "radiojavan://" in final_url:
            return None

        return final_url
    except:
        return None


def detect_type(url):
    """
    تشخیص نوع محتوا
    """
    if "podcast" in url:
        return "podcast"
    elif "song" in url or "mp3" in url:
        return "song"
    else:
        return None


# =====================
# START
# =====================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎧 لینک رادیو جوان رو بفرست (هر نوعی باشه)\n"
        "من خودم دانلودش می‌کنم 😎🔥"
    )


# =====================
# UNIVERSAL HANDLER
# =====================
@bot.message_handler(func=lambda m: m.text and "radiojavan" in m.text)
def handle_all_links(message):
    try:
        raw_url = message.text

        msg = bot.send_message(message.chat.id, "⏳ در حال پردازش لینک...")

        # 1. Resolve link
        url = resolve_link(raw_url)

        if not url:
            bot.edit_message_text("❌ لینک نامعتبر یا غیرقابل پردازش", message.chat.id, msg.message_id)
            return

        # 2. Detect type
        content_type = detect_type(url)

        if not content_type:
            bot.edit_message_text("❌ نوع لینک قابل تشخیص نیست", message.chat.id, msg.message_id)
            return

        # =====================
        # SONG
        # =====================
        if content_type == "song":
            song = client.get_song_by_url(url)

            # cover
            photo_path = f"{song.name}_photo.jpg"
            with open(photo_path, "wb") as f:
                f.write(requests.get(song.photo).content)

            with open(photo_path, "rb") as f:
                bot.send_photo(message.chat.id, f)

            # audio
            audio_path = f"{song.name}.mp3"
            with open(audio_path, "wb") as f:
                f.write(requests.get(song.hq_link).content)

            with open(audio_path, "rb") as f:
                bot.send_audio(
                    message.chat.id,
                    f,
                    caption=f"🎵 {song.name}\n👤 {song.artist}"
                )

            os.remove(photo_path)
            os.remove(audio_path)

        # =====================
        # PODCAST
        # =====================
        elif content_type == "podcast":
            podcast = client.get_podcast_by_url(url)

            photo_path = f"{podcast.title}_photo.jpg"
            with open(photo_path, "wb") as f:
                f.write(requests.get(podcast.photo).content)

            with open(photo_path, "rb") as f:
                bot.send_photo(message.chat.id, f)

            audio_path = f"{podcast.title}.mp3"
            with open(audio_path, "wb") as f:
                f.write(requests.get(podcast.hq_link).content)

            with open(audio_path, "rb") as f:
                bot.send_audio(
                    message.chat.id,
                    f,
                    caption=f"🎙 {podcast.title}"
                )

            os.remove(photo_path)
            os.remove(audio_path)

        # finish
        bot.delete_message(message.chat.id, msg.message_id)
        bot.send_message(message.chat.id, "✅ دانلود کامل شد!")

    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")


# =====================
# RUN
# =====================
print("Bot is running...")
bot.polling(none_stop=True)