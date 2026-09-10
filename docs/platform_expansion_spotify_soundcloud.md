# Technical Review & Architecture Plan: Spotify & SoundCloud Integration

## 1. Executive Summary

This document reviews two reference repositories for expanding the **Music Downloader Bot** to support **Spotify** and **SoundCloud**:
1. [spotDL/spotify-downloader](https://github.com/spotDL/spotify-downloader) — Command-line and library solution for matching Spotify track metadata with YouTube/YouTube Music audio streams and downloading via `yt-dlp`.
2. [purr/soundcloud-aiogram](https://github.com/purr/soundcloud-aiogram) — An `aiogram`-based Telegram bot providing SoundCloud search, direct links, dynamic client ID harvesting, and HLS/progressive audio downloading.

### Current Bot Baseline (`Radiojavan-dl`)
- **Telegram Framework**: `pyTelegramBotAPI` (`telebot` v4.20.0), multi-threaded synchronous polling.
- **Provider Architecture**: Abstract base class [`BaseMusicService`](file:///D:/projects/Telegram%20Bot/RJ%20downloader/Radiojavan-dl/services/base.py) producing standardized [`TrackInfo`](file:///D:/projects/Telegram%20Bot/RJ%20downloader/Radiojavan-dl/services/base.py) objects with stream URLs.
- **Downloader Pipeline**: Stream-based chunk downloader ([`download_stream`](file:///D:/projects/Telegram%20Bot/RJ%20downloader/Radiojavan-dl/utils/downloader.py)) with throttled Telegram message edits, Mutagen ID3/MP4 metadata and artwork tagging ([`utils/audio.py`](file:///D:/projects/Telegram%20Bot/RJ%20downloader/Radiojavan-dl/utils/audio.py)), and isolated temporary job folders ([`temporary_work_dir`](file:///D:/projects/Telegram%20Bot/RJ%20downloader/Radiojavan-dl/utils/filesystem.py)).

---

## 2. Comparative Analysis of the Reference Repositories

| Dimension | `spotdl/spotify-downloader` | `purr/soundcloud-aiogram` | Current Codebase (`Radiojavan-dl`) |
| :--- | :--- | :--- | :--- |
| **Primary Platforms** | Spotify (Tracks, Albums, Playlists) | SoundCloud (Tracks, Playlists), pseudo-Spotify (redirects to SC) | Radio Javan (Songs, Podcasts) |
| **Telegram Framework** | None (CLI tool) | `aiogram` v3 (Modern async, inline queries) | `pyTelegramBotAPI` (`telebot`, sync threaded) |
| **Audio Extraction** | Metadata from Spotify API/Scrape $\rightarrow$ matches audio on YouTube Music/YouTube $\rightarrow$ downloads via `yt-dlp` | Direct SoundCloud v2 REST API $\rightarrow$ Progressive MP3 direct or HLS (`m3u8`) via FFmpeg | Direct HTTP stream from Radio Javan API/CDN via `requests` |
| **Authentication** | Spotify Client Credentials (free developer app or scraped anonymous token) | Scraped dynamic `client_id` with 12h TTL + hardcoded fallbacks | None required (RJ public API) |
| **External Binaries** | `ffmpeg`, `yt-dlp` | `ffmpeg` (for HLS transcoding) | None (pure Python: `mutagen`, `requests`) |
| **Tagging & Artwork** | Embedded ID3v2.3/v2.4 tags via `mutagen`, synced/plain lyrics, 640x640 cover art | ID3 tags via `mutagen`, 500x500 artwork, `pydub` silence removal | ID3v2.3 and MP4Cover via `mutagen`, lyrics, cover art |
| **Caching** | Local track cache / metadata cache | Telegram `file_id` caching in memory/JSON, downloaded file cache | None (stateless temporary dirs) |

---

## 3. Deep-Dive Review: `spotdl/spotify-downloader`

### 3.1 Architecture & Mechanism
- **The DRM Reality**: Spotify uses Widevine and FairPlay DRM to encrypt audio. Direct ripping of raw Spotify audio streams without breaking encryption or violating Terms of Service is impossible. `spotdl` does **not** download from Spotify directly; it uses Spotify exclusively for **metadata extraction** and **track identification**.
- **Audio Matching Pipeline**:
  1. Parse Spotify URL (track, album, playlist, artist).
  2. Fetch canonical metadata from Spotify Web API or Spotipy (Title, Artist, Album, ISRC, Duration, Year, Cover URL).
  3. Query audio providers (primarily **YouTube Music**, fallback to standard YouTube or SoundCloud) using search algorithms that compare track title, artist name, and duration tolerance ($\pm 5-10$ seconds).
  4. Download the matched video's best audio stream (Opus 160kbps or AAC 128-256kbps) using `yt-dlp`.
  5. Convert audio to target format (MP3 320k or original m4a) via `ffmpeg`.
  6. Embed Spotify metadata and high-res cover art using `mutagen`.

### 3.2 Strengths
- **Metadata Fidelity**: Retrieves official Spotify metadata including album name, release date, artist credits, and high-resolution album art (`i.scdn.co`).
- **Comprehensive Music Library**: Covers virtually any track on Spotify because YouTube Music hosts almost all commercial releases.
- **Playlist & Album Parsing**: Native support for batch parsing Spotify playlists and albums.

### 3.3 Pitfalls & Considerations for Our Bot
- **No Stable Python API**: `spotdl` is maintained primarily as a CLI application. Internal classes (`spotdl.download.downloader.DownloadManager`) change between versions and are not designed for direct async/thread-safe in-process Python imports.
- **YouTube Rate Limiting & Bot Detection**: YouTube frequently serves HTTP 429 ("Too Many Requests") or HTTP 403 ("Sign in to confirm you’re not a bot") to datacenter and VPS IP addresses. This requires `yt-dlp` to use cookies or PO tokens.
- **Processing Latency**: Because downloading a Spotify track requires metadata retrieval + YouTube search + `yt-dlp` audio download + FFmpeg transcoding, latency is typically **6–15 seconds per track**, compared to 1–2 seconds for direct CDN links.
- **Recommended Integration Pattern**: Rather than adding `spotdl` as a monolithic dependency, the bot should implement a streamlined **`SpotifyService`** that uses `spotipy` (or anonymous Spotify web token API) for metadata, then uses `yt-dlp`'s Python API (`yt_dlp.YoutubeDL`) to extract the matching audio directly.

---

## 4. Deep-Dive Review: `purr/soundcloud-aiogram`

### 4.1 Architecture & Mechanism
- **Direct SoundCloud v2 REST API**: Avoids heavy scrapers by directly calling SoundCloud's internal API (`https://api-v2.soundcloud.com/`).
- **Dynamic Client ID Scraping (`utils/client_id.py`)**:
  - SoundCloud requires a `client_id` query parameter on API requests.
  - The repo scrapes `https://soundcloud.com/`, finds JavaScript bundle tags matching `https://a-v2.sndcdn.com/assets/*.js`, regex-extracts the client ID, and caches it for 12 hours.
  - Maintains a hardcoded fallback list of known client IDs if dynamic harvesting fails.
- **URL Resolution (`/resolve`)**:
  - Handles canonical URLs (`soundcloud.com/artist/track`), mobile links (`m.soundcloud.com`), and short URLs (`on.soundcloud.com`).
  - Calls `https://api-v2.soundcloud.com/resolve?url=<url>&client_id=<id>` which returns the full track or playlist JSON.
- **Stream Extraction**:
  - SoundCloud provides multiple transcoding streams in the track JSON under `media.transcodings`.
  - **Progressive Stream (`protocol: "progressive"`)**: Returns a direct HTTP link to an MP3 file (128 kbps). This stream can be downloaded directly using standard HTTP chunk streaming with progress bars.
  - **HLS Stream (`protocol: "hls"`)**: Returns an `.m3u8` playlist of audio chunks. Requires FFmpeg or `yt-dlp` to concatenate and export as MP3.
- **Audio Processing**:
  - `pydub` silence detection and trimming at the start and end of tracks.
  - Mutagen for ID3 tag injection and high-quality artwork (`t500x500.jpg` replaces the default `large.jpg` 100x100 thumbnail).

### 4.2 Strengths
- **Native & Lightweight**: Progressive streams download fast and do not require external heavy engines.
- **No API Credentials Needed**: Dynamic client ID harvesting means zero user configuration in `.env`.
- **Supports Shortlinks & Playlists**: Resolves `on.soundcloud.com` redirects cleanly.

### 4.3 Pitfalls & Considerations for Our Bot
- **HLS vs Progressive Streams**: Many modern SoundCloud tracks only offer HLS streams (Opus/AAC chunks), meaning `download_stream()` in `utils/downloader.py` cannot download them as raw HTTP streams without an HLS parser or FFmpeg/yt-dlp.
- **Code Organization**: `purr/soundcloud-aiogram` has a monolithic 100KB `helpers/soundcloud.py` with tight coupling between business logic and UI. We should extract only the pure service logic into clean, modular files.
- **Spotify Pseudo-Support**: Note that `purr/soundcloud-aiogram`'s "Spotify" support is merely a title regex scrape from Spotify HTML that executes a SoundCloud search. This fails if the track is not on SoundCloud. Our bot needs a genuine Spotify downloader.

---

## 5. Architectural Decision: `pyTelegramBotAPI` vs `aiogram`

### Current State
`Radiojavan-dl` is built on `pyTelegramBotAPI` (`telebot`):
- Simple synchronous message handler pipeline.
- Thread-pool worker dispatch.
- Downloader runs in a thread, editing messages synchronously every 2 seconds.

### Should we migrate to `aiogram` v3?
- **Benefits of `aiogram` v3**:
  - Fully asynchronous event loop (`asyncio`), native support for concurrent downloads without Python OS thread overhead.
  - Robust inline query handling (for searching SoundCloud/Spotify directly in any chat).
  - Clean middleware support (for rate limiting, error logging, authentication).
  - Modern keyboard builders and state machine (FSM).
- **Drawbacks / Migration Cost**:
  - Requires rewriting `bot/bot.py`, `bot/handlers.py`, and converting all service and downloader calls to `async/await` (`httpx` or `aiohttp`).
  - Potential regressions in existing Radio Javan functionality during refactoring.

### Recommendation for Parsa
1. **Phase 1 (Immediate - Service Integration)**:
   - Retain the current `pyTelegramBotAPI` architecture.
   - Implement `SoundCloudService` and `SpotifyService` conforming to the existing [`BaseMusicService`](file:///D:/projects/Telegram%20Bot/RJ%20downloader/Radiojavan-dl/services/base.py) interface.
   - This delivers multi-platform support immediately without disrupting the bot's stable polling loop.
2. **Phase 2 (Optional Future Optimization)**:
   - If inline search or advanced interactive keyboards (e.g. browsing playlists interactively) are prioritized, migrate the bot layer to `aiogram` v3 in a dedicated branch.

---

## 6. Recommended System Architecture

```
                    ┌─────────────────────────┐
                    │      Telegram User      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  bot/handlers.py (Bot)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   services/find_service  │
                    └────────────┬────────────┘
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ RadioJavanService│   │SoundCloudService │   │  SpotifyService  │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         │ Direct CDN           │ Progressive / HLS    │ Metadata (Spotify)
         │                      │ (Client ID harvest)  │ + Audio (yt-dlp)
         ▼                      ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│                   Standardized TrackInfo Object                │
│ (title, artist, album, duration, year, cover_url, download_url)│
└───────────────────────────────┬────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                      Download & Tagging Pipeline                │
│  - utils/downloader.py (HTTP stream or yt-dlp/ffmpeg local dl) │
│  - utils/audio.py (Mutagen ID3 tagging & high-res artwork)     │
│  - Telegram 50MB check & bot.send_audio()                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. Step-by-Step Implementation Roadmap for Parsa

### Phase 1: Dependency & Configuration Updates
1. Add new dependencies to `requirements.txt`:
   ```text
   yt-dlp>=2024.08.06
   spotipy>=2.24.0
   ```
2. Update `config.py`:
   - Add optional `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` (fallback to public client scraping if empty).
   - Add `SOUNDCLOUD_CLIENT_ID` fallback configuration.

### Phase 2: Refactor `BaseMusicService` & Download Workflow
Currently, `TrackInfo` assumes `download_url` is always an HTTP URL streamable via `requests.get()`. For HLS SoundCloud streams and YouTube/Spotify matches, `yt-dlp` handles the download and muxing directly into a file.
- Update `BaseMusicService` in `services/base.py` to support an optional `download_track(self, track: TrackInfo, target_path: Path, on_progress=None) -> Path` method. If not overridden, it falls back to `utils.downloader.download_stream`.

### Phase 3: Implement `SoundCloudService` (`services/soundcloud.py`)
1. Implement URL matching for `soundcloud.com` and `on.soundcloud.com`.
2. Implement client ID resolver with in-memory caching (12h expiry) using the asset scraping pattern from `purr/soundcloud-aiogram/utils/client_id.py`.
3. Implement `resolve_url()` via `https://api-v2.soundcloud.com/resolve`.
4. Handle audio transcodings:
   - If `progressive` stream available, get direct MP3 stream URL.
   - If only `hls` stream available, route download through `yt-dlp` with the HLS manifest URL or page URL.
5. Extract high-resolution artwork (`replace('-large.', '-t500x500.')`).

### Phase 4: Implement `SpotifyService` (`services/spotify.py`)
1. Implement URL matching for `open.spotify.com/track/`, `spotify.link/`, and URI `spotify:track:`.
2. Extract track ID from URL.
3. Fetch metadata:
   - Query Spotify Web API (or scrape the Spotify embed/OpenGraph page for zero-credential mode) to obtain track name, artists, album name, release year, duration, and cover art image URL.
4. Audio extraction:
   - Use `yt_dlp.YoutubeDL` configured for audio-only extraction (`bestaudio/best`).
   - Search query: `ytsearch1:{artist} - {title} audio` (or YouTube Music provider).
   - Verify duration to avoid matching 1-hour loops or extended mixes.
   - Save output as MP3 into the job directory.

### Phase 5: Register Services & Enhance UI
1. Register both services in `services/__init__.py`:
   ```python
   SERVICES = [
       RadioJavanService(),
       SoundCloudService(),
       SpotifyService(),
   ]
   ```
2. Update `/start` and `/help` text in `bot/handlers.py` to highlight the newly supported platforms:
   - Radio Javan
   - SoundCloud
   - Spotify
3. Update error reporting:
   - If a track exceeds 50MB, provide clear direct download instructions.
   - If audio matching fails on Spotify, advise the user to provide a direct SoundCloud or Radio Javan link.
