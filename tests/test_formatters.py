import unittest
from services.base import TrackInfo
from bot.formatters import (
    get_service_badge,
    format_duration,
    format_progress_bar,
    format_caption,
)


class TestFormatters(unittest.TestCase):

    def test_get_service_badge(self):
        self.assertEqual(get_service_badge("Radio Javan"), "📻 Radio Javan")
        self.assertEqual(get_service_badge("Radio Javan Podcast"), "📻 Radio Javan")
        self.assertEqual(get_service_badge("SoundCloud"), "☁️ SoundCloud")
        self.assertEqual(get_service_badge("Spotify"), "🟢 Spotify")
        self.assertEqual(get_service_badge("CustomSource"), "📡 CustomSource")
        self.assertEqual(get_service_badge(None), "🎵 Music")

    def test_format_duration(self):
        self.assertEqual(format_duration(45), "0:45")
        self.assertEqual(format_duration(215), "3:35")
        self.assertEqual(format_duration(3665), "1:01:05")
        self.assertEqual(format_duration(None), "N/A")
        self.assertEqual(format_duration("invalid"), "N/A")

    def test_format_progress_bar(self):
        # Basic percent only
        bar = format_progress_bar(50)
        self.assertIn("50%", bar)
        self.assertIn("█", bar)

        # With downloaded and total bytes
        bar_bytes = format_progress_bar(
            percent=50,
            downloaded_bytes=5 * 1024 * 1024,
            total_bytes=10 * 1024 * 1024,
        )
        self.assertIn("50%", bar_bytes)
        self.assertIn("5.0 / 10.0 MB", bar_bytes)

        # Clamping at 0 and 100
        self.assertIn("0%", format_progress_bar(-10))
        self.assertIn("100%", format_progress_bar(150))

    def test_format_caption(self):
        track = TrackInfo(
            title="A <Test> & Song",
            artist="Artist & Friends",
            download_url="https://example.com/audio.mp3",
            album="Greatest Hits",
            duration=180,
            year="2026",
            source="Spotify",
            lyrics="Line 1\nLine 2\n" + ("Long lyric sentence. " * 50),
            share_url="https://open.spotify.com/track/123",
        )
        caption = format_caption(track)
        # HTML entities properly escaped
        self.assertIn("A &lt;Test&gt; &amp; Song", caption)
        self.assertIn("Artist &amp; Friends", caption)
        self.assertIn("🟢 Spotify", caption)
        self.assertIn("3:00", caption)
        self.assertIn("2026", caption)
        # Length under Telegram limit
        self.assertLessEqual(len(caption), 1024)


if __name__ == "__main__":
    unittest.main()
