import re
import html
import logging
from typing import Optional
import urllib.parse
import urllib.request
import json

import config

logger = logging.getLogger(__name__)

# Pattern to match and remove Genius header/footer artifacts
GENIUS_CONTRIBUTORS_PATTERN = re.compile(r"^\d+\s+Contributors?.*$", re.MULTILINE)
GENIUS_EMBED_PATTERN = re.compile(r"\d*Embed$", re.MULTILINE)
TITLE_CLEANUP_PATTERN = re.compile(
    r"\s*[\(\[\{](?:official\s*(?:video|audio|music\s*video|lyrics?\s*video|visualizer)?|lyrics?(?:\s*video)?|audio|hd|4k|hq|live|remastered|explicit)[\)\]\}]",
    re.IGNORECASE,
)


def clean_query_term(text: str) -> str:
    """Clean video/track titles by stripping extraneous tags like '(Official Video)'."""
    if not text:
        return ""
    cleaned = TITLE_CLEANUP_PATTERN.sub("", text)
    # Remove excessive punctuation or trailing dashes
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|:")
    return cleaned


def clean_lyrics_text(raw_lyrics: str) -> str:
    """Strip Genius and scraping artifacts from lyrics text."""
    if not raw_lyrics:
        return ""

    text = raw_lyrics.strip()

    # Remove '123 Contributors' lines at start
    text = GENIUS_CONTRIBUTORS_PATTERN.sub("", text).strip()

    # Remove the first line if it's just 'Artist - Song Lyrics' or similar
    lines = text.splitlines()
    if lines and re.search(r"lyrics\s*$", lines[0], re.IGNORECASE):
        lines = lines[1:]
        text = "\n".join(lines).strip()

    # Remove trailing 'Embed' or '123Embed'
    text = GENIUS_EMBED_PATTERN.sub("", text).strip()

    # Normalize excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_from_genius(title: str, artist: str) -> Optional[str]:
    """Fetch lyrics from Genius using lyricsgenius if token is configured."""
    if not config.GENIUS_ACCESS_TOKEN:
        return None

    try:
        import lyricsgenius

        clean_t = clean_query_term(title)
        clean_a = clean_query_term(artist)

        genius = lyricsgenius.Genius(
            config.GENIUS_ACCESS_TOKEN,
            verbose=False,
            remove_section_headers=False,
            timeout=8,
            retries=1,
        )

        song = None
        # First search with artist and title
        if clean_a:
            song = genius.search_song(clean_t, clean_a)
        if not song:
            song = genius.search_song(f"{clean_a} {clean_t}".strip())

        if song and song.lyrics:
            cleaned = clean_lyrics_text(song.lyrics)
            if cleaned:
                logger.info(f"Genius lyrics found for '{clean_a} - {clean_t}'")
                return cleaned
    except Exception as e:
        logger.debug(f"Genius lyrics search failed for '{artist} - {title}': {e}")

    return None


def fetch_from_lrclib(title: str, artist: str) -> Optional[str]:
    """Fetch lyrics from open-source LRCLIB API without requiring any API token."""
    clean_t = clean_query_term(title)
    clean_a = clean_query_term(artist)

    # 1. Direct match endpoint
    query_params = {"track_name": clean_t}
    if clean_a:
        query_params["artist_name"] = clean_a

    url = f"https://lrclib.net/api/get?{urllib.parse.urlencode(query_params)}"

    headers = {
        "User-Agent": "MusicDownloaderBot/1.2 (https://github.com)",
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)
    proxies = {}
    if config.PROXY_URL:
        proxies["http"] = config.PROXY_URL
        proxies["https"] = config.PROXY_URL

    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))

    try:
        with opener.open(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8", errors="ignore"))
                lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
                if lyrics:
                    # If synced lyrics (with timestamps [00:12.34]), strip timestamps for plain view
                    plain = re.sub(r"\[\d{2}:\d{2}\.\d+\]\s*", "", lyrics)
                    cleaned = clean_lyrics_text(plain)
                    if cleaned:
                        logger.info(f"LRCLIB lyrics matched for '{clean_a} - {clean_t}'")
                        return cleaned
    except Exception as e:
        logger.debug(f"LRCLIB get failed for '{clean_a} - {clean_t}': {e}")

    # 2. Search fallback endpoint
    try:
        search_query = f"{clean_a} {clean_t}".strip()
        search_url = f"https://lrclib.net/api/search?{urllib.parse.urlencode({'q': search_query})}"
        search_req = urllib.request.Request(search_url, headers=headers)
        with opener.open(search_req, timeout=6) as search_resp:
            if search_resp.status == 200:
                results = json.loads(search_resp.read().decode("utf-8", errors="ignore"))
                if isinstance(results, list) and len(results) > 0:
                    for item in results:
                        lyrics = item.get("plainLyrics") or item.get("syncedLyrics")
                        if lyrics:
                            plain = re.sub(r"\[\d{2}:\d{2}\.\d+\]\s*", "", lyrics)
                            cleaned = clean_lyrics_text(plain)
                            if cleaned:
                                logger.info(f"LRCLIB search fallback matched for '{search_query}'")
                                return cleaned
    except Exception as ex:
        logger.debug(f"LRCLIB search fallback failed for '{clean_a} - {clean_t}': {ex}")

    return None


def fetch_lyrics(title: str, artist: str = "") -> Optional[str]:
    """
    Main lyrics resolver:
    1. Tries Genius if GENIUS_ACCESS_TOKEN is configured.
    2. Falls back to free LRCLIB (open-source music lyrics database).
    """
    if not title:
        return None

    # Try Genius first if token exists
    if config.GENIUS_ACCESS_TOKEN:
        lyrics = fetch_from_genius(title, artist)
        if lyrics:
            return lyrics

    # Try LRCLIB (zero-credential)
    lyrics = fetch_from_lrclib(title, artist)
    if lyrics:
        return lyrics

    return None
