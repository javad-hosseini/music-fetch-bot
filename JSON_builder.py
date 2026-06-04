from radiojavanapi import Client
import json

def build_song_json(song):
    """
    تبدیل آبجکت song به JSON استاندارد
    """
    data = {
        "title": getattr(song, "title", None),
        "artist": getattr(song, "artist", None),
        "name": getattr(song, "name", None),
        "album": getattr(song, "album", None),
        "duration": getattr(song, "duration", None),
        "created": getattr(song, "created_at", None),
        "share_link": str(getattr(song, "share_link", "")),
        "hq_link": str(getattr(song, "hq_link", "")),
        "lq_link": str(getattr(song, "lq_link", "")),
        "stream": str(getattr(song, "link", "")),
        "photo": str(getattr(song, "photo", "")),
        "player_img": str(getattr(song, "photo_player", "")),
        "lyric": getattr(song, "lyric", None)
    }
    return data

def get_song_json(url):
    client = Client()
    song = client.get_song_by_url(url)
    return build_song_json(song)