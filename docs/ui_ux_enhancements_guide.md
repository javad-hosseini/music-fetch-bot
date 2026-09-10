# 🎨 UI/UX & CLI Enhancement Specification: Telegram Music Downloader Bot

This blueprint outlines the complete UI/UX and CLI improvements designed by **Hana** for **Parsa** (`parsa-mtvwquqx`) to implement in the codebase.

---

## 1. Overview of Improvements

| Component | Current State | Proposed Enhancement |
| :--- | :--- | :--- |
| **Command Palette** | None registered with BotFather / Bot API | Dynamic registration of native `/start`, `/help`, `/commands`, `/platforms`, `/ping`, `/about` via `bot.set_my_commands()`. |
| **Navigation & Buttons** | Plain text only; no inline buttons | Interactive `InlineKeyboardMarkup` menus: Main Menu, Help Guide, Platform Breakdown, Ping/Health, and Audio Action buttons. |
| **Audio Post Delivery** | Plain audio message with text caption | Interactive inline buttons below the audio: `[🔗 Listen on Source]` and `[ℹ️ Track Details]`. |
| **Error Handling UX** | Text error message | Actionable buttons: `[🔄 Try Again]`, `[📖 Supported Platforms]`, and direct link buttons for files > 50 MB. |
| **CLI & Terminal** | Basic text logs | Modern ANSI terminal header banner, CLI arguments (`--check`, `--verbose`), and graceful `Ctrl+C` shutdown. |
| **Windows Control Panel** | Fixed 4-second boot animation, single run option | Instant-launch interactive menu with Bot Run, Diagnostics (`--check`), Unit Tests, and Pip Dependency Updater. |

---

## 2. Component Design & Code Structure

### 2.1 New Keyboards Module: `bot/keyboards.py`

Create a clean module dedicated to constructing inline keyboards:

```python
"""
bot/keyboards.py - Inline keyboard builders for rich Telegram UI.
"""
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.base import TrackInfo


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Primary navigation keyboard shown on /start and main menu."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 Guide & Help", callback_data="ui_help"),
        InlineKeyboardButton("🎵 Supported Platforms", callback_data="ui_platforms"),
    )
    markup.add(
        InlineKeyboardButton("⚡ Bot Status", callback_data="ui_ping"),
        InlineKeyboardButton("ℹ️ About Bot", callback_data="ui_about"),
    )
    return markup


def platforms_menu_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for exploring supported platforms."""
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("📻 Radio Javan", callback_data="ui_plat_rj"),
        InlineKeyboardButton("☁️ SoundCloud", callback_data="ui_plat_sc"),
        InlineKeyboardButton("🟢 Spotify", callback_data="ui_plat_sp"),
    )
    markup.add(
        InlineKeyboardButton("🔙 Back to Main Menu", callback_data="ui_main"),
    )
    return markup


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Single back button to return to the main menu."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="ui_main"))
    return markup


def audio_action_keyboard(track: TrackInfo) -> InlineKeyboardMarkup:
    """Action buttons attached directly below delivered audio messages."""
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []

    # Direct source link
    if track.share_url:
        buttons.append(InlineKeyboardButton("🔗 Listen on Source", url=track.share_url))
    elif track.download_url and track.download_url.startswith("http"):
        buttons.append(InlineKeyboardButton("🔗 Direct Link", url=track.download_url))

    if buttons:
        markup.add(*buttons)

    return markup


def error_keyboard(retry_url: str = None) -> InlineKeyboardMarkup:
    """Actionable buttons when an error or unrecognized link is received."""
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🎵 Supported Links", callback_data="ui_platforms"),
        InlineKeyboardButton("📖 Help Guide", callback_data="ui_help"),
    ]
    markup.add(*buttons)
    return markup


def oversized_file_keyboard(direct_url: str) -> InlineKeyboardMarkup:
    """Buttons when audio exceeds Telegram's 50MB limit."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🌐 Download Directly (Browser)", url=direct_url))
    return markup
```

---

### 2.2 Updating Handlers: `bot/handlers.py`

#### Commands to add:
1. **`/start`**:
   - Sends the welcome greeting with `main_menu_keyboard()`.
2. **`/help`** or **`/commands`**:
   - Comprehensive command list and link submission instructions with back/topic buttons.
3. **`/platforms`**:
   - Detailed format reference with tap-to-copy code blocks for Radio Javan, SoundCloud, and Spotify.
4. **`/ping`**:
   - Measures API latency:
     ```python
     start_time = time.time()
     # calculate delta after message dispatch
     latency_ms = int((time.time() - start_time) * 1000)
     ```
   - Displays active providers count and bot status.
5. **`/about`**:
   - Displays version, open-source license, and GitHub repository link.

#### Callback Query Handler:
Register `@bot.callback_query_handler(func=lambda call: call.data.startswith("ui_"))` to handle:
- `"ui_main"` $\rightarrow$ edit message text to the Main Menu.
- `"ui_help"` $\rightarrow$ edit message text to Help & Guide.
- `"ui_platforms"` $\rightarrow$ edit message text to Platforms overview.
- `"ui_plat_rj"` $\rightarrow$ Radio Javan link examples (`radiojavan.com/mp3s/mp3/...`, `rj.app/...`).
- `"ui_plat_sc"` $\rightarrow$ SoundCloud link examples (`soundcloud.com/...`, `on.soundcloud.com/...`).
- `"ui_plat_sp"` $\rightarrow$ Spotify link examples (`open.spotify.com/track/...`, `spotify.link/...`).
- `"ui_ping"` $\rightarrow$ refresh ping and latency.
- `"ui_about"` $\rightarrow$ display project info and credits.

Always call `bot.answer_callback_query(call.id)` at the start of callback handlers to dismiss the loading animation on the Telegram client.

#### Attaching Buttons to Downloads:
When `bot.send_audio()` executes, pass:
```python
reply_markup = audio_action_keyboard(track)
```
When a file exceeds 50MB:
```python
reply_markup = oversized_file_keyboard(fallback_link)
```

---

### 2.3 Command Palette Setup: `bot/bot.py`

Add a helper function in `bot/bot.py` to register native Telegram Bot commands with the API:

```python
from telebot.types import BotCommand

def setup_bot_commands(bot: TeleBot) -> None:
    """Register native Telegram command menu."""
    commands = [
        BotCommand("start", "🚀 Start bot & main menu"),
        BotCommand("help", "📖 User guide & commands"),
        BotCommand("platforms", "🎵 Supported music links"),
        BotCommand("ping", "⚡ Check latency & health"),
        BotCommand("about", "ℹ️ About this bot"),
    ]
    try:
        bot.set_my_commands(commands)
        logger.info("Registered Telegram native bot commands.")
    except Exception as e:
        logger.warning(f"Could not register Telegram commands: {e}")
```

Call `setup_bot_commands(bot)` right inside `create_bot()`.

---

### 2.4 CLI Enhancements: `run.py`

Update `run.py` with argument parsing and a stylish terminal banner:

```python
"""
run.py - Main entry point with CLI diagnostics and colored startup banner.
"""
import sys
import time
import argparse
import logging
from bot import run_bot, create_bot
import config
from services import SERVICES


BANNER = r"""
╭─────────────────────────────────────────────────────────────╮
│  🎵  Telegram Music Downloader Bot                          │
│  📡  Radio Javan • SoundCloud • Spotify                     │
╰─────────────────────────────────────────────────────────────╯
"""

def run_diagnostics() -> int:
    """CLI Health check: tests environment, tokens, providers, and FFmpeg."""
    print("\n🔍 Running System & Service Diagnostics...\n")
    all_ok = True

    # 1. Bot Token
    if config.BOT_TOKEN:
        print("  ✅ BOT_TOKEN: Configured")
        try:
            bot = create_bot()
            me = bot.get_me()
            print(f"  ✅ Telegram API: Connected as @{me.username} (ID: {me.id})")
        except Exception as e:
            print(f"  ❌ Telegram API connection failed: {e}")
            all_ok = False
    else:
        print("  ❌ BOT_TOKEN: Missing in environment/.env!")
        all_ok = False

    # 2. FFmpeg
    if config.FFMPEG_PATH:
        print(f"  ✅ FFmpeg: Found at {config.FFMPEG_PATH}")
    else:
        print("  ⚠️  FFmpeg: Not detected (HLS/Spotify conversions will fail without it)")
        all_ok = False

    # 3. Active Services
    print(f"  ✅ Active Providers ({len(SERVICES)}):")
    for s in SERVICES:
        print(f"     • {s.__class__.__name__}")

    # 4. Downloads directory
    if config.DOWNLOAD_DIR.exists():
        print(f"  ✅ Download directory: {config.DOWNLOAD_DIR} (Writable)")
    else:
        print(f"  ❌ Download directory does not exist: {config.DOWNLOAD_DIR}")
        all_ok = False

    print("\n" + ("=" * 50))
    if all_ok:
        print("🎉 All diagnostics passed! System is ready to run.\n")
        return 0
    else:
        print("⚠️  Some diagnostics reported warnings or errors.\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Telegram Music Downloader Bot")
    parser.add_argument("-c", "--check", action="store_true", help="Run system diagnostics and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose DEBUG logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.check:
        sys.exit(run_diagnostics())

    print(BANNER)
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped gracefully by user (Ctrl+C). Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

---

### 2.5 Windows Launcher: `bot_launcher.bat`

Update `bot_launcher.bat` to eliminate the slow artificial boot delays and provide a clean control menu:
- `[1] Start Bot (Production)`
- `[2] Run Diagnostics (--check)`
- `[3] Run Unit Tests (test_services.py)`
- `[4] Install / Update Dependencies (pip)`
- `[5] Exit`

---

## 3. Step-by-Step Implementation Roadmap for Parsa

1. **Create `bot/keyboards.py`**:
   - Implement `main_menu_keyboard()`, `platforms_menu_keyboard()`, `back_to_main_keyboard()`, `audio_action_keyboard()`, and `oversized_file_keyboard()`.
2. **Update `bot/handlers.py`**:
   - Add command handlers for `/commands`, `/platforms`, `/ping`, and `/about`.
   - Update `/start` and `/help` to use inline buttons.
   - Implement callback query dispatcher for `ui_*` actions.
   - Attach `audio_action_keyboard(track)` to `bot.send_audio()`.
3. **Update `bot/bot.py`**:
   - Add `setup_bot_commands(bot)` to set native menu commands.
4. **Update `run.py`**:
   - Add CLI arguments (`--check`, `--verbose`), terminal banner, and graceful Ctrl+C handler.
5. **Update `bot_launcher.bat`**:
   - Modernize the control panel with diagnostics and test suite options.
6. **Verify with test suite**:
   - Run `python -m unittest discover tests`.
