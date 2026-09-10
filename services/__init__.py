from typing import List, Optional
from services.base import BaseMusicService, TrackInfo
from services.radiojavan import RadioJavanService
from services.soundcloud import SoundCloudService
from services.spotify import SpotifyService

# Registry of active music services
SERVICES: List[BaseMusicService] = [
    RadioJavanService(),
    SoundCloudService(),
    SpotifyService(),
]


def find_service(url: str) -> Optional[BaseMusicService]:
    """Find a registered music service that can handle the URL."""
    for service in SERVICES:
        if service.can_handle(url):
            return service
    return None


__all__ = [
    "BaseMusicService",
    "TrackInfo",
    "RadioJavanService",
    "SoundCloudService",
    "SpotifyService",
    "find_service",
    "SERVICES",
]
