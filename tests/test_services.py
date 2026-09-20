import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services import find_service, RadioJavanService, SoundCloudService, SpotifyService
from services.base import TrackInfo


class TestServices(unittest.TestCase):

    def test_find_service_detection(self):
        # Radio Javan
        rj_urls = [
            "https://www.radiojavan.com/mp3s/mp3/Shadmehr-Aghili-Barandeh",
            "https://rj.app/m/2qk8P3l9",
            "radiojavan://song/test-song",
        ]
        for url in rj_urls:
            service = find_service(url)
            self.assertIsNotNone(service, f"Failed to match RJ URL: {url}")
            self.assertIsInstance(service, RadioJavanService)

        # SoundCloud
        sc_urls = [
            "https://soundcloud.com/artist/track-name",
            "https://m.soundcloud.com/artist/track-name",
            "https://on.soundcloud.com/abcde",
        ]
        for url in sc_urls:
            service = find_service(url)
            self.assertIsNotNone(service, f"Failed to match SoundCloud URL: {url}")
            self.assertIsInstance(service, SoundCloudService)

        # Spotify
        sp_urls = [
            "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
            "https://open.spotify.com/intl-de/track/4cOdK2wGLETKBW3PvgPWqT?si=123",
            "https://spotify.link/AbCdEfGh",
            "spotify:track:4cOdK2wGLETKBW3PvgPWqT",
        ]
        for url in sp_urls:
            service = find_service(url)
            self.assertIsNotNone(service, f"Failed to match Spotify URL: {url}")
            self.assertIsInstance(service, SpotifyService)

        # Unknown & SSRF injection attempt URLs (must be rejected)
        self.assertIsNone(find_service("https://youtube.com/watch?v=12345"))
        self.assertIsNone(find_service("https://example.com/audio.mp3"))
        self.assertIsNone(find_service("http://169.254.169.254/latest/meta-data/#radiojavan.com"))
        self.assertIsNone(find_service("http://attacker.com/evil?ref=radiojavan.com"))
        self.assertIsNone(find_service("http://radiojavan.com.attacker.com/path"))
        self.assertIsNone(find_service("http://attacker.com/soundcloud.com/exploit"))
        self.assertIsNone(find_service("http://127.0.0.1:8080/on.soundcloud.com"))
        self.assertIsNone(find_service("http://evil.com/page?track=spotify.com"))
        self.assertIsNone(find_service("http://spotify.link.evil.com/steal"))

    def test_spotify_extract_track_id(self):
        service = SpotifyService()
        self.assertEqual(
            service.extract_track_id("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"),
            "4cOdK2wGLETKBW3PvgPWqT"
        )
        self.assertEqual(
            service.extract_track_id("https://open.spotify.com/intl-fr/track/4cOdK2wGLETKBW3PvgPWqT?si=xyz"),
            "4cOdK2wGLETKBW3PvgPWqT"
        )
        self.assertEqual(
            service.extract_track_id("spotify:track:4cOdK2wGLETKBW3PvgPWqT"),
            "4cOdK2wGLETKBW3PvgPWqT"
        )
        with self.assertRaises(ValueError):
            service.extract_track_id("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")

    @patch("requests.get")
    def test_soundcloud_fetch_track_progressive(self, mock_get):
        service = SoundCloudService()
        service._cached_client_id = "test_client_id"
        service._client_id_expires_at = 9999999999.0

        # Mock resolve response
        resolve_resp = MagicMock()
        resolve_resp.status_code = 200
        resolve_resp.json.return_value = {
            "kind": "track",
            "title": "Echoes",
            "user": {"username": "Pink Floyd"},
            "artwork_url": "https://i1.sndcdn.com/artworks-large.jpg",
            "duration": 1400000,
            "created_at": "1971-11-05T00:00:00Z",
            "permalink_url": "https://soundcloud.com/pink-floyd/echoes",
            "playback_count": 50000,
            "likes_count": 1200,
            "description": "Echoes by Pink Floyd",
            "media": {
                "transcodings": [
                    {
                        "url": "https://api-v2.soundcloud.com/media/stream/progressive",
                        "format": {"protocol": "progressive", "mime_type": "audio/mpeg"},
                    }
                ]
            }
        }

        # Mock stream url response
        stream_resp = MagicMock()
        stream_resp.status_code = 200
        stream_resp.json.return_value = {
            "url": "https://cf-media.sndcdn.com/stream-progressive.mp3"
        }

        mock_get.side_effect = [resolve_resp, stream_resp]

        track = service.fetch_track("https://soundcloud.com/pink-floyd/echoes")
        self.assertEqual(track.title, "Echoes")
        self.assertEqual(track.artist, "Pink Floyd")
        self.assertEqual(track.download_url, "https://cf-media.sndcdn.com/stream-progressive.mp3")
        self.assertEqual(track.cover_url, "https://i1.sndcdn.com/artworks-t500x500.jpg")
        self.assertEqual(track.year, "1971")
        self.assertEqual(track.duration, 1400)
        self.assertEqual(track.source, "SoundCloud")

    @patch("requests.get")
    def test_spotify_fetch_track_embed(self, mock_get):
        service = SpotifyService()

        embed_html = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "state": {
                        "data": {
                            "entity": {
                                "name": "Bohemian Rhapsody",
                                "artists": [{"name": "Queen"}],
                                "duration": 354000,
                                "releaseDate": {"isoString": "1975-10-31T00:00:00Z"},
                                "visualIdentity": {
                                    "image": [{"url": "https://image-cdn-ak.spotifycdn.com/image/ab67616d00001e02123456"}]
                                }
                            }
                        }
                    }
                }
            }
        }
        </script>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = embed_html
        mock_get.return_value = mock_resp

        track = service.fetch_track("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
        self.assertEqual(track.title, "Bohemian Rhapsody")
        self.assertEqual(track.artist, "Queen")
        self.assertEqual(track.duration, 354)
        self.assertEqual(track.year, "1975")
        self.assertEqual(track.cover_url, "https://image-cdn-ak.spotifycdn.com/image/ab67616d0000b273123456")
        self.assertEqual(track.source, "Spotify")

    @patch("yt_dlp.YoutubeDL")
    def test_spotify_download_track(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        service = SpotifyService()
        track = TrackInfo(
            title="Song",
            artist="Artist",
            download_url="https://open.spotify.com/track/123",
            duration=200,
        )

        test_path = Path("test_spotify_song.mp3")
        try:
            # Create dummy target file to simulate yt-dlp output
            test_path.write_bytes(b"dummy audio content")

            bytes_written = service.download_track(track, test_path)
            self.assertEqual(bytes_written, len(b"dummy audio content"))
            mock_ydl.download.assert_called_once()
        finally:
            if test_path.exists():
                test_path.unlink()

    @patch("services.soundcloud.download_stream")
    def test_soundcloud_download_track_progressive(self, mock_download_stream):
        mock_download_stream.return_value = 1024
        service = SoundCloudService()
        track = TrackInfo(
            title="SCTrack",
            artist="SCArtist",
            download_url="https://cf-media.sndcdn.com/stream.mp3",
        )
        test_path = Path("test_sc_song.mp3")
        bytes_written = service.download_track(track, test_path)
        self.assertEqual(bytes_written, 1024)
        mock_download_stream.assert_called_once_with("https://cf-media.sndcdn.com/stream.mp3", test_path, on_progress=None)


if __name__ == "__main__":
    unittest.main()
