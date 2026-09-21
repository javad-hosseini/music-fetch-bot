from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Callable


@dataclass
class TrackInfo:
    title: str
    artist: str
    download_url: str
    album: Optional[str] = None
    duration: Optional[int] = None
    year: Optional[str] = None
    format: str = "mp3"  # 'mp3' or 'm4a'
    cover_url: Optional[str] = None
    lyrics: Optional[str] = None
    source: str = "Unknown"
    share_url: Optional[str] = None
    plays: Optional[Any] = None
    likes: Optional[Any] = None

    def __post_init__(self):
        if self.title is not None:
            self.title = str(self.title)
        if self.artist is not None:
            self.artist = str(self.artist)
        if self.download_url is not None:
            self.download_url = str(self.download_url)
        if self.share_url is not None:
            self.share_url = str(self.share_url)
        if self.cover_url is not None:
            self.cover_url = str(self.cover_url)


class BaseMusicService(ABC):
    """
    Abstract interface for music providers.
    Extend this class to add support for other services (Spotify, SoundCloud, etc.).
    """

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this service can handle the given URL."""
        pass

    @abstractmethod
    def fetch_track(self, url: str) -> TrackInfo:
        """Extract metadata and stream/download URL for the track."""
        pass

    def download_track(
        self,
        track: TrackInfo,
        target_path: Path,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> int:
        """
        Download track to target_path. By default, uses standard HTTP streaming downloader.
        Services requiring custom downloading (like HLS or yt-dlp) can override this method.
        """
        from utils.downloader import download_stream
        return download_stream(track.download_url, target_path, on_progress=on_progress)
