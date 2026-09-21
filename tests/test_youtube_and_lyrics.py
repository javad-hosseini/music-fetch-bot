import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.base import TrackInfo
from services.youtube import (
    YouTubeMusicService,
    _is_valid_youtube_url,
    parse_title_artist,
)
from utils.lyrics import (
    clean_lyrics_text,
    clean_query_term,
    fetch_lyrics,
)
from bot.keyboards import (
    store_lyrics,
    get_cached_lyrics,
    audio_action_keyboard,
    platforms_menu_keyboard,
)
from bot.formatters import get_service_badge


class TestYouTubeAndLyrics(unittest.TestCase):
    def setUp(self):
        self.yt_service = YouTubeMusicService()

    def test_youtube_url_validation(self):
        valid_urls = [
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        ]
        for url in valid_urls:
            self.assertTrue(self.yt_service.can_handle(url), f"Should handle {url}")

        invalid_urls = [
            "https://malicious-youtube.com/watch?v=dQw4w9WgXcQ",
            "https://attacker.com/?url=youtube.com",
            "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://soundcloud.com/artist/track",
            "not a url",
            "",
        ]
        for url in invalid_urls:
            self.assertFalse(self.yt_service.can_handle(url), f"Should not handle {url}")

    def test_parse_title_artist(self):
        t1, a1 = parse_title_artist("Adele - Hello (Official Music Video)", "AdeleVEVO")
        self.assertEqual(t1, "Hello")
        self.assertEqual(a1, "Adele")

        t2, a2 = parse_title_artist("Mohsen Yeganeh - Behet Ghol Midam [Live]", "Mohsen Yeganeh")
        self.assertEqual(t2, "Behet Ghol Midam")
        self.assertEqual(a2, "Mohsen Yeganeh")

        t3, a3 = parse_title_artist("Alone (Audio)", "Marshmello - Topic")
        self.assertEqual(t3, "Alone")
        self.assertEqual(a3, "Marshmello")

    def test_clean_lyrics_text(self):
        raw = "42 Contributors\nAdele - Hello Lyrics\nHello, it's me\nI was wondering\n123Embed"
        cleaned = clean_lyrics_text(raw)
        self.assertNotIn("Contributors", cleaned)
        self.assertNotIn("Hello Lyrics", cleaned)
        self.assertNotIn("Embed", cleaned)
        self.assertIn("Hello, it's me", cleaned)

    def test_clean_query_term(self):
        self.assertEqual(clean_query_term("Song Title (Official Video)"), "Song Title")
        self.assertEqual(clean_query_term("Track Name [Lyrics Video]"), "Track Name")
        self.assertEqual(clean_query_term("Audio HD {Remastered}"), "Audio HD")

    def test_lyrics_caching_and_keyboard(self):
        key = store_lyrics("My Song", "My Artist", "Sample song lyrics line 1\nline 2")
        self.assertIsNotNone(key)
        cached = get_cached_lyrics(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["title"], "My Song")
        self.assertEqual(cached["lyrics"], "Sample song lyrics line 1\nline 2")

        track_with_lyrics = TrackInfo(
            title="Song",
            artist="Artist",
            download_url="https://youtube.com/watch?v=123",
            lyrics="Some lyrics text",
            share_url="https://youtube.com/watch?v=123",
        )
        kb = audio_action_keyboard(track_with_lyrics)
        # Verify lyrics button is present in keyboard
        button_texts = [btn.text for row in kb.keyboard for btn in row]
        self.assertTrue(any("Lyrics" in txt for txt in button_texts))

    def test_service_badges(self):
        self.assertEqual(get_service_badge("YouTube Music"), "🔴 YouTube Music")
        self.assertEqual(get_service_badge("YouTube"), "▶️ YouTube")

    def test_platforms_menu_contains_youtube(self):
        kb = platforms_menu_keyboard()
        button_texts = [btn.text for row in kb.keyboard for btn in row]
        self.assertTrue(any("YouTube" in txt for txt in button_texts))

    @patch("yt_dlp.YoutubeDL")
    def test_youtube_fetch_track_mocked(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "title": "Adele - Hello (Official Video)",
            "artist": "Adele",
            "track": "Hello",
            "album": "25",
            "duration": 295,
            "upload_date": "20151023",
            "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "view_count": 1000000,
            "like_count": 50000,
        }
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        track = self.yt_service.fetch_track("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(track.title, "Hello")
        self.assertEqual(track.artist, "Adele")
        self.assertEqual(track.album, "25")
        self.assertEqual(track.source, "YouTube Music")
        self.assertEqual(track.duration, 295)


if __name__ == "__main__":
    unittest.main()
