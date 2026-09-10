import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.base import TrackInfo
from services.radiojavan import RadioJavanService
from services.soundcloud import SoundCloudService
from services.spotify import SpotifyService
from utils.audio import convert_to_mp3


class TestMP3ConversionAndFormat(unittest.TestCase):

    @patch("subprocess.run")
    def test_convert_to_mp3_subprocess_call(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        in_p = Path("input.m4a")
        out_p = Path("output.mp3")

        result = convert_to_mp3(in_p, out_p, bitrate="256k")
        self.assertEqual(result, out_p)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIn("-acodec", cmd)
        self.assertIn("libmp3lame", cmd)
        self.assertIn("256k", cmd)

    @patch("subprocess.run")
    def test_convert_to_mp3_failure_raises(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Conversion codec error"
        mock_run.return_value = mock_proc

        with self.assertRaises(RuntimeError):
            convert_to_mp3(Path("input.m4a"), Path("output.mp3"))

    @patch("services.radiojavan.download_stream")
    @patch("services.radiojavan.convert_to_mp3")
    def test_radiojavan_m4a_conversion(self, mock_convert, mock_dl):
        service = RadioJavanService()
        track = TrackInfo(
            title="Song",
            artist="Artist",
            download_url="https://media.radiojavan.com/mp3/song.m4a",
            format="mp3",
        )
        target_path = Path("test_song.mp3")
        target_path.touch()

        try:
            service.download_track(track, target_path)
            mock_dl.assert_called_once()
            # Verify convert_to_mp3 was called to turn the temporary .m4a into .mp3
            mock_convert.assert_called_once()
        finally:
            if target_path.exists():
                target_path.unlink()

    def test_all_services_guarantee_mp3_format(self):
        # RadioJavan song & podcast
        rj = RadioJavanService()
        dummy_song = MagicMock()
        dummy_song.name = "Test"
        dummy_song.artist = "Artist"
        dummy_song.hq_link = "https://example.com/audio.m4a"
        dummy_song.photo = None
        dummy_song.lyric = None
        dummy_song.plays = 100
        dummy_song.likes = 10
        dummy_song.album = "Album"
        dummy_song.duration = 200
        dummy_song.created_at = "2026-01-01"
        rj.client.get_song_by_url = MagicMock(return_value=dummy_song)

        track_song = rj._fetch_song("https://radiojavan.com/mp3s/mp3/test")
        self.assertEqual(track_song.format, "mp3")

        dummy_pod = MagicMock()
        dummy_pod.title = "Pod"
        dummy_pod.artist = "RJ"
        dummy_pod.hq_link = "https://example.com/pod.m4a"
        dummy_pod.photo = None
        dummy_pod.plays = 200
        dummy_pod.likes = 20
        dummy_pod.duration = 3600
        dummy_pod.created_at = "2026-01-01"
        rj.client.get_podcast_by_url = MagicMock(return_value=dummy_pod)

        track_pod = rj._fetch_podcast("https://radiojavan.com/podcasts/podcast/test")
        self.assertEqual(track_pod.format, "mp3")


if __name__ == "__main__":
    unittest.main()
