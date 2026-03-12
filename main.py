import os, logging, threading, time, asyncio
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot():
    time.sleep(2)
    try:
        # Create a NEW event loop for this thread — fixes "no current event loop" error
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from bot import main
        logger.info("Starting Telegram bot...")
        main()
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)

threading.Thread(target=run_bot, daemon=True).start()

from server import app
port = int(os.environ.get("PORT", 8080))
logger.info(f"Starting Flask on port {port}")
app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
