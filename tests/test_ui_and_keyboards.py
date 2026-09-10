import unittest
from unittest.mock import MagicMock, patch

from services.base import TrackInfo
from bot.keyboards import (
    main_menu_keyboard,
    platforms_menu_keyboard,
    platform_detail_keyboard,
    back_to_main_keyboard,
    audio_action_keyboard,
    error_keyboard,
    oversized_file_keyboard,
)
from bot.bot import setup_bot_commands


class TestKeyboardsAndUI(unittest.TestCase):

    def test_main_menu_keyboard(self):
        markup = main_menu_keyboard()
        self.assertIsNotNone(markup)
        callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
        self.assertIn("ui_help", callbacks)
        self.assertIn("ui_platforms", callbacks)
        self.assertIn("ui_ping", callbacks)
        self.assertIn("ui_about", callbacks)

    def test_platforms_menu_keyboard(self):
        markup = platforms_menu_keyboard()
        self.assertIsNotNone(markup)
        callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
        self.assertIn("ui_plat_rj", callbacks)
        self.assertIn("ui_plat_sc", callbacks)
        self.assertIn("ui_plat_sp", callbacks)
        self.assertIn("ui_main", callbacks)

    def test_platform_detail_keyboard(self):
        markup = platform_detail_keyboard()
        callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
        self.assertIn("ui_platforms", callbacks)
        self.assertIn("ui_main", callbacks)

    def test_back_to_main_keyboard(self):
        markup = back_to_main_keyboard()
        callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
        self.assertIn("ui_main", callbacks)

    def test_audio_action_keyboard_with_share_url(self):
        track = TrackInfo(
            title="Song",
            artist="Artist",
            download_url="https://cf-media.sndcdn.com/stream.mp3",
            share_url="https://soundcloud.com/artist/song"
        )
        markup = audio_action_keyboard(track)
        urls = [btn.url for row in markup.keyboard for btn in row]
        self.assertIn("https://soundcloud.com/artist/song", urls)

    def test_oversized_file_keyboard(self):
        markup = oversized_file_keyboard("https://example.com/huge.mp3")
        urls = [btn.url for row in markup.keyboard for btn in row if btn.url]
        self.assertIn("https://example.com/huge.mp3", urls)

    def test_setup_bot_commands(self):
        mock_bot = MagicMock()
        setup_bot_commands(mock_bot)
        mock_bot.set_my_commands.assert_called_once()
        args, _ = mock_bot.set_my_commands.call_args
        commands = args[0]
        cmd_names = [c.command for c in commands]
        self.assertIn("start", cmd_names)
        self.assertIn("help", cmd_names)
        self.assertIn("platforms", cmd_names)
        self.assertIn("ping", cmd_names)
        self.assertIn("about", cmd_names)


if __name__ == "__main__":
    unittest.main()
