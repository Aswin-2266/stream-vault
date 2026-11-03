import asyncio
import logging
from bot.utils.crypto_patch import apply_crypto_patch

# Apply cryptg acceleration before importing Hydrogram components
apply_crypto_patch()

from hydrogram import Client, idle
import config
from bot.utils.database import db
from bot.utils.streamer import set_bot_instance, start_web_server
from bot.utils.tunnel import start_tunnel, stop_tunnel
from bot.utils.vm_leech import vm_leech_manager
from bot.utils.cleaner import start_storage_cleaner

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("StreamVault")

async def main():
    logger.info("Initializing StreamVault...")

    # Step 1: Connect to MongoDB Atlas
    db.connect()
    await db.init_indexes()

    # Step 1b: Initialize Non-blocking MongoDB Logging Pipeline
    from bot.utils.mongo_logger import setup_mongo_logging
    setup_mongo_logging()

    # Step 2: Initialize Telegram Bot Client
    bot = Client(
        name="stream_vault_bot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
        plugins=dict(root="bot.handlers")
    )

    # Step 3: Register bot with the streaming web server
    set_bot_instance(bot)

    # Step 4: Start web server (Port 7860 on Hugging Face Spaces)
    web_runner = await start_web_server()

    # Step 4b: Start Cloudflare Tunnel if STREAM_URL is local
    if "localhost" in config.STREAM_URL or "127.0.0.1" in config.STREAM_URL:
        public_url = start_tunnel(config.PORT)
        if public_url:
            config.STREAM_URL = public_url
            logger.info(f"StreamVault Public Streaming Gateway: {config.STREAM_URL}")

    # Step 5: Start Telegram Bot
    await bot.start()
    bot_info = await bot.get_me()
    logger.info(f"Telegram Bot Online: @{bot_info.username} (ID: {bot_info.id})")

    # Step 5b: Start Oracle VM Leech Worker & Rolling Storage Cleaner
    asyncio.create_task(vm_leech_manager.start_worker())
    start_storage_cleaner()
    logger.info("Oracle VM Native Leech Worker & Storage Cleaner online!")

    # Step 6: Initial channel auto-indexer (if configured in .env)
    if config.CHANNELS_TO_INDEX:
        logger.info(f"Auto-indexing {len(config.CHANNELS_TO_INDEX)} channels configured on startup...")
        for channel in config.CHANNELS_TO_INDEX:
            try:
                logger.info(f"Connecting to initial channel: {channel}")
            except Exception as e:
                logger.warning(f"Could not index channel {channel}: {e}")

    logger.info("StreamVault Engine is fully operational! Listening for requests...")
    
    # Keep application running
    await idle()

    # Clean shutdown
    logger.info("Shutting down StreamVault...")
    stop_tunnel()
    await bot.stop()
    await web_runner.cleanup()

if __name__ == "__main__":
    if not config.validate_config():
        logger.warning("Application started with incomplete configuration. Please check your .env settings.")
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("StreamVault stopped.")
