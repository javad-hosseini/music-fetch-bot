# 🎵 Telegram Music Downloader Bot

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](./LICENSE)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-0088cc.svg?style=flat-square&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![Platforms](https://img.shields.io/badge/Platforms-Radio%20Javan%20%7C%20SoundCloud%20%7C%20Spotify-brightgreen.svg?style=flat-square)](https://github.com/javad-hosseini/music-fetch-bot)
[![Audio Format: MP3](https://img.shields.io/badge/Audio-Universal%20MP3-orange.svg?style=flat-square)](https://github.com/javad-hosseini/music-fetch-bot)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

An extensible, high-performance Telegram bot that downloads songs, podcasts, and audio tracks from **Radio Javan**, **SoundCloud**, and **Spotify** with guaranteed **universal MP3** conversion, embedded ID3 metadata, high-resolution cover artwork, lyrics, and an interactive inline UI with real-time visual progress tracking.

---

## 🌟 Highlights

- **Multi-Platform Support**: Seamlessly parses and downloads tracks from Radio Javan, SoundCloud, and Spotify.
- **Universal MP3 Output**: Enforces strict, guaranteed `.mp3` output format across all platforms using FFmpeg transcoding, embedded ID3v2.3 tags, and high-res cover art.
- **Modern Telegram UI/UX**: Interactive inline menus, command suggestions (`/start`, `/help`, `/platforms`, `/ping`, `/about`), service badges, and quick-action links.
- **High-Fidelity Audio Tagging**: Automatically embeds Title, Artist, Album, Year, Lyrics, and high-resolution cover artwork using [Mutagen](https://mutagen.readthedocs.io/).
- **Zero-Credential Fallbacks**: Works out of the box with only your Telegram Bot Token! Uses dynamic client ID harvesting for SoundCloud and embed scraping for Spotify.
- **Real-Time Visual Progress**: Interactive ASCII progress bar updates download status without triggering Telegram's `429 Too Many Requests` rate limits.
- **Concurrency & Isolation**: Every download runs inside an isolated, self-cleaning temporary directory (`temporary_work_dir`), preventing race conditions and file collisions.
- **Telegram Upload Safeguard**: Respects the Telegram Bot API 50 MB upload limit. If a mix or podcast exceeds 50 MB, the bot cleanly notifies the user with direct download links.
- **Auto-Reconnecting Engine**: Resilient polling loop automatically recovers from network drops and transient Telegram API errors.

---

## 🎧 Supported Services & Link Formats

| Service | Supported Content | Example Link Formats |
| :--- | :--- | :--- |
| **Radio Javan** | Songs & Podcasts | `https://www.radiojavan.com/mp3s/mp3/...`<br>`https://www.radiojavan.com/podcasts/podcast/...`<br>`https://rj.app/m/...` |
| **SoundCloud** | Individual Tracks | `https://soundcloud.com/artist/track-name`<br>`https://m.soundcloud.com/artist/track-name`<br>`https://on.soundcloud.com/xyz123` |
| **Spotify** | Tracks | `https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT`<br>`https://open.spotify.com/intl-de/track/...`<br>`https://spotify.link/...`<br>`spotify:track:...` |

> [!NOTE]
> Spotify audio is protected by DRM encryption. Similar to [spotDL](https://github.com/spotDL/spotify-downloader), this bot extracts official Spotify metadata and artwork, then matches and extracts the audio stream from high-quality sources via `yt-dlp`.

---

## 📱 How to Use the Bot

Using the bot is intuitive and requires zero special commands:

1. **Start the Bot**: Open your bot in Telegram and click **Start** (or send `/start`).
2. **Send Any Link**: Simply paste a song, podcast, or track link into the chat.
3. **Watch the Download**: The bot analyzes the link, fetches the track metadata, and displays a live progress bar:
   ```text
   ⏳ Downloading...
   [████████░░] 80%
   ```
4. **Enjoy Your Music**: The bot sends you the MP3/M4A file with full tags, artwork, and an informative caption:
   ```text
   🎵 Blinding Lights
   👤 Artist: The Weeknd
   💿 Album: After Hours
   ⏱ Duration: 03:20
   📅 Year: 2020
   📡 Source: Spotify
   ```

---

## 📋 System Requirements

- **Python**: Version `3.9` or higher.
- **FFmpeg**: Required for audio transcoding and HLS stream assembly.

### Installing FFmpeg

- **Windows**:
  ```powershell
  winget install Gyan.FFmpeg
  # Or with Chocolatey:
  choco install ffmpeg
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```
- **macOS** (Homebrew):
  ```bash
  brew install ffmpeg
  ```
- **Arch Linux**:
  ```bash
  sudo pacman -S ffmpeg
  ```

---

## 🚀 Installation & Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/javad-hosseini/music-fetch-bot.git
cd music-fetch-bot
```

### 2. Create and Activate a Virtual Environment

- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Open `.env` in your editor and enter your Telegram Bot Token obtained from [@BotFather](https://t.me/BotFather):
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

---

## ⚙️ Configuration Reference (`.env`)

All settings can be customized in `.env`:

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `BOT_TOKEN` | **Yes** | — | Telegram Bot Token from [@BotFather](https://t.me/BotFather). |
| `DOWNLOAD_DIR` | No | `downloads` | Directory used for temporary download sandboxes. |
| `PROGRESS_UPDATE_INTERVAL`| No | `2.0` | Throttling interval (seconds) for editing progress messages. Prevents Telegram 429 rate limits. |
| `SPOTIPY_CLIENT_ID` | No | *(empty)* | Optional Spotify Developer Client ID. If omitted, web scraping is used. |
| `SPOTIPY_CLIENT_SECRET` | No | *(empty)* | Optional Spotify Developer Client Secret. |
| `SOUNDCLOUD_CLIENT_ID` | No | *(empty)* | Optional SoundCloud API client ID. If omitted, dynamic harvesting is used. |
| `FFMPEG_PATH` | No | *(auto)* | Custom path to `ffmpeg` executable. Defaults to system `PATH`. |

---

## ▶️ Running the Bot

### Option A: Via Python (All Platforms)

```bash
# Start bot in production mode:
python run.py

# Run pre-flight system diagnostics:
python run.py --check

# Run with verbose debug logging:
python run.py --verbose
```

### Option B: Windows Control Panel

Double-click [`bot_launcher.bat`](./bot_launcher.bat) to open the interactive control menu:
- `[1] Start Bot (Production)`
- `[2] Run System Diagnostics (--check)`
- `[3] Run Unit Tests (unittest)`
- `[4] Install / Update Dependencies (pip)`
- `[5] Exit`

---

## 🏗️ Architecture & Adding New Music Services

The codebase follows an extensible **Provider Pattern**. All music services implement the [`BaseMusicService`](./services/base.py) abstract base class:

```text
services/
├── base.py            # Abstract BaseMusicService & TrackInfo model
├── radiojavan.py      # RadioJavanService
├── soundcloud.py      # SoundCloudService
├── spotify.py         # SpotifyService
└── __init__.py        # Registry & find_service() factory
```

### How to Add a New Music Service in 3 Steps:

1. **Create your provider** in `services/your_service.py`:
   ```python
   from services.base import BaseMusicService, TrackInfo

   class MyMusicService(BaseMusicService):
       def can_handle(self, url: str) -> bool:
           return "myservice.com" in url

       def fetch_track(self, url: str) -> TrackInfo:
           # Extract metadata and download URL
           return TrackInfo(
               title="Song Title",
               artist="Artist Name",
               download_url="https://...",
               source="MyService",
           )
   ```

2. **Register the service** in `services/__init__.py`:
   ```python
   from services.your_service import MyMusicService

   SERVICES: List[BaseMusicService] = [
       RadioJavanService(),
       SoundCloudService(),
       SpotifyService(),
       MyMusicService(),  # <-- Added here
   ]
   ```

3. That's it! The bot will now automatically route matching links to your new service.

---

## 🧪 Testing

Run the automated test suite using Python's built-in `unittest`:

```bash
# Using virtual environment python:
python -m unittest discover -s tests
```

---

## 📁 Project Structure

```text
music-fetch-bot/
├── bot/
│   ├── __init__.py
│   ├── bot.py             # Bot initialization, command registration & polling loop
│   ├── formatters.py      # HTML escaping, duration formatting & captions
│   ├── handlers.py        # Message & callback query handlers
│   └── keyboards.py       # Inline keyboard builders (Main menu, platforms, actions)
├── services/
│   ├── __init__.py        # Active services registry & provider lookup
│   ├── base.py            # Abstract BaseMusicService & TrackInfo dataclass
│   ├── radiojavan.py      # Radio Javan songs & podcasts provider
│   ├── soundcloud.py      # SoundCloud progressive & HLS audio provider
│   └── spotify.py         # Spotify metadata & audio-matching provider
├── tests/
│   ├── test_services.py   # Unit tests for URL matching & service routing
│   └── test_ui_and_mp3.py # Unit tests for UI, keyboards & MP3 format enforcement
├── utils/
│   ├── __init__.py
│   ├── audio.py           # Mutagen ID3v2 tagger with artwork embedding & MP3 conversion
│   ├── downloader.py      # Streaming chunk downloader with progress updates
│   └── filesystem.py      # Filename sanitization & temporary workspaces
├── docs/
│   ├── platform_expansion_spotify_soundcloud.md  # Architectural research
│   └── ui_ux_enhancements_guide.md               # UI/UX & CLI blueprint
├── config.py              # Centralized environment configuration
├── run.py                 # Main entry point with CLI diagnostics & banner
├── bot_launcher.bat       # Windows interactive control panel
├── .env.example           # Environment template
├── requirements.txt       # Python package dependencies
├── .gitignore             # Git exclusions
└── README.md              # Project documentation
```

---

## ❓ Troubleshooting & FAQ

<details>
<summary><b>Q: Getting "FFmpeg not found" error during Spotify or SoundCloud downloads?</b></summary>
Make sure FFmpeg is installed and added to your system's PATH. You can verify by opening a terminal and running <code>ffmpeg -version</code>. Alternatively, define <code>FFMPEG_PATH=/path/to/ffmpeg</code> directly in your <code>.env</code> file.
</details>

<details>
<summary><b>Q: What happens if a podcast or track is larger than 50 MB?</b></summary>
Telegram Bot API enforces a hard 50 MB file upload limit for standard bots. If a downloaded audio file exceeds 49.5 MB, the bot cleanly cancels the upload and sends a direct download link with a clear message explaining the file size limit.
</details>

<details>
<summary><b>Q: Do I need Spotify API credentials?</b></summary>
No! By default, the bot uses a zero-credential web embed extraction technique to obtain Spotify track metadata. Supplying <code>SPOTIPY_CLIENT_ID</code> and <code>SPOTIPY_CLIENT_SECRET</code> is completely optional and only needed if you prefer using the official Spotify Web API.
</details>

<details>
<summary><b>Q: Bot stops responding or crashes on disconnect?</b></summary>
The bot features an auto-reconnecting loop in <code>bot/bot.py</code> that catches network dropouts and automatically attempts reconnection every 5 seconds.
</details>

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](./LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is created for personal, educational, and backup purposes only. Please respect the intellectual property rights of artists and platforms. Users are responsible for ensuring they have the right to download and use any media obtained through this bot.
