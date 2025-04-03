"""
Main application runner for the Meme Coin Bot.
This module initializes and starts all services including the health API.
"""
import asyncio
import logging
import os
import uvicorn
from dotenv import load_dotenv
from threading import Thread
import sys

from src.database import init_db
from src.scanners.service import scanner_service
from src.filters.service import filter_service
from src.scoring.service import scoring_service
from src.signals.service import signal_service
from src.telegram.bot import telegram_bot
from src.health_api import app as health_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Health API port
HEALTH_API_PORT = int(os.getenv("PORT", 8000))

def run_health_api():
    """Run the health API in a separate thread."""
    uvicorn.run(health_app, host="0.0.0.0", port=HEALTH_API_PORT)

async def main():
    """Initialize and start all services."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Start health API in a separate thread
        logger.info(f"Starting health API on port {HEALTH_API_PORT}...")
        health_thread = Thread(target=run_health_api, daemon=True)
        health_thread.start()
        
        # Initialize services
        logger.info("Initializing services...")
        
        # Initialize Telegram bot first
        logger.info("Initializing Telegram bot...")
        telegram_initialized = await telegram_bot.initialize()
        if not telegram_initialized:
            logger.error("Failed to initialize Telegram bot")
            logger.warning("Continuing without Telegram bot...")
        
        # Initialize scanner service
        logger.info("Initializing scanner service...")
        scanner_initialized = await scanner_service.initialize()
        if not scanner_initialized:
            logger.error("Failed to initialize scanner service")
            return
        
        # Initialize signal service with Telegram bot
        logger.info("Initializing signal service...")
        signal_initialized = await signal_service.initialize(telegram_bot)
        if not signal_initialized:
            logger.error("Failed to initialize signal service")
            return
        
        # Initialize scoring service with other services
        logger.info("Initializing scoring service...")
        scoring_initialized = await scoring_service.initialize(
            scanner_service, filter_service, signal_service
        )
        if not scoring_initialized:
            logger.error("Failed to initialize scoring service")
            return
        
        # Start services
        tasks = []
        
        # Start scanner service
        logger.info("Starting scanner service...")
        tasks.append(asyncio.create_task(scanner_service.start()))
        
        # Start scoring service
        logger.info("Starting scoring service...")
        tasks.append(asyncio.create_task(scoring_service.start()))
        
        # Start signal service
        logger.info("Starting signal service...")
        tasks.append(asyncio.create_task(signal_service.start()))
        
        # Start Telegram bot
        if telegram_initialized:
            logger.info("Starting Telegram bot...")
            tasks.append(asyncio.create_task(telegram_bot.start()))
        
        if not tasks:
            logger.error("No services could be started. Exiting...")
            return
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            
            # Stop all services
            await scanner_service.stop()
            await scoring_service.stop()
            await signal_service.stop()
            if telegram_initialized:
                await telegram_bot.stop()
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
    
    except Exception as e:
        logger.error(f"Critical error in main function: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
