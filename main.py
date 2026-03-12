import os, logging, threading
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask runs in background thread (just for healthcheck + streaming)
def run_flask():
    from server import app
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

# Bot runs in MAIN thread (required by asyncio signal handlers)
if not os.environ.get("BOT_TOKEN"):
    logger.error("BOT_TOKEN not set!")
else:
    from bot import main
    logger.info("Starting bot in main thread...")
    main()
