"""
Entrypoint for Railway.
Flask (web server) runs in the FOREGROUND so Railway's healthcheck on /health passes.
Telegram bot runs in a background thread with its own asyncio loop.
"""

import os
import logging
import threading
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Env var validation ────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BASE_URL  = os.environ.get("BASE_URL", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

if not BASE_URL:
    logger.warning("BASE_URL not set — video stream links won't work until you set it!")

# ── Start Telegram bot in background thread ───────────────────────────────────
def run_bot():
    """
    Sets up a new event loop for the background thread and starts the bot.
    """
    try:
        from bot import main
        
        # Create a new event loop for this specific thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Starting Telegram bot...")
        
        # If your bot's main() is an 'async def' function:
        # loop.run_until_complete(main())
        
        # If your bot's main() is a regular 'def' function that calls run_polling():
        main()
        
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)

# Use a daemon thread so it closes when the Flask server stops
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# ── Start Flask in FOREGROUND (Railway healthcheck needs this) ────────────────
from server import app

# Railway provides the PORT env var automatically
port = int(os.environ.get("PORT", 8080))
logger.info(f"Starting Flask on port {port}")

# Important: use_reloader=False is required when running threads
app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
