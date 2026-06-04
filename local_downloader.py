import os
import re
import requests
from radiojavanapi import Client
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT, TDRC
from mutagen.mp3 import MP3

# =====================
# CONFIG
# =====================
BASE_DIR = "fetched_songs"
os.makedirs(BASE_DIR, exist_ok=True)

client = Client()


# =====================
# HELPERS
# =====================
def safe_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def download_file(url: str, path: str) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


# =====================
# METADATA
# =====================
def apply_metadata(mp3_path: str, song) -> None:
    audio = MP3(mp3_path, ID3=ID3)

    # اگر فایل تگ نداشت، اضافه کن
    if audio.tags is None:
        audio.add_tags()

    # تگ‌های اصلی
    audio.tags["TIT2"] = TIT2(encoding=3, text=song.name)
    audio.tags["TPE1"] = TPE1(encoding=3, text=song.artist)

    if song.album:
        audio.tags["TALB"] = TALB(encoding=3, text=song.album)

    # کاور
    if song.photo:
        try:
            cover_data = requests.get(str(song.photo), timeout=10).content
            audio.tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_data
            )
        except Exception as e:
            print(f"⚠️  Cover fetch failed: {e}")

    # متن آهنگ
    if song.lyric:
        audio.tags["USLT"] = USLT(
            encoding=3,
            lang="eng",
            desc="Lyrics",
            text=song.lyric
        )

    # سال انتشار
    if song.created_at:
        year = str(song.created_at)[:4]
        audio.tags["TDRC"] = TDRC(encoding=3, text=year)

    # ذخیره با سازگاری بالا
    audio.save(v2_version=3)


# =====================
# MAIN
# =====================
def main():
    url = input("RadioJavan URL: ").strip()

    print("⏳ Fetching metadata...")
    song = client.get_song_by_url(url)


    artist = safe_name(song.artist)
    name = safe_name(song.name)
    filename = f"{artist} - {name}.mp3"
    audio_path = os.path.join(BASE_DIR, filename)
    print("Download URL:", song.hq_link)

    print(f"📥 Downloading: {filename}")
    download_file(str(song.hq_link), audio_path)
    with open(audio_path, "rb") as f:
        print(f.read(200))

    # verify file is real MP3 before tagging
    with open(audio_path, "rb") as f:
        header = f.read(3)

    if header != b"ID3" and header[:1] != b"\xff":
        raise ValueError("Downloaded file is NOT a valid MP3 (HTML or corrupted).")

    size = os.path.getsize(audio_path)
    print("File size:", size)

    print("🏷  Applying metadata...")
    apply_metadata(audio_path, song)

    # verify file is a valid MP3
    try:
        mp3 = MP3(audio_path)
        duration = int(mp3.info.length)
        print(f"✅ Saved to: {audio_path} ({duration}s)")
    except Exception:
        print(f"⚠️ File saved but could not read MP3 info — check file integrity.")
        print(f"📌 Path: {audio_path}")


if __name__ == "__main__":
    main()
