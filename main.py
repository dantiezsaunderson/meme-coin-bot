"""
Modified main application runner for the Meme Coin Signal Bot.

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
from src.blockchain.service import scanner_service
from src.social.service import social_monitoring_service
from src.scoring.service import scoring_service
from src.telegram_bot import telegram_bot
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
        
        # Start services
        tasks = []
        
        # Start blockchain scanner service with error handling
        try:
            logger.info("Starting blockchain scanner service...")
            tasks.append(asyncio.create_task(scanner_service.start()))
        except Exception as e:
            logger.error(f"Failed to start blockchain scanner service: {str(e)}")
            logger.info("Continuing without blockchain scanner service...")
        
        # Start social media monitoring service with error handling
        try:
            logger.info("Starting social media monitoring service...")
            tasks.append(asyncio.create_task(social_monitoring_service.start()))
        except Exception as e:
            logger.error(f"Failed to start social media monitoring service: {str(e)}")
            logger.info("Continuing without social media monitoring service...")
        
        # Start scoring service with error handling
        try:
            logger.info("Starting scoring service...")
            tasks.append(asyncio.create_task(scoring_service.start()))
        except Exception as e:
            logger.error(f"Failed to start scoring service: {str(e)}")
            logger.info("Continuing without scoring service...")
        
        # Start Telegram bot with error handling
        try:
            logger.info("Starting Telegram bot...")
            tasks.append(asyncio.create_task(telegram_bot.start()))
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {str(e)}")
            logger.info("Continuing without Telegram bot...")
        
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
            await social_monitoring_service.stop()
            await scoring_service.stop()
            await telegram_bot.stop()
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
    
    except Exception as e:
        logger.error(f"Critical error in main function: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
