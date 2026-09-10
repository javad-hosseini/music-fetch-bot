import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.base import TrackInfo
from bot.formatters import (
    get_service_badge,
    format_duration,
    format_progress_bar,
    format_caption,
)
from bot.keyboards import (
    main_menu_keyboard,
    platforms_menu_keyboard,
    platform_detail_keyboard,
    back_to_main_keyboard,
    audio_action_keyboard,
    error_keyboard,
    oversized_file_keyboard,
)
from utils.audio import ensure_mp3, convert_to_mp3


class TestUIAndUX(unittest.TestCase):

    def test_service_badges(self):
        self.assertIn("Radio Javan", get_service_badge("Radio Javan"))
        self.assertIn("SoundCloud", get_service_badge("SoundCloud"))
        self.assertIn("Spotify", get_service_badge("Spotify"))
        self.assertIn("Bandcamp", get_service_badge("Bandcamp"))
        self.assertEqual(get_service_badge(None), "🎵 Music")

    def test_format_duration(self):
        self.assertEqual(format_duration(0), "N/A")
        self.assertEqual(format_duration(None), "N/A")
        self.assertEqual(format_duration(45), "0:45")
        self.assertEqual(format_duration(215), "3:35")
        self.assertEqual(format_duration(3665), "1:01:05")

    def test_progress_bar(self):
        bar_0 = format_progress_bar(0)
        self.assertIn("0%", bar_0)
        self.assertIn("░", bar_0)

        bar_50 = format_progress_bar(50)
        self.assertIn("50%", bar_50)
        self.assertIn("█", bar_50)

        bar_bytes = format_progress_bar(50, downloaded_bytes=5 * 1024 * 1024, total_bytes=10 * 1024 * 1024)
        self.assertIn("5.0 / 10.0 MB", bar_bytes)

    def test_format_caption_length_and_content(self):
        track = TrackInfo(
            title="A" * 100,
            artist="B" * 50,
            download_url="https://example.com/audio.mp3",
            album="Test Album",
            duration=180,
            year="2024",
            source="Spotify",
            lyrics="Long lyrics " * 200,
            share_url="https://open.spotify.com/track/123",
            plays=10000,
            likes=500,
        )
        caption = format_caption(track)
        self.assertLess(len(caption), 1024)
        self.assertIn("Test Album", caption)
        self.assertIn("Lyrics", caption)
        self.assertIn("https://open.spotify.com/track/123", caption)

    def test_keyboards_structure(self):
        main_kb = main_menu_keyboard()
        self.assertIsNotNone(main_kb.keyboard)
        callbacks = [btn.callback_data for row in main_kb.keyboard for btn in row]
        self.assertIn("ui_help", callbacks)
        self.assertIn("ui_platforms", callbacks)
        self.assertIn("ui_ping", callbacks)

        plat_kb = platforms_menu_keyboard()
        plat_callbacks = [btn.callback_data for row in plat_kb.keyboard for btn in row]
        self.assertIn("ui_plat_rj", plat_callbacks)
        self.assertIn("ui_plat_sc", plat_callbacks)
        self.assertIn("ui_plat_sp", plat_callbacks)

        detail_kb = platform_detail_keyboard()
        self.assertEqual(len(detail_kb.keyboard[0]), 2)

        back_kb = back_to_main_keyboard()
        self.assertEqual(back_kb.keyboard[0][0].callback_data, "ui_main")

        track = TrackInfo(
            title="Song",
            artist="Artist",
            download_url="https://example.com/song.mp3",
            share_url="https://example.com/share",
        )
        audio_kb = audio_action_keyboard(track)
        self.assertEqual(audio_kb.keyboard[0][0].url, "https://example.com/share")

        err_kb = error_keyboard()
        self.assertEqual(len(err_kb.keyboard[0]), 2)

        over_kb = oversized_file_keyboard("https://example.com/large.mp3")
        self.assertEqual(over_kb.keyboard[0][0].url, "https://example.com/large.mp3")


class TestMP3Enforcement(unittest.TestCase):

    @patch("utils.audio.MP3")
    def test_ensure_mp3_already_valid(self, mock_mp3):
        mock_mp3.return_value = MagicMock()
        test_file = Path("dummy_valid.mp3")
        result = ensure_mp3(test_file)
        self.assertEqual(result, test_file)
        mock_mp3.assert_called_once_with(test_file)

    @patch("utils.audio.convert_to_mp3")
    @patch("utils.audio.MP3")
    def test_ensure_mp3_converts_non_mp3(self, mock_mp3, mock_convert):
        mock_mp3.side_effect = Exception("Not an MP3")
        source_file = Path("dummy_track.m4a")
        target_mp3 = Path("dummy_track.mp3")

        def fake_convert(inp, out, bitrate="192k"):
            out.write_bytes(b"converted mp3 bytes")
            return out

        mock_convert.side_effect = fake_convert

        source_file.write_bytes(b"dummy m4a content")
        try:
            result = ensure_mp3(source_file)
            self.assertEqual(result.suffix, ".mp3")
            self.assertTrue(target_mp3.exists())
        finally:
            if source_file.exists():
                source_file.unlink()
            if target_mp3.exists():
                target_mp3.unlink()

    @patch("subprocess.run")
    def test_convert_to_mp3_ffmpeg_call(self, mock_subproc):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stderr = ""
        mock_subproc.return_value = mock_res

        with patch("config.FFMPEG_PATH", "ffmpeg"):
            input_p = Path("in.m4a")
            output_p = Path("out.mp3")
            convert_to_mp3(input_p, output_p, bitrate="192k")

            mock_subproc.assert_called_once()
            cmd = mock_subproc.call_args[0][0]
            self.assertEqual(cmd[0], "ffmpeg")
            self.assertIn("-acodec", cmd)
            self.assertIn("libmp3lame", cmd)
            self.assertIn("-b:a", cmd)
            self.assertIn("192k", cmd)


if __name__ == "__main__":
    unittest.main()
