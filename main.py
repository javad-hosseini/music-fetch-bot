import os
import re
import requests
from tqdm import tqdm
import argparse
from radiojavanapi import Client

from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT, TDRC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover


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


def download_file(url: str, path: str, retries=3) -> None:
    attempt = 0

    while attempt < retries:
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()

                total = int(r.headers.get("content-length", 0))
                progress = tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc="Downloading",
                    ncols=80
                )

                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            progress.update(len(chunk))

                progress.close()
                return  # success

        except Exception as e:
            attempt += 1
            print(f"⚠️ Download failed (attempt {attempt}/{retries}): {e}")

            if attempt == retries:
                raise ValueError("❌ Download failed after multiple retries")

            print("🔁 Retrying...")


def is_valid_mp3(path: str) -> bool:
    with open(path, "rb") as f:
        header = f.read(4)
    return header.startswith(b"ID3") or header.startswith(b"\xff")


def is_valid_m4a(path: str) -> bool:
    with open(path, "rb") as f:
        header = f.read(12)
    return b"ftypM4A" in header or b"ftypisom" in header


# =====================
# METADATA: MP3
# =====================
def apply_mp3_metadata(path: str, song):
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
        except:
            pass

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


# =====================
# METADATA: M4A
# =====================
def apply_m4a_metadata(path: str, song):
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
        except:
            pass

    audio.save()


# =====================
# DEBUG MODE
# =====================
def safe_get(obj, attr, default="N/A"):
    return getattr(obj, attr, default)


def debug_song(song):
    print("\n================ SONG DEBUG ================")

    print(f"🎵 TITLE      : {safe_get(song, 'title')}")
    print(f"👤 ARTIST     : {safe_get(song, 'artist')}")
    print(f"📌 NAME       : {safe_get(song, 'name')}")
    print(f"💿 ALBUM      : {safe_get(song, 'album')}")
    print(f"⏱ DURATION   : {safe_get(song, 'duration')} sec")
    print(f"📅 CREATED    : {safe_get(song, 'created_at')}")

    print(f"👍 LIKES      : {safe_get(song, 'likes')}")
    print(f"👎 DISLIKES   : {safe_get(song, 'dislikes')}")
    print(f"▶️ PLAYS      : {safe_get(song, 'plays')}")
    print(f"⬇️ DOWNLOADS  : {safe_get(song, 'downloads')}")

    print(f"🔗 SHARE LINK : {safe_get(song, 'share_link')}")
    print(f"🎧 HQ LINK    : {safe_get(song, 'hq_link')}")
    print(f"🔊 LQ LINK    : {safe_get(song, 'lq_link')}")
    print(f"🌐 STREAM     : {safe_get(song, 'link')}")

    print(f"🖼 PHOTO      : {safe_get(song, 'photo')}")
    print(f"🖼 THUMBNAIL  : {safe_get(song, 'thumbnail')}")
    print(f"🎬 PLAYER IMG : {safe_get(song, 'photo_player')}")

    lyric = safe_get(song, 'lyric', "")
    print("\n📝 LYRIC (preview):")
    print(lyric if lyric else "No lyric available")

    related = safe_get(song, 'related_songs', [])
    # print(f"\n🎧 RELATED SONGS: {len(related) if related else 0}")
    #
    # print("===========================================\n")




# =====================
# MAIN LOGIC
# =====================
def handle_debug(url):
    song = client.get_song_by_url(url)

    # print("\n=== RAW OBJECT ===")
    # print(song)

    print("\n=== CLEAN DEBUG OUTPUT ===")
    debug_song(song)

    # print("\n=== DICT (clean version) ===")
    # try:
    #     safe_data = make_json_safe(song)
    #     print(json.dumps(safe_data, indent=4, ensure_ascii=False))
    # except Exception as e:
    #     print("Error converting to JSON:", e)


def handle_download(url):
    song = client.get_song_by_url(url)

    download_url = str(song.hq_link or song.lq_link)

    if download_url.endswith(".mp3"):
        ext = ".mp3"
    elif download_url.endswith(".m4a"):
        ext = ".m4a"
    else:
        raise ValueError("Unknown audio format")

    artist = safe_name(song.artist)
    name = safe_name(song.name)
    filename = f"{artist} - {name}{ext}"
    audio_path = os.path.join(BASE_DIR, filename)

    print(f"📥 Downloading: {filename}")
    download_file(download_url, audio_path, retries=3)

    if ext == ".mp3" and not is_valid_mp3(audio_path):
        raise ValueError("Downloaded file is NOT a valid MP3")

    if ext == ".m4a" and not is_valid_m4a(audio_path):
        raise ValueError("Downloaded file is NOT a valid M4A")

    print("🏷  Applying metadata...")

    if ext == ".mp3":
        apply_mp3_metadata(audio_path, song)
    else:
        apply_m4a_metadata(audio_path, song)

    print(f"✅ Saved to: {audio_path}")


# =====================
# CLI ENTRY
# =====================
def main():
    parser = argparse.ArgumentParser(
        description="RadioJavan Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--debug", action="store_true", help="Show full metadata")
    parser.add_argument("--download", action="store_true", help="Download the song")
    parser.add_argument("--loop", action="store_true", help="Keep asking for URLs")

    args = parser.parse_args()

    # ============================
    # If no arguments → show help
    # ============================
    if not any(vars(args).values()):
        parser.print_help()
        return

    # ============================
    # Normal execution
    # ============================
    while True:
        url = input("\n🎧 Enter RadioJavan URL:\n> ").strip()

        if args.debug:
            handle_debug(url)

        if args.download:
            handle_download(url)

        if not args.loop:
            break

        again = input("\n🔁 Download another? (y/n): ").strip().lower()
        if again != "y":
            break


if __name__ == "__main__":
    main()
