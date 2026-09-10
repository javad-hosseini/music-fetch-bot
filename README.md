# Telegram Music Downloader Bot 🎵

A modular, extensible Telegram bot for downloading music and podcasts with complete metadata (ID3v2 tags, high-resolution cover artwork, lyrics, and track information).

Currently supports **Radio Javan** (Songs and Podcasts), **SoundCloud** (Tracks), and **Spotify** (Tracks), designed with a pluggable architecture to easily add more services.

---

## 🚀 Features

- **Multi-Platform Music Provider Architecture**: Modular providers for Radio Javan, SoundCloud, and Spotify extending `BaseMusicService`.
- **High-Fidelity Audio Metadata & Artwork**: Embeds Title, Artist, Album, Year, Lyrics, and high-resolution Cover Art (supports MP3 and M4A).
- **Zero-Credential Fallbacks**: Works out of the box with dynamic client ID harvesting (SoundCloud) and web embed extraction (Spotify) without mandatory API keys.
- **Concurrency-Safe**: Each download executes in an isolated temporary workspace to prevent file collisions.
- **Throttled Telegram Progress**: Prevents Telegram API 429 rate-limit errors by throttling status message edits.
- **Telegram Size Safeguards**: Automatically validates the 50 MB bot API upload limit and provides direct streaming links when files exceed the limit.
- **Resilient Polling**: Auto-reconnects on network drops.

---

## 📁 Project Structure

```text
Radiojavan-dl/
├── bot/
│   ├── __init__.py
│   ├── bot.py             # Bot initialization, configuration & resilient runner
│   ├── handlers.py        # Telegram command & message handlers
│   └── formatters.py      # HTML entity escaping & caption/progress formatting
├── services/
│   ├── __init__.py        # Provider registry & lookup
│   ├── base.py            # Abstract BaseMusicService & TrackInfo model
│   ├── radiojavan.py      # Radio Javan provider (Songs & Podcasts)
│   ├── soundcloud.py      # SoundCloud provider (Progressive & HLS)
│   └── spotify.py         # Spotify provider (Metadata + yt-dlp audio matching)
├── tests/
│   └── test_services.py   # Comprehensive service test suite
├── utils/
│   ├── __init__.py
│   ├── audio.py           # Mutagen ID3/M4A metadata tagger
│   ├── downloader.py      # Streamed HTTP downloader with throttled callbacks
│   └── filesystem.py      # Filename sanitization & isolated temporary directories
├── config.py              # Centralized environment settings
├── run.py                 # Main bot entry point
├── bot_launcher.bat       # Windows launcher
├── .env.example           # Configuration template
├── requirements.txt       # Project dependencies
└── README.md
```


---

## 🛠 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MhdiTaheri/Radiojavan-dl.git
   cd Radiojavan-dl
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your bot token:**
   Copy `.env.example` to `.env` and fill in your Telegram Bot Token:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   BOT_TOKEN=your_bot_token_here
   ```

---

## ▶️ Running the Bot

- **Via Python:**
  ```bash
  python run.py
  ```

- **On Windows (GUI Launcher):**
  Double click `bot_launcher.bat`.

- **Background execution on Linux:**
  ```bash
  nohup python run.py > bot.log 2>&1 &
  ```

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
