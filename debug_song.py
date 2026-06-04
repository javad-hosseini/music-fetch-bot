from radiojavanapi import Client
from pydantic import TypeAdapter
import json


def safe_get(obj, attr, default="N/A"):
    """
    برای جلوگیری از کرش اگر فیلد وجود نداشت
    """
    return getattr(obj, attr, default)


def debug_song(song):
    print("\n================ SONG DEBUG ================")

    # 🎵 Main Info
    print(f"🎵 TITLE      : {safe_get(song, 'title')}")
    print(f"👤 ARTIST     : {safe_get(song, 'artist')}")
    print(f"📌 NAME       : {safe_get(song, 'name')}")
    print(f"💿 ALBUM      : {safe_get(song, 'album')}")
    print(f"⏱ DURATION   : {safe_get(song, 'duration')} sec")
    print(f"📅 CREATED    : {safe_get(song, 'created_at')}")

    # 📊 Stats
    print(f"👍 LIKES      : {safe_get(song, 'likes')}")
    print(f"👎 DISLIKES   : {safe_get(song, 'dislikes')}")
    print(f"▶️ PLAYS      : {safe_get(song, 'plays')}")
    print(f"⬇️ DOWNLOADS  : {safe_get(song, 'downloads')}")

    # 🔗 Links
    print(f"🔗 SHARE LINK : {safe_get(song, 'share_link')}")
    print(f"🎧 HQ LINK    : {safe_get(song, 'hq_link')}")
    print(f"🔊 LQ LINK    : {safe_get(song, 'lq_link')}")
    print(f"🌐 STREAM     : {safe_get(song, 'link')}")

    # 🖼 Media
    print(f"🖼 PHOTO      : {safe_get(song, 'photo')}")
    print(f"🖼 THUMBNAIL  : {safe_get(song, 'thumbnail')}")
    print(f"🎬 PLAYER IMG : {safe_get(song, 'photo_player')}")

    # 📝 Lyrics
    lyric = safe_get(song, 'lyric', "")
    print("\n📝 LYRIC (preview):")
    print(lyric if lyric else "No lyric available")

    # 🧠 Related songs count
    related = safe_get(song, 'related_songs', [])
    print(f"\n🎧 RELATED SONGS: {len(related) if related else 0}")

    print("===========================================\n")

def make_json_safe(obj):
    """
    تبدیل کامل Pydantic object به JSON قابل چاپ
    """
    return json.loads(
        json.dumps(obj.model_dump(), default=str, ensure_ascii=False)
    )


# ======================
# RUN
# ======================
client = Client()

url = input("\n=== URL ===\n")

song = client.get_song_by_url(url)

print("\n=== RAW OBJECT ===")
print(song)

print("\n=== CLEAN DEBUG OUTPUT ===")
debug_song(song)

print("\n=== DICT (clean version) ===")
try:
    safe_data = make_json_safe(song)
    print(json.dumps(safe_data, indent=4, ensure_ascii=False))
except Exception as e:
    print("Error converting to JSON:", e)