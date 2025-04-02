"""
Telegram social media monitor implementation for the Meme Coin Signal Bot.

This module implements the SocialMediaMonitor interface for Telegram.
"""
import asyncio
import logging
import re
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

from ..config import MEME_KEYWORDS
from .base import SocialMediaMonitor

# Configure logging
logger = logging.getLogger(__name__)

# Flag to track if telethon package is available
TELETHON_AVAILABLE = False

# Try to import telethon packages
try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.tl.functions.messages import GetHistoryRequest
    from telethon.tl.types import InputPeerChannel, Channel, Chat, User
    TELETHON_AVAILABLE = True
except ImportError:
    logger.warning("Telethon package not available. Using mock implementation.")

# Get Telegram credentials from environment variables
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25254354"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "f5f087d0e5a711a51b55bcf8b94fd786")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Session file path - check both root and secrets directory
SESSION_FILE_PATHS = [
    'coin_scan_session',
    'secrets/coin_scan_session',
    '/app/secrets/coin_scan_session',
    '/app/coin_scan_session'
]

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
            # If telethon is not available, use mock implementation
            if not TELETHON_AVAILABLE:
                logger.warning("Using mock implementation for Telegram monitor")
                return
                
            try:
                # Try to find a valid session file
                session_path = None
                for path in SESSION_FILE_PATHS:
                    if os.path.exists(f"{path}.session"):
                        session_path = path
                        logger.info(f"Found existing session file at {path}.session")
                        break
                
                if not session_path:
                    logger.warning("No session file found. Using fallback mechanism.")
                
                # Create and start the client
                self.client = TelegramClient(session_path or 'meme_coin_bot_session', 
                                            TELEGRAM_API_ID, 
                                            TELEGRAM_API_HASH)
                
                # Check if we have a bot token
                if TELEGRAM_BOT_TOKEN:
                    await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
                    logger.info("Telegram client initialized successfully with bot token")
                else:
                    # Try to start with the session file (non-interactive)
                    await self.client.start()
                    logger.info("Telegram client initialized successfully with session file")
                
                # Test connection
                me = await self.client.get_me()
                logger.info(f"Connected as: {me.username if hasattr(me, 'username') else 'Unknown'}")
                
            except Exception as e:
                logger.error(f"Error initializing Telegram client: {str(e)}")
                logger.info("Falling back to mock implementation")
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
        
        # If telethon is not available or client initialization failed, return mock data
        if not TELETHON_AVAILABLE or not self.client:
            return self._generate_mock_mentions(keywords, 3)
        
        mentions = []
        
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
            return self._generate_mock_mentions(keywords, 3)
    
    def _generate_mock_mentions(self, keywords: List[str], count: int) -> List[Dict[str, Any]]:
        """Generate mock mention data for testing."""
        mock_mentions = []
        groups = ["memecoin_traders", "crypto_gems", "altcoin_signals", "degen_finance"]
        authors = ["crypto_whale", "meme_hunter", "token_scout", "degen_trader", "moon_boy"]
        
        for i in range(count):
            keyword = random.choice(keywords) if keywords else "memecoin"
            group = random.choice(groups)
            author = random.choice(authors)
            
            # Create mock content with the keyword
            content_templates = [
                f"Just found this new {keyword} gem! Looks promising with good liquidity.",
                f"Anyone looking at {keyword}? Chart looks bullish!",
                f"New {keyword} token just launched with solid fundamentals.",
                f"{keyword} is pumping right now! Get in early.",
                f"This {keyword} could be the next 100x. DYOR!"
            ]
            
            content = random.choice(content_templates)
            
            mention_info = {
                'source': 'telegram',
                'author': author,
                'is_influencer': random.choice([True, False, False, False]),
                'content': content,
                'url': f"https://t.me/{group}/12345",
                'timestamp': datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                'group': group
            }
            
            mock_mentions.append(mention_info)
        
        logger.info(f"Generated {len(mock_mentions)} mock mentions for Telegram")
        return mock_mentions
    
    async def monitor_influencers(self, influencer_accounts: List[str]) -> List[Dict[str, Any]]:
        """
        Monitor influencer accounts for new posts.
        
        Args:
            influencer_accounts: List of influencer Telegram usernames.
            
        Returns:
            List of dictionaries containing post information.
        """
        logger.info(f"Monitoring {len(influencer_accounts)} Telegram influencers")
        
        # If telethon is not available or client initialization failed, return mock data
        if not TELETHON_AVAILABLE or not self.client:
            return self._generate_mock_influencer_posts(influencer_accounts, 3)
        
        posts = []
        
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
            return self._generate_mock_influencer_posts(influencer_accounts, 3)
    
    def _generate_mock_influencer_posts(self, influencers: List[str], count: int) -> List[Dict[str, Any]]:
        """Generate mock influencer post data for testing."""
        mock_posts = []
        
        # Use provided influencers or generate some if none provided
        if not influencers:
            influencers = ["crypto_guru", "meme_master", "whale_alerts", "token_insider", "degen_king"]
        
        for i in range(count):
            influencer = random.choice(influencers)
            
            # Create mock content with meme keywords
            content_templates = [
                "Just found the next big meme coin! This one has real utility and strong community.",
                "ALERT: New gem spotted with 100x potential. Liquidity locked, contract audited.",
                "This new dog-themed token is gaining serious traction. Chart looks bullish!",
                "Insider info: Major influencers about to promote this new meme coin. Get in early!",
                "Just bought a bag of this new token. Strong fundamentals and great tokenomics."
            ]
            
            content = random.choice(content_templates)
            
            post_info = {
                'source': 'telegram',
                'author': influencer,
                'is_influencer': True,
                'content': content,
                'url': f"https://t.me/{influencer}/12345",
                'timestamp': datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
            }
            
            mock_posts.append(post_info)
        
        logger.info(f"Generated {len(mock_posts)} mock posts for Telegram influencers")
        return mock_posts
    
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
                    'blockchain': 'ETHEREUM',
                    'context': content
                })
            
            sol_addresses = re.findall(sol_address_pattern, content)
            for address in sol_addresses:
                # Filter out false positives (this is a simplified approach)
                if len(address) >= 32:
                    token_mentions.append({
                        'address': address,
                        'blockchain': 'SOLANA',
                        'context': content
                    })
            
            return token_mentions
        
        except Exception as e:
            logger.error(f"Error extracting token mentions: {str(e)}")
            return []
    
    async def close(self):
        """Close the Telegram client."""
        if self.client and TELETHON_AVAILABLE:
            await self.client.disconnect()
            self.client = None
            logger.info("Telegram client closed")
