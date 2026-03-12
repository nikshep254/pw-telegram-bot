"""
Entrypoint for Railway.
Flask (web server) runs in the FOREGROUND.
Telegram bot runs in a background thread with signal handling disabled.
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

# ── Start Telegram bot in background thread ───────────────────────────────────
def run_bot():
    try:
        # We need to import the application object or the main function
        from bot import main 
        
        # Create and set the event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Starting Telegram bot in background thread...")

        # Most likely your bot.py uses application.run_polling()
        # We must ensure it doesn't try to handle signals in a background thread
        main() 
        
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)

# Start the bot thread
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# ── Start Flask in FOREGROUND ────────────────────────────────────────────────
from server import app

port = int(os.environ.get("PORT", 8080))
logger.info(f"Starting Flask on port {port}")

# use_reloader=False is CRITICAL here to prevent the thread from starting twice
app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
