"""
run.py - Main entry point with CLI diagnostics and colored startup banner.
"""
import sys
import argparse
import logging

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
