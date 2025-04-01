"""
Telegram social media monitor implementation for the Meme Coin Signal Bot.

This module implements the SocialMediaMonitor interface for Telegram.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import InputPeerChannel, Channel, Chat, User

from ..config import MEME_KEYWORDS
from .base import SocialMediaMonitor

# Configure logging
logger = logging.getLogger(__name__)

# Telegram API credentials (would be in config in production)
API_ID = 12345  # Replace with actual API ID in production
API_HASH = "abcdef1234567890abcdef1234567890"  # Replace with actual API hash in production

class TelegramMonitor(SocialMediaMonitor):
    """Telegram social media monitor implementation."""
    
    def __init__(self):
        """Initialize the Telegram monitor."""
        self.client = None
        self.last_search_time = datetime.utcnow() - timedelta(hours=24)
        self.monitored_groups = []
    
    async def initialize(self):
        """Initialize the Telegram client."""
        if self.client is None:
            try:
                # Create and start the client
                self.client = TelegramClient('meme_coin_bot_session', API_ID, API_HASH)
                await self.client.start()
                logger.info("Telegram client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Telegram client: {str(e)}")
                self.client = None
    
    async def add_group_to_monitor(self, group_link: str):
        """
        Add a Telegram group to monitor.
        
        Args:
            group_link: The Telegram group link or username.
        """
        if group_link not in self.monitored_groups:
            self.monitored_groups.append(group_link)
            logger.info(f"Added Telegram group to monitor: {group_link}")
    
    async def search_for_mentions(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for mentions of keywords in monitored Telegram groups.
        
        Args:
            keywords: List of keywords to search for.
            
        Returns:
            List of dictionaries containing mention information.
        """
        logger.info(f"Searching Telegram for mentions of {len(keywords)} keywords")
        mentions = []
        
        if not self.client:
            await self.initialize()
            if not self.client:
                return []
        
        try:
            for group in self.monitored_groups:
                try:
                    # Get the entity (channel/group)
                    entity = await self.client.get_entity(group)
                    
                    # Get messages from the group
                    messages = await self.client(GetHistoryRequest(
                        peer=entity,
                        limit=100,
                        offset_date=self.last_search_time,
                        offset_id=0,
                        max_id=0,
                        min_id=0,
                        add_offset=0,
                        hash=0
                    ))
                    
                    # Process messages
                    for message in messages.messages:
                        if not message.message:
                            continue
                        
                        # Check if message contains any of the keywords
                        if any(keyword.lower() in message.message.lower() for keyword in keywords):
                            # Get sender information
                            if message.from_id:
                                sender = await self.client.get_entity(message.from_id)
                                sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Unknown')
                            else:
                                sender_name = 'Unknown'
                            
                            # Create mention info
                            mention_info = {
                                'source': 'telegram',
                                'author': sender_name,
                                'is_influencer': False,  # Could check against a list of influencers
                                'content': message.message,
                                'url': f"https://t.me/{group}/{message.id}" if isinstance(group, str) else None,
                                'timestamp': message.date,
                                'group': group
                            }
                            
                            mentions.append(mention_info)
                
                except Exception as e:
                    logger.error(f"Error searching Telegram group '{group}': {str(e)}")
            
            # Update last search time
            self.last_search_time = datetime.utcnow()
            
            logger.info(f"Found {len(mentions)} mentions on Telegram")
            return mentions
        
        except Exception as e:
            logger.error(f"Error searching Telegram: {str(e)}")
            return []
    
    async def monitor_influencers(self, influencer_accounts: List[str]) -> List[Dict[str, Any]]:
        """
        Monitor influencer accounts for new posts.
        
        Args:
            influencer_accounts: List of influencer Telegram usernames.
            
        Returns:
            List of dictionaries containing post information.
        """
        logger.info(f"Monitoring {len(influencer_accounts)} Telegram influencers")
        posts = []
        
        if not self.client:
            await self.initialize()
            if not self.client:
                return []
        
        try:
            for influencer in influencer_accounts:
                try:
                    # Get the entity (user/channel)
                    entity = await self.client.get_entity(influencer)
                    
                    # Get messages from the user/channel
                    messages = await self.client(GetHistoryRequest(
                        peer=entity,
                        limit=20,
                        offset_date=None,
                        offset_id=0,
                        max_id=0,
                        min_id=0,
                        add_offset=0,
                        hash=0
                    ))
                    
                    # Process messages
                    for message in messages.messages:
                        if not message.message:
                            continue
                        
                        # Check if message contains meme-related keywords
                        if self._contains_meme_keywords(message.message):
                            # Create post info
                            post_info = {
                                'source': 'telegram',
                                'author': influencer,
                                'is_influencer': True,
                                'content': message.message,
                                'url': f"https://t.me/{influencer}/{message.id}" if isinstance(influencer, str) else None,
                                'timestamp': message.date
                            }
                            
                            posts.append(post_info)
                
                except Exception as e:
                    logger.error(f"Error monitoring Telegram influencer '{influencer}': {str(e)}")
            
            logger.info(f"Found {len(posts)} new posts from Telegram influencers")
            return posts
        
        except Exception as e:
            logger.error(f"Error monitoring Telegram influencers: {str(e)}")
            return []
    
    def _contains_meme_keywords(self, content: str) -> bool:
        """
        Check if content contains meme-related keywords.
        
        Args:
            content: The text content to check.
            
        Returns:
            True if content contains meme keywords, False otherwise.
        """
        content_lower = content.lower()
        for keyword in MEME_KEYWORDS:
            if keyword.lower() in content_lower:
                return True
        return False
    
    async def analyze_sentiment(self, content: str) -> float:
        """
        Analyze the sentiment of a social media post.
        
        Args:
            content: The text content of the post.
            
        Returns:
            Sentiment score between -1.0 (negative) and 1.0 (positive).
        """
        try:
            # In a real implementation, use a sentiment analysis library or API
            # For simplicity, we'll use a basic keyword-based approach
            
            positive_keywords = [
                "bullish", "moon", "pump", "gem", "buy", "hodl", "hold", "good",
                "great", "amazing", "excellent", "profit", "gains", "win", "winning",
                "100x", "1000x", "opportunity", "undervalued", "potential"
            ]
            
            negative_keywords = [
                "bearish", "dump", "sell", "scam", "rug", "rugpull", "bad",
                "terrible", "awful", "loss", "losing", "crash", "down", "overvalued",
                "avoid", "stay away", "ponzi", "honeypot"
            ]
            
            content_lower = content.lower()
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in content_lower)
            negative_count = sum(1 for keyword in negative_keywords if keyword in content_lower)
            
            total_count = positive_count + negative_count
            if total_count == 0:
                return 0.0
            
            sentiment_score = (positive_count - negative_count) / total_count
            return max(-1.0, min(1.0, sentiment_score))  # Clamp to [-1.0, 1.0]
        
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return 0.0
    
    async def extract_token_mentions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract token mentions from a social media post.
        
        Args:
            content: The text content of the post.
            
        Returns:
            List of dictionaries containing token information.
        """
        try:
            # In a real implementation, use more sophisticated NLP techniques
            # For simplicity, we'll use regex to find potential token symbols
            
            # Pattern for token symbols (e.g., $BTC, $ETH, $DOGE)
            symbol_pattern = r'\$([A-Za-z0-9]{2,10})'
            
            # Find all matches
            matches = re.findall(symbol_pattern, content)
            
            # Create token mentions
            token_mentions = []
            for match in matches:
                token_mentions.append({
                    'symbol': match.upper(),
                    'context': content
                })
            
            # Also look for contract addresses
            eth_address_pattern = r'0x[a-fA-F0-9]{40}'
            sol_address_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
            
            eth_addresses = re.findall(eth_address_pattern, content)
            for address in eth_addresses:
                token_mentions.append({
                    'address': address,
                    'blockchain': 'ethereum',
                    'context': content
                })
            
            sol_addresses = re.findall(sol_address_pattern, content)
            for address in sol_addresses:
                # Filter out false positives (this is a simplified approach)
                if len(address) >= 32:
                    token_mentions.append({
                        'address': address,
                        'blockchain': 'solana',
                        'context': content
                    })
            
            return token_mentions
        
        except Exception as e:
            logger.error(f"Error extracting token mentions: {str(e)}")
            return []
    
    async def close(self):
        """Close the Telegram client."""
        if self.client:
            await self.client.disconnect()
            self.client = None
            logger.info("Telegram client closed")
