import os
import re
import requests
import json
from telebot import TeleBot, apihelper
from radiojavanapi import Client
from JSON_builder import get_song_json
from metadata import apply_metadata

# =====================
# CONFIG
# =====================
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(BOT_TOKEN)

# تنظیم تایم‌اوت به صورت جهانی برای جلوگیری از ارور TimeOut
apihelper.READ_TIMEOUT = 300
apihelper.CONNECT_TIMEOUT = 300

client = Client()

BASE_DIR = "fetched_songs"
os.makedirs(BASE_DIR, exist_ok=True)


# =====================
# HELPERS
# =====================
def safe_name(name):
    return re.sub(r'[\/*?:"<>|]', "", name)


def download_file(url, path):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def resolve_link(url):
    try:
        r = requests.get(url, allow_redirects=True, timeout=10)
        final_url = r.url
        if "radiojavan://" in final_url:
            return None
        return final_url
    except:
        return None


def detect_type(url):
    if "podcast" in url:
        return "podcast"
    elif "song" in url or "mp3" in url:
        return "song"
    return None


# =====================
# HANDLERS
# =====================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id, "🎧 لینک رادیو جوان رو بفرست\nمن خودم برات دانلود می‌کنم 😎🔥")


@bot.message_handler(func=lambda m: m.text and "radiojavan" in m.text)
def handle_all_links(message):
    try:
        raw_url = message.text
        msg = bot.send_message(message.chat.id, "⏳ در حال پردازش...")

        url = resolve_link(raw_url)
        if not url:
            bot.edit_message_text("❌ لینک نامعتبره", message.chat.id, msg.message_id)
            return

        content_type = detect_type(url)
        if not content_type:
            bot.edit_message_text("❌ نوع لینک قابل تشخیص نیست", message.chat.id, msg.message_id)
            return

        if content_type == "song":
            # 1️⃣ دریافت اطلاعات به صورت دیکشنری تمیز
            song_data = get_song_json(url)

            name = safe_name(song_data["name"])
            artist = safe_name(song_data["artist"])

            # مسیر فایل‌ها
            photo_path = os.path.join(BASE_DIR, f"{name}_photo.jpg")
            audio_path = os.path.join(BASE_DIR, f"{name}_{artist}.mp3")

            # 2️⃣ دانلود فایل‌ها
            download_file(song_data["photo"], photo_path)
            download_file(song_data["hq_link"], audio_path)

            # 3️⃣ اعمال متادیتا (قبل از ارسال)
            apply_metadata(audio_path, song_data)

            # 4️⃣ ارسال به کاربر
            with open(photo_path, "rb") as photo, open(audio_path, "rb") as audio:
                bot.send_photo(message.chat.id, photo)
                bot.send_audio(
                    message.chat.id,
                    audio,
                    caption=f"🎵 {song_data['name']}\n👤 {song_data['artist']}"
                )

            # 5️⃣ پاکسازی
            os.remove(photo_path)
            os.remove(audio_path)

        elif content_type == "podcast":
            podcast = client.get_podcast_by_url(url)
            title = safe_name(podcast.title)
            photo_path = os.path.join(BASE_DIR, f"{title}_photo.jpg")
            audio_path = os.path.join(BASE_DIR, f"{title}.mp3")

            download_file(podcast.photo, photo_path)
            download_file(podcast.hq_link, audio_path)

            with open(photo_path, "rb") as photo, open(audio_path, "rb") as audio:
                bot.send_photo(message.chat.id, photo)
                bot.send_audio(
                    message.chat.id,
                    audio,
                    caption=f"🎙 {podcast.title}"
                )

            os.remove(photo_path)
            os.remove(audio_path)

        bot.delete_message(message.chat.id, msg.message_id)
        bot.send_message(message.chat.id, "✅ دانلود کامل شد!")

    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
        print(e)


if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.polling(none_stop=True)