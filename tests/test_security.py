import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess

from utils.downloader import download_stream
from utils.audio import convert_to_mp3
from services.radiojavan import _is_valid_rj_url
from services.soundcloud import _is_valid_soundcloud_url
from services.spotify import _is_valid_spotify_url


class TestSecurityHardening(unittest.TestCase):

    def test_ssrf_domain_allowlists(self):
        # Valid URLs
        self.assertTrue(_is_valid_rj_url("https://www.radiojavan.com/mp3s/mp3/test"))
        self.assertTrue(_is_valid_rj_url("https://play.radiojavan.com/song/test"))
        self.assertTrue(_is_valid_rj_url("https://rj.app/m/12345"))
        self.assertTrue(_is_valid_rj_url("radiojavan://song/test"))

        self.assertTrue(_is_valid_soundcloud_url("https://soundcloud.com/artist/track"))
        self.assertTrue(_is_valid_soundcloud_url("https://m.soundcloud.com/artist/track"))
        self.assertTrue(_is_valid_soundcloud_url("https://on.soundcloud.com/abcde"))

        self.assertTrue(_is_valid_spotify_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"))
        self.assertTrue(_is_valid_spotify_url("https://spotify.link/AbCdEfGh"))
        self.assertTrue(_is_valid_spotify_url("spotify:track:4cOdK2wGLETKBW3PvgPWqT"))

        # Malicious SSRF URLs
        self.assertFalse(_is_valid_rj_url("http://169.254.169.254/latest/meta-data/#radiojavan.com"))
        self.assertFalse(_is_valid_rj_url("http://attacker.com/evil?ref=radiojavan.com"))
        self.assertFalse(_is_valid_rj_url("http://radiojavan.com.evil.com/"))
        self.assertFalse(_is_valid_rj_url("file:///etc/passwd"))

        self.assertFalse(_is_valid_soundcloud_url("http://127.0.0.1:8080/on.soundcloud.com"))
        self.assertFalse(_is_valid_soundcloud_url("http://attacker.com/soundcloud.com/test"))
        self.assertFalse(_is_valid_soundcloud_url("http://soundcloud.com.evil.com/"))

        self.assertFalse(_is_valid_spotify_url("http://169.254.169.254/open.spotify.com"))
        self.assertFalse(_is_valid_spotify_url("http://evil.com/page?track=spotify.com"))
        self.assertFalse(_is_valid_spotify_url("http://spotify.link.evil.com/"))

    @patch("requests.get")
    def test_download_stream_aborts_on_excessive_content_length(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": str(100 * 1024 * 1024)}  # 100 MB
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value.__enter__.return_value = mock_resp

        target_file = Path("test_oversized.tmp")
        try:
            with self.assertRaises(ValueError) as ctx:
                download_stream(
                    "https://example.com/oversized.mp3",
                    target_file,
                    max_bytes=10 * 1024 * 1024,  # 10 MB limit
                )
            self.assertIn("exceeds maximum allowed limit", str(ctx.exception))
        finally:
            if target_file.exists():
                target_file.unlink()

    @patch("requests.get")
    def test_download_stream_aborts_on_unbounded_chunk_stream(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.headers = {}  # No Content-Length
        mock_resp.raise_for_status = MagicMock()
        # Yield 3 chunks of 1 MB each
        mock_resp.iter_content.return_value = [b"x" * (1024 * 1024)] * 3
        mock_get.return_value.__enter__.return_value = mock_resp

        target_file = Path("test_stream_limit.tmp")
        try:
            with self.assertRaises(ValueError) as ctx:
                download_stream(
                    "https://example.com/infinite.mp3",
                    target_file,
                    max_bytes=2 * 1024 * 1024,  # 2 MB limit
                )
            self.assertIn("exceeded maximum allowed limit", str(ctx.exception))
        finally:
            if target_file.exists():
                target_file.unlink()

    @patch("subprocess.run")
    def test_convert_to_mp3_timeout_protection(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)

        with patch("config.FFMPEG_PATH", "ffmpeg"):
            with self.assertRaises(RuntimeError) as ctx:
                convert_to_mp3(Path("in.m4a"), Path("out.mp3"), timeout=10)
            self.assertIn("timed out after 10 seconds", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
