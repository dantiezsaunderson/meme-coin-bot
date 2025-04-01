"""
Test script for the Meme Coin Signal Bot.

This script tests the core functionality of the bot.
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

from src.database import init_db, get_session, Token, BlockchainType
from src.blockchain import get_scanner
from src.social.twitter import TwitterMonitor
from src.scoring.scorer import TokenScorer

async def test_ethereum_scanner():
    """Test the Ethereum blockchain scanner."""
    logger.info("Testing Ethereum scanner...")
    
    # Get Ethereum scanner
    scanner = get_scanner('ethereum')
    
    # Test scanning for new tokens
    tokens = await scanner.scan_for_new_tokens()
    logger.info(f"Found {len(tokens)} potential new tokens on Ethereum")
    
    # Test token liquidity
    if tokens:
        token_address = tokens[0]['address']
        liquidity = await scanner.get_token_liquidity(token_address)
        logger.info(f"Token liquidity: ${liquidity:.2f}")
        
        # Test contract safety
        safety = await scanner.check_contract_safety(token_address)
        logger.info(f"Contract safety: {safety}")
    
    logger.info("Ethereum scanner test completed")

async def test_solana_scanner():
    """Test the Solana blockchain scanner."""
    logger.info("Testing Solana scanner...")
    
    # Get Solana scanner
    scanner = get_scanner('solana')
    
    # Test scanning for new tokens
    tokens = await scanner.scan_for_new_tokens()
    logger.info(f"Found {len(tokens)} potential new tokens on Solana")
    
    # Test token liquidity
    if tokens:
        token_address = tokens[0]['address']
        liquidity = await scanner.get_token_liquidity(token_address)
        logger.info(f"Token liquidity: ${liquidity:.2f}")
        
        # Test contract safety
        safety = await scanner.check_contract_safety(token_address)
        logger.info(f"Contract safety: {safety}")
    
    logger.info("Solana scanner test completed")

async def test_twitter_monitor():
    """Test the Twitter monitor."""
    logger.info("Testing Twitter monitor...")
    
    # Create Twitter monitor
    monitor = TwitterMonitor()
    
    # Test searching for mentions
    keywords = ["meme coin", "memecoin", "doge", "shib"]
    mentions = await monitor.search_for_mentions(keywords)
    logger.info(f"Found {len(mentions)} mentions on Twitter")
    
    # Test monitoring influencers
    influencers = ["elonmusk", "ShibaInuHodler"]
    posts = await monitor.monitor_influencers(influencers)
    logger.info(f"Found {len(posts)} posts from influencers")
    
    # Test sentiment analysis
    content = "This new meme coin is going to the moon! 100x potential!"
    sentiment = await monitor.analyze_sentiment(content)
    logger.info(f"Sentiment score: {sentiment}")
    
    logger.info("Twitter monitor test completed")

async def test_token_scoring():
    """Test the token scoring algorithm."""
    logger.info("Testing token scoring...")
    
    # Initialize database
    init_db()
    
    # Create a test token
    session = next(get_session())
    
    # Check if test token already exists
    test_token = session.query(Token).filter(Token.symbol == "TEST").first()
    
    if not test_token:
        # Create a new test token
        test_token = Token(
            address="0x1234567890123456789012345678901234567890",
            name="Test Token",
            symbol="TEST",
            blockchain=BlockchainType.ETHEREUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            
            # Contract details
            contract_verified=True,
            is_honeypot=False,
            contract_audit_score=80.0,
            
            # Token metrics
            current_price_usd=0.0001,
            market_cap_usd=1000000.0,
            liquidity_usd=15000.0,
            volume_24h_usd=50000.0,
            holders_count=500,
            buy_sell_ratio=2.5,
        )
        
        session.add(test_token)
        session.commit()
    
    # Create token scorer
    scorer = TokenScorer()
    
    # Score tokens
    await scorer.score_tokens()
    
    # Get updated token
    session = next(get_session())
    updated_token = session.query(Token).filter(Token.id == test_token.id).first()
    
    logger.info(f"Token scores: Liquidity={updated_token.liquidity_score:.1f}, Volume={updated_token.volume_score:.1f}, Social={updated_token.social_score:.1f}, Safety={updated_token.safety_score:.1f}, Total={updated_token.total_score:.1f}")
    
    session.close()
    logger.info("Token scoring test completed")

async def main():
    """Run all tests."""
    logger.info("Starting tests...")
    
    try:
        # Test Ethereum scanner
        await test_ethereum_scanner()
        
        # Test Solana scanner
        await test_solana_scanner()
        
        # Test Twitter monitor
        await test_twitter_monitor()
        
        # Test token scoring
        await test_token_scoring()
        
        logger.info("All tests completed successfully")
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
