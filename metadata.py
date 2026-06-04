from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT, TDRC
import requests


def apply_metadata(mp3_path, metadata):
    try:
        # اگر فایل تگ داشته باشه لود می‌کنه، اگر نه جدید می‌سازه
        try:
            audio = ID3(mp3_path)
        except:
            audio = ID3()

        # Title
        if metadata.get("name"):
            audio.add(TIT2(encoding=3, text=metadata["name"]))

        # Artist
        if metadata.get("artist"):
            audio.add(TPE1(encoding=3, text=metadata["artist"]))

        # Album
        if metadata.get("album"):
            audio.add(TALB(encoding=3, text=metadata["album"]))

        # Cover Art
        if metadata.get("photo"):
            try:
                response = requests.get(metadata["photo"], timeout=10)
                if response.status_code == 200:
                    audio.add(APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=response.content
                    ))
            except Exception as e:
                print(f"Cover Error: {e}")

        # Lyrics
        if metadata.get("lyric"):
            audio.add(USLT(
                encoding=3,
                lang='eng',
                desc='Lyrics',
                text=metadata["lyric"]
            ))

        # Year
        if metadata.get("created"):
            year = metadata["created"][:4]
            audio.add(TDRC(encoding=3, text=year))

        # Save changes to file
        audio.save(mp3_path)

    except Exception as e:
        print(f"Metadata Apply Error: {e}")