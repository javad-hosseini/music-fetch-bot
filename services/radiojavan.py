import re
import requests
from pathlib import Path
from typing import Optional, Callable
from radiojavanapi import Client
from services.base import BaseMusicService, TrackInfo
from utils.downloader import download_stream
from utils.audio import convert_to_mp3


class RadioJavanService(BaseMusicService):
    """
    Music service provider for Radio Javan (Songs and Podcasts).
    Enforces universal MP3 output by auto-converting M4A streams to MP3.
    """

    def __init__(self):
        self.client = Client()

    def can_handle(self, url: str) -> bool:
        """Check if URL belongs to Radio Javan."""
        if not url:
            return False
        patterns = [
            r"radiojavan\.com",
            r"rj\.app",
            r"radiojavan:\/\/",
        ]
        return any(re.search(p, url, re.IGNORECASE) for p in patterns)

    def resolve_url(self, raw_url: str, timeout: int = 10) -> Optional[str]:
        """Resolve redirects (e.g. rj.app short links) into canonical URLs."""
        try:
            # Extract clean URL if surrounded by other text
            url_match = re.search(r"https?://[^\s]+", raw_url)
            target = url_match.group(0) if url_match else raw_url

            resp = requests.get(target, allow_redirects=True, timeout=timeout)
            final_url = resp.url
            if "radiojavan://" in final_url:
                # If redirect was intercepted by custom scheme, fallback to target
                return target
            return final_url
        except Exception:
            return raw_url

    def fetch_track(self, raw_url: str) -> TrackInfo:
        """Fetch track metadata and stream/download URL."""
        resolved_url = self.resolve_url(raw_url) or raw_url

        if "podcast" in resolved_url.lower():
            return self._fetch_podcast(resolved_url)
        else:
            return self._fetch_song(resolved_url)

    def _fetch_song(self, url: str) -> TrackInfo:
        song = self.client.get_song_by_url(url)
        if not song:
            raise ValueError("Song not found or invalid Radio Javan link.")

        download_url = str(song.hq_link or song.lq_link or song.link or "")
        if not download_url:
            raise ValueError("No download stream found for this song.")

        created_at = getattr(song, "created_at", None)
        year = str(created_at)[:4] if created_at else None

        title = getattr(song, "name", None) or getattr(song, "title", "Unknown Track")
        artist = getattr(song, "artist", "Radio Javan")

        return TrackInfo(
            title=title,
            artist=artist,
            download_url=download_url,
            album=getattr(song, "album", None),
            duration=getattr(song, "duration", None),
            year=year,
            format="mp3",
            cover_url=str(song.photo) if getattr(song, "photo", None) else None,
            lyrics=getattr(song, "lyric", None),
            source="Radio Javan",
            share_url=getattr(song, "share_link", url),
            plays=getattr(song, "plays", None),
            likes=getattr(song, "likes", None),
        )

    def _fetch_podcast(self, url: str) -> TrackInfo:
        podcast = self.client.get_podcast_by_url(url)
        if not podcast:
            raise ValueError("Podcast not found or invalid Radio Javan link.")

        download_url = str(getattr(podcast, "hq_link", None) or getattr(podcast, "link", None) or "")
        if not download_url:
            raise ValueError("No download stream found for this podcast.")

        created_at = getattr(podcast, "created_at", None)
        year = str(created_at)[:4] if created_at else None

        title = getattr(podcast, "title", "Radio Javan Podcast")
        artist = getattr(podcast, "artist", "Radio Javan")

        return TrackInfo(
            title=title,
            artist=artist,
            download_url=download_url,
            album="Radio Javan Podcasts",
            duration=getattr(podcast, "duration", None),
            year=year,
            format="mp3",
            cover_url=str(podcast.photo) if getattr(podcast, "photo", None) else None,
            lyrics=None,
            source="Radio Javan Podcast",
            share_url=getattr(podcast, "share_link", url),
            plays=getattr(podcast, "plays", None),
            likes=getattr(podcast, "likes", None),
        )

    def download_track(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> int:
        """
        Download Radio Javan track. If source stream is M4A, download and convert to MP3.
        Always outputs a strict MP3 file at target_path.
        """
        is_m4a = ".m4a" in track.download_url.lower()

        if is_m4a:
            temp_m4a = target_path.with_suffix(".m4a")
            try:
                download_stream(track.download_url, temp_m4a, on_progress=on_progress)
                # Convert downloaded M4A to target MP3
                convert_to_mp3(temp_m4a, target_path)
                return target_path.stat().st_size
            finally:
                if temp_m4a.exists():
                    try:
                        temp_m4a.unlink()
                    except Exception:
                        pass
        else:
            return download_stream(track.download_url, target_path, on_progress=on_progress)
