import os
import re
import requests
from telebot import TeleBot, apihelper
from radiojavanapi import Client
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT, TDRC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover

# =====================
# CONFIG
# =====================
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(BOT_TOKEN)

# تنظیم تایم‌اوت
apihelper.READ_TIMEOUT = 300
apihelper.CONNECT_TIMEOUT = 300

client = Client()

BASE_DIR = "fetched_songs"
os.makedirs(BASE_DIR, exist_ok=True)


# =====================
# HELPERS
# =====================
def safe_name(name):
    return re.sub(r'[\/*?:"<>|]', "", name).strip()


def download_file_with_progress(url, path, chat_id, msg_id, bot_instance):
    """
    دانلود فایل با نمایش درصد پیشرفت در تلگرام
    """
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # آپدیت پیام هر ۵٪ یا هر ۱ مگابایت
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        if percent % 5 == 0 or downloaded % (1024 * 1024) == 0:
                            try:
                                bot_instance.edit_message_text(
                                    f"⏳ در حال دانلود... {percent}%",
                                    chat_id,
                                    msg_id
                                )
                            except:
                                pass  # اگر ارور داد (مثلاً سریع تموم شد)، نادیده بگیر

    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")


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
# METADATA FUNCTIONS
# =====================
def apply_mp3_metadata(path, song):
    audio = MP3(path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()

    audio.tags["TIT2"] = TIT2(encoding=3, text=song.name)
    audio.tags["TPE1"] = TPE1(encoding=3, text=song.artist)

    if song.album:
        audio.tags["TALB"] = TALB(encoding=3, text=song.album)

    if song.photo:
        try:
            cover = requests.get(str(song.photo), timeout=10).content
            audio.tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover
            )
        except Exception as e:
            print(f"Cover Error: {e}")

    if song.lyric:
        audio.tags["USLT"] = USLT(
            encoding=3,
            lang="eng",
            desc="Lyrics",
            text=song.lyric
        )

    if song.created_at:
        year = str(song.created_at)[:4]
        audio.tags["TDRC"] = TDRC(encoding=3, text=year)

    audio.save(v2_version=3)


def apply_m4a_metadata(path, song):
    audio = MP4(path)
    audio["\xa9nam"] = song.name
    audio["\xa9ART"] = song.artist

    if song.album:
        audio["\xa9alb"] = song.album

    if song.lyric:
        audio["\xa9lyr"] = song.lyric

    if song.created_at:
        year = str(song.created_at)[:4]
        audio["\xa9day"] = year

    if song.photo:
        try:
            cover = requests.get(str(song.photo), timeout=10).content
            audio["covr"] = [
                MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)
            ]
        except Exception as e:
            print(f"Cover Error: {e}")

    audio.save()


# =====================
# CAPTION GENERATOR
# =====================
def generate_caption(song):
    def safe_get(obj, attr, default="N/A"):
        return getattr(obj, attr, default) or default

    title = safe_get(song, 'title')
    artist = safe_get(song, 'artist')
    album = safe_get(song, 'album')
    duration = safe_get(song, 'duration')
    created_at = safe_get(song, 'created_at')
    likes = safe_get(song, 'likes')
    plays = safe_get(song, 'plays')
    lyric = safe_get(song, 'lyric')  # استخراج متن آهنگ

    # فرمت‌بندی زمان
    if duration and isinstance(duration, (int, float)):
        mins, secs = divmod(int(duration), 60)
        duration_str = f"{mins}:{secs:02d}"
    else:
        duration_str = "N/A"

    year = str(created_at)[:4] if created_at else "N/A"

    # مدیریت متن لیریکس (برای جلوگیری از رد شدن از محدودیت ۱۰۲۴ کاراکتر تلگرام)
    lyric_section = ""
    if lyric:
        # اگر متن لیریکس طولانی باشه، فقط ۳۰۰ کاراکتر اولش رو نشون میدیم + لینک "ادامه..."
        if len(lyric) > 700:
            short_lyric = lyric[:700] + "..."
            lyric_section = f"\n\n📝 <b>Lyrics:</b>\n<pre>{short_lyric}</pre>"
        else:
            lyric_section = f"\n\n📝 <b>Lyrics:</b>\n<pre>{lyric}</pre>"

    caption = (
        f"🎵 <b>{title}</b>\n"
        f"👤 <b>Artist:</b> {artist}\n"
        f"💿 <b>Album:</b> {album if album else 'Single'}\n"
        f"⏱ <b>Duration:</b> {duration_str}\n"
        f"📅 <b>Year:</b> {year}\n\n"
        f"📊 <b>Stats:</b>\n"
        f"▶️ Plays: {plays}\n"
        f"👍 Likes: {likes}"
        f"{lyric_section}"  # اضافه شدن لیریکس اینجا
        f"\n\n🔗 <a href='{safe_get(song, 'share_link')}'>Listen on RadioJavan</a>"
    )

    return caption


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
            song = client.get_song_by_url(url)

            # تشخیص فرمت فایل
            download_url = str(song.hq_link or song.lq_link)
            if download_url.endswith(".m4a"):
                ext = ".m4a"
            else:
                ext = ".mp3"

            name = safe_name(song.name)
            artist = safe_name(song.artist)

            audio_path = os.path.join(BASE_DIR, f"{name}_{artist}{ext}")

            # دانلود با پروگرس بار
            bot.edit_message_text("⏳ در حال دانلود... 0%", message.chat.id, msg.message_id)
            download_file_with_progress(download_url, audio_path, message.chat.id, msg.message_id, bot)

            # اعمال متادیتا
            bot.edit_message_text("🏷 در حال اعمال متادیتا...", message.chat.id, msg.message_id)
            if ext == ".mp3":
                apply_mp3_metadata(audio_path, song)
            else:
                apply_m4a_metadata(audio_path, song)

            # ارسال آهنگ
            caption_text = generate_caption(song)

            with open(audio_path, "rb") as audio:
                bot.send_audio(
                    message.chat.id,
                    audio,
                    caption=caption_text,
                    parse_mode="HTML"
                )

            # پاکسازی
            os.remove(audio_path)
            bot.delete_message(message.chat.id, msg.message_id)
            bot.send_message(message.chat.id, "✅ دانلود کامل شد!")

        elif content_type == "podcast":
            podcast = client.get_podcast_by_url(url)
            title = safe_name(podcast.title)

            audio_path = os.path.join(BASE_DIR, f"{title}.mp3")

            bot.edit_message_text("⏳ در حال دانلود پادکست...", message.chat.id, msg.message_id)
            download_file_with_progress(podcast.hq_link, audio_path, message.chat.id, msg.message_id, bot)

            with open(audio_path, "rb") as audio:
                bot.send_audio(
                    message.chat.id,
                    audio,
                    caption=f"🎙 {podcast.title}"
                )

            os.remove(audio_path)
            bot.delete_message(message.chat.id, msg.message_id)
            bot.send_message(message.chat.id, "✅ دانلود کامل شد!")

    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
        print(e)


if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.polling(none_stop=True)