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
    # Load environment variables
    load_dotenv()
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Start health API in a separate thread
    logger.info(f"Starting health API on port {HEALTH_API_PORT}...")
    health_thread = Thread(target=run_health_api, daemon=True)
    health_thread.start()
    
    # Start services
    tasks = []
    
    # Start blockchain scanner service
    logger.info("Starting blockchain scanner service...")
    tasks.append(asyncio.create_task(scanner_service.start()))
    
    # Start social media monitoring service
    logger.info("Starting social media monitoring service...")
    tasks.append(asyncio.create_task(social_monitoring_service.start()))
    
    # Start scoring service
    logger.info("Starting scoring service...")
    tasks.append(asyncio.create_task(scoring_service.start()))
    
    # Start Telegram bot
    logger.info("Starting Telegram bot...")
    tasks.append(asyncio.create_task(telegram_bot.start()))
    
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

if __name__ == "__main__":
    asyncio.run(main())
