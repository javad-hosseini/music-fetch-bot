import os
import re
import requests
from telebot import TeleBot
from radiojavanapi import Client

# =====================
# CONFIG
# =====================
BOT_TOKEN = "8979874899:AAG-lVb0-8Lkf-fni2Si4VQq15JhQ0mY7uE"
bot = TeleBot(BOT_TOKEN)
client = Client()

# =====================
# STORAGE FOLDER
# =====================
BASE_DIR = "fetched_songs"
os.makedirs(BASE_DIR, exist_ok=True)


# =====================
# SAFE FILENAME
# =====================
def safe_name(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


# =====================
# DOWNLOAD FUNCTION (STABLE)
# =====================
def download_file(url, path):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


# =====================
# RESOLVE LINK
# =====================
def resolve_link(url):
    try:
        r = requests.get(url, allow_redirects=True, timeout=10)
        final_url = r.url

        if "radiojavan://" in final_url:
            return None

        return final_url
    except:
        return None


# =====================
# DETECT TYPE
# =====================
def detect_type(url):
    if "podcast" in url:
        return "podcast"
    elif "song" in url or "mp3" in url:
        return "song"
    return None


# =====================
# START
# =====================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎧 لینک رادیو جوان رو بفرست\n"
        "من خودم برات دانلود می‌کنم 😎🔥"
    )


# =====================
# MAIN HANDLER
# =====================
@bot.message_handler(func=lambda m: m.text and "radiojavan" in m.text)
def handle_all_links(message):
    try:
        raw_url = message.text

        msg = bot.send_message(message.chat.id, "⏳ در حال پردازش...")

        # 1. resolve link
        url = resolve_link(raw_url)
        if not url:
            bot.edit_message_text("❌ لینک نامعتبره", message.chat.id, msg.message_id)
            return

        # 2. detect type
        content_type = detect_type(url)
        if not content_type:
            bot.edit_message_text("❌ نوع لینک قابل تشخیص نیست", message.chat.id, msg.message_id)
            return

        # =====================
        # SONG
        # =====================
        if content_type == "song":
            song = client.get_song_by_url(url)

            name = safe_name(song.name)
            artist = safe_name(song.artist)

            photo_path = os.path.join(BASE_DIR, f"{name}_photo.jpg")
            audio_path = os.path.join(BASE_DIR, f"{name}_{artist}.mp3")

            download_file(song.photo, photo_path)
            bot.send_photo(message.chat.id, open(photo_path, "rb"))

            download_file(song.hq_link, audio_path)
            bot.send_audio(
                message.chat.id,
                open(audio_path, "rb"),
                caption=f"🎵 {song.name}\n👤 {song.artist}"
            )

            os.remove(photo_path)
            os.remove(audio_path)

        # =====================
        # PODCAST
        # =====================
        elif content_type == "podcast":
            podcast = client.get_podcast_by_url(url)

            title = safe_name(podcast.title)

            photo_path = os.path.join(BASE_DIR, f"{title}_photo.jpg")
            audio_path = os.path.join(BASE_DIR, f"{title}.mp3")

            download_file(podcast.photo, photo_path)
            bot.send_photo(message.chat.id, open(photo_path, "rb"))

            download_file(podcast.hq_link, audio_path)
            bot.send_audio(
                message.chat.id,
                open(audio_path, "rb"),
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