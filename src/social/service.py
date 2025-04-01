"""
Social media monitoring service for the Meme Coin Signal Bot.

This module provides a service that periodically monitors social media platforms
for mentions of meme coins and updates the database with social mention information.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..config import (
    SOCIAL_MEDIA_SCAN_INTERVAL, MEME_KEYWORDS, 
    INFLUENCER_ACCOUNTS
)
from ..database import get_session, Token, SocialMention, SocialMentionType
from .twitter import TwitterMonitor
from .telegram import TelegramMonitor

# Configure logging
logger = logging.getLogger(__name__)

class SocialMediaMonitoringService:
    """Service for monitoring social media and updating the database."""
    
    def __init__(self):
        """Initialize the social media monitoring service."""
        self.twitter_monitor = TwitterMonitor()
        self.telegram_monitor = TelegramMonitor()
        self.running = False
    
    async def start(self):
        """Start the social media monitoring service."""
        self.running = True
        logger.info("Starting social media monitoring service")
        
        # Initialize Telegram monitor
        await self.telegram_monitor.initialize()
        
        # Add Telegram groups to monitor
        # In production, these would be loaded from a configuration file or database
        await self.telegram_monitor.add_group_to_monitor("memecoin_signals")
        await self.telegram_monitor.add_group_to_monitor("crypto_gems")
        await self.telegram_monitor.add_group_to_monitor("solana_memes")
        
        while self.running:
            try:
                # Monitor Twitter
                await self._monitor_twitter()
                
                # Monitor Telegram
                await self._monitor_telegram()
                
                # Wait for next scan
                logger.info(f"Social media scan completed. Next scan in {SOCIAL_MEDIA_SCAN_INTERVAL} seconds")
                await asyncio.sleep(SOCIAL_MEDIA_SCAN_INTERVAL)
            
            except Exception as e:
                logger.error(f"Error in social media monitoring service: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def stop(self):
        """Stop the social media monitoring service."""
        self.running = False
        logger.info("Stopping social media monitoring service")
        
        # Close Telegram client
        await self.telegram_monitor.close()
    
    async def _monitor_twitter(self):
        """Monitor Twitter for meme coin mentions."""
        logger.info("Monitoring Twitter for meme coin mentions")
        
        try:
            # Search for mentions of meme keywords
            mentions = await self.twitter_monitor.search_for_mentions(MEME_KEYWORDS)
            
            # Process mentions
            for mention in mentions:
                await self._process_social_mention(mention, SocialMentionType.TWITTER)
            
            # Monitor influencer accounts
            influencer_posts = await self.twitter_monitor.monitor_influencers(INFLUENCER_ACCOUNTS)
            
            # Process influencer posts
            for post in influencer_posts:
                await self._process_social_mention(post, SocialMentionType.TWITTER)
        
        except Exception as e:
            logger.error(f"Error monitoring Twitter: {str(e)}")
    
    async def _monitor_telegram(self):
        """Monitor Telegram for meme coin mentions."""
        logger.info("Monitoring Telegram for meme coin mentions")
        
        try:
            # Search for mentions of meme keywords
            mentions = await self.telegram_monitor.search_for_mentions(MEME_KEYWORDS)
            
            # Process mentions
            for mention in mentions:
                await self._process_social_mention(mention, SocialMentionType.TELEGRAM)
            
            # Monitor influencer accounts
            # In a real implementation, we would have a list of Telegram influencers
            telegram_influencers = ["cryptosignals", "memecoin_alerts"]
            influencer_posts = await self.telegram_monitor.monitor_influencers(telegram_influencers)
            
            # Process influencer posts
            for post in influencer_posts:
                await self._process_social_mention(post, SocialMentionType.TELEGRAM)
        
        except Exception as e:
            logger.error(f"Error monitoring Telegram: {str(e)}")
    
    async def _process_social_mention(self, mention: Dict[str, Any], source_type: SocialMentionType):
        """
        Process a social media mention and update the database.
        
        Args:
            mention: Dictionary containing mention information.
            source_type: The source type (Twitter or Telegram).
        """
        try:
            # Extract token mentions
            monitor = self.twitter_monitor if source_type == SocialMentionType.TWITTER else self.telegram_monitor
            token_mentions = await monitor.extract_token_mentions(mention.get('content', ''))
            
            if not token_mentions:
                return
            
            # Analyze sentiment
            sentiment_score = await monitor.analyze_sentiment(mention.get('content', ''))
            
            # Get a database session
            session = next(get_session())
            
            try:
                # Process each token mention
                for token_mention in token_mentions:
                    # Try to find the token in the database
                    token = None
                    
                    if 'symbol' in token_mention:
                        # Search by symbol
                        token = session.query(Token).filter(Token.symbol == token_mention['symbol']).first()
                    
                    elif 'address' in token_mention:
                        # Search by address
                        token = session.query(Token).filter(Token.address == token_mention['address']).first()
                    
                    if token:
                        # Create social mention
                        social_mention = SocialMention(
                            token_id=token.id,
                            source=source_type,
                            author=mention.get('author', ''),
                            is_influencer=mention.get('is_influencer', False),
                            content=mention.get('content', ''),
                            url=mention.get('url', ''),
                            timestamp=mention.get('timestamp', datetime.utcnow()),
                            sentiment_score=sentiment_score
                        )
                        
                        # Add to database
                        session.add(social_mention)
                        session.commit()
                        logger.info(f"Added social mention for token {token.symbol}")
            
            except Exception as e:
                logger.error(f"Error processing token mentions: {str(e)}")
                session.rollback()
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error processing social mention: {str(e)}")

# Singleton instance
social_monitoring_service = SocialMediaMonitoringService()
