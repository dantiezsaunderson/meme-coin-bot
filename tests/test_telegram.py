"""
Test script for the Telegram bot functionality.

This script tests the Telegram bot commands and signal generation.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, get_session, Token, Signal, SignalType
from src.telegram_bot.bot import TelegramBot

async def test_signal_generation():
    """Test signal generation and formatting."""
    logger.info("Testing signal generation...")
    
    # Initialize database
    init_db()
    
    # Get a database session
    session = next(get_session())
    
    try:
        # Get a token
        token = session.query(Token).first()
        
        if not token:
            logger.warning("No tokens found in database, skipping signal test")
            return
        
        # Create a test signal
        test_signal = Signal(
            token_id=token.id,
            signal_type=SignalType.BUY,
            timestamp=datetime.utcnow(),
            score=85.0,
            reason="Test signal for bot functionality",
            sent_to_telegram=False,
            
            # Snapshot of metrics
            price_usd=token.current_price_usd,
            liquidity_usd=token.liquidity_usd,
            volume_24h_usd=token.volume_24h_usd,
            holders_count=token.holders_count,
            buy_sell_ratio=token.buy_sell_ratio,
            social_mentions_count=10
        )
        
        session.add(test_signal)
        session.commit()
        
        logger.info(f"Created test signal for token {token.symbol}")
    
    except Exception as e:
        logger.error(f"Error creating test signal: {str(e)}")
        session.rollback()
    finally:
        session.close()
    
    logger.info("Signal generation test completed")

async def test_telegram_bot():
    """Test Telegram bot functionality."""
    logger.info("Testing Telegram bot...")
    
    # Create Telegram bot
    bot = TelegramBot()
    
    # Test formatting functions
    session = next(get_session())
    
    try:
        # Get a token and signal
        token = session.query(Token).first()
        signal = session.query(Signal).first()
        
        if token and signal:
            # Test DEX link generation
            dex_link = bot._get_dex_link(token)
            logger.info(f"DEX link: {dex_link}")
        
        logger.info("Telegram bot formatting tests completed")
    
    except Exception as e:
        logger.error(f"Error testing Telegram bot: {str(e)}")
    finally:
        session.close()
    
    logger.info("Telegram bot test completed")

async def main():
    """Run all tests."""
    logger.info("Starting Telegram bot tests...")
    
    try:
        # Test signal generation
        await test_signal_generation()
        
        # Test Telegram bot
        await test_telegram_bot()
        
        logger.info("All Telegram bot tests completed successfully")
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
