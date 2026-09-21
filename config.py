import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN is not set in environment or .env file.", file=sys.stderr)
    print("Please copy .env.example to .env and add your Telegram bot token.", file=sys.stderr)

DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Telegram standard bot upload limit is 50MB (using 49.5 MB for safety margin)
MAX_AUDIO_BYTES = int(49.5 * 1024 * 1024)

# Throttling interval for Telegram message edits in seconds
PROGRESS_UPDATE_INTERVAL = float(os.getenv("PROGRESS_UPDATE_INTERVAL", 2.0))

# Network timeouts
NETWORK_TIMEOUT = 30

# Spotify credentials (optional, zero-credential scraping used as fallback)
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()

# SoundCloud client ID (optional, dynamic scraping used if not provided)
SOUNDCLOUD_CLIENT_ID = os.getenv("SOUNDCLOUD_CLIENT_ID", "").strip()

# Proxy configuration (optional, for Telegram API, yt-dlp, and streaming)
# Supports PROXY_URL from .env or standard HTTP_PROXY/HTTPS_PROXY/ALL_PROXY
raw_proxy = (
    os.getenv("PROXY_URL", "").strip()
    or os.getenv("HTTPS_PROXY", "").strip()
    or os.getenv("HTTP_PROXY", "").strip()
    or os.getenv("ALL_PROXY", "").strip()
)
if raw_proxy and not (raw_proxy.startswith("http://") or raw_proxy.startswith("https://") or raw_proxy.startswith("socks")):
    PROXY_URL = f"http://{raw_proxy}"
else:
    PROXY_URL = raw_proxy

if PROXY_URL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL


def get_ffmpeg_binary() -> str | None:
    """Locate FFmpeg executable: custom path, imageio-ffmpeg package, or system PATH."""
    custom = os.getenv("FFMPEG_PATH")
    if custom and os.path.exists(custom):
        return custom
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        import shutil
        return shutil.which("ffmpeg")


FFMPEG_PATH = get_ffmpeg_binary()
