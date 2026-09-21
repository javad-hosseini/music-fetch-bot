import time
import logging
from telebot import TeleBot, apihelper
import config
from bot.handlers import register_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MusicBot")


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


def create_bot() -> TeleBot:
    """Initialize and configure the TeleBot instance."""
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing! Please configure .env file.")

    apihelper.READ_TIMEOUT = 300
    apihelper.CONNECT_TIMEOUT = 300

    if config.PROXY_URL:
        apihelper.proxy = {'http': config.PROXY_URL, 'https': config.PROXY_URL}
        logger.info(f"Configured Telegram proxy: {config.PROXY_URL}")

    bot = TeleBot(config.BOT_TOKEN, parse_mode=None)
    register_handlers(bot)
    setup_bot_commands(bot)
    return bot


def run_bot() -> None:
    """Start the Telegram bot with auto-reconnect polling."""
    bot = create_bot()
    bot_info = bot.get_me()
    logger.info(f"🤖 Bot @{bot_info.username} (ID: {bot_info.id}) started successfully!")

    while True:
        try:
            bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"⚠️ Polling encountered an error: {e}")
            logger.info("Reconnecting in 5 seconds...")
            time.sleep(5)
