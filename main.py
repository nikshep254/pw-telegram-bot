"""
Entrypoint for Railway.
Flask (web server) runs in the FOREGROUND so Railway's healthcheck on /health passes.
Telegram bot runs in a background thread.
"""

import os
import logging
import threading

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

# BASE_URL can be empty on first deploy — bot still works, stream links won't
if not BASE_URL:
    logger.warning("BASE_URL not set — video stream links won't work until you set it!")

# ── Start Telegram bot in background thread ───────────────────────────────────
def run_bot():
    try:
        from bot import main
        logger.info("Starting Telegram bot...")
        main()
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# ── Start Flask in FOREGROUND (Railway healthcheck needs this) ────────────────
from server import app

port = int(os.environ.get("PORT", 8080))
logger.info(f"Starting Flask on port {port}")
app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
