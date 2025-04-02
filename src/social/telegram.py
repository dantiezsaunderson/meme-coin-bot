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
from pathlib import Path

from ..config import MEME_KEYWORDS, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_SESSION_PATHS
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
                for path in TELEGRAM_SESSION_PATHS:
                    if os.path.exists(f"{path}.session"):
                        session_path = path
                        logger.info(f"Found existing session file at {path}.session")
                        break
                
                if not session_path:
                    logger.warning("No session file found. Using fallback mechanism.")
                    # Create data directory if it doesn't exist
                    os.makedirs('secrets', exist_ok=True)
                    session_path = 'secrets/telegram_session'
                
                # Create and start the client
                self.client = TelegramClient(session_path, 
                                           TELEGRAM_API_ID, 
                                           TELEGRAM_API_HASH)
                
                # Check if we have a bot token
                if TELEGRAM_BOT_TOKEN:
                    try:
                        # Try to start with bot token (non-interactive)
                        await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
                        logger.info("Telegram client initialized successfully with bot token")
                    except Exception as e:
                        logger.error(f"Error starting with bot token: {str(e)}")
                        # Try to start without bot token (non-interactive)
                        await self.client.start()
                        logger.info("Telegram client initialized successfully with session file")
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
            logger.info("Using mock data for Telegram mentions")
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
            logger.info("Using mock data for Telegram influencers")
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
                        
                        # Check if message contains any meme coin related keywords
                        if any(keyword.lower() in message.message.lower() for keyword in MEME_KEYWORDS):
                            # Create post info
                            post_info = {
                                'source': 'telegram',
                                'author': influencer,
                                'is_influencer': True,
                                'content': message.message,
                                'url': f"https://t.me/{influencer}/{message.id}" if isinstance(influencer, str) else None,
                                'timestamp': message.date,
                                'followers': 0  # Telegram doesn't provide follower count easily
                            }
                            
                            posts.append(post_info)
                
                except Exception as e:
                    logger.error(f"Error monitoring Telegram influencer '{influencer}': {str(e)}")
            
            logger.info(f"Found {len(posts)} influencer posts on Telegram")
            return posts
        
        except Exception as e:
            logger.error(f"Error monitoring Telegram influencers: {str(e)}")
            return self._generate_mock_influencer_posts(influencer_accounts, 3)
    
    def _generate_mock_influencer_posts(self, influencer_accounts: List[str], count: int) -> List[Dict[str, Any]]:
        """Generate mock influencer post data for testing."""
        mock_posts = []
        
        for i in range(count):
            influencer = random.choice(influencer_accounts) if influencer_accounts else "crypto_influencer"
            
            # Create mock content
            content_templates = [
                "Just found this new meme coin gem! Looks promising with good liquidity.",
                "This new token could be the next Doge or Shiba. NFA but worth checking out.",
                "New memecoin alert! This one has actual utility and strong community.",
                "Found a potential 100x meme coin. Early stage with solid team.",
                "This memecoin is pumping right now! Chart looks bullish."
            ]
            
            content = random.choice(content_templates)
            
            post_info = {
                'source': 'telegram',
                'author': influencer,
                'is_influencer': True,
                'content': content,
                'url': f"https://t.me/{influencer}/12345",
                'timestamp': datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                'followers': random.randint(10000, 500000)
            }
            
            mock_posts.append(post_info)
        
        logger.info(f"Generated {len(mock_posts)} mock influencer posts for Telegram")
        return mock_posts
    
    async def analyze_sentiment(self, content: str) -> float:
        """
        Analyze the sentiment of a social media post.
        
        Args:
            content: The text content of the post.
            
        Returns:
            Sentiment score between -1.0 (negative) and 1.0 (positive).
        """
        logger.info(f"Analyzing sentiment for Telegram content")
        
        # Simple rule-based sentiment analysis
        # In a production environment, this would use a proper NLP model
        positive_words = [
            "bullish", "moon", "gem", "100x", "1000x", "pump", "buy", "good", "great", "excellent",
            "amazing", "solid", "strong", "promising", "potential", "opportunity", "early", "gains",
            "profit", "winner", "winning", "success", "successful", "up", "rising", "rise", "green"
        ]
        
        negative_words = [
            "bearish", "dump", "sell", "bad", "poor", "weak", "scam", "rug", "rugpull", "ponzi",
            "avoid", "stay away", "risky", "risk", "dangerous", "suspicious", "red flag", "warning",
            "crash", "down", "falling", "fall", "red", "loss", "losing", "fail", "failure"
        ]
        
        # Convert to lowercase for case-insensitive matching
        content_lower = content.lower()
        
        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        # Calculate sentiment score
        total_count = positive_count + negative_count
        if total_count == 0:
            return 0.0  # Neutral sentiment
        
        sentiment_score = (positive_count - negative_count) / total_count
        
        # Ensure score is between -1.0 and 1.0
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        logger.info(f"Sentiment score: {sentiment_score}")
        return sentiment_score
    
    async def extract_token_mentions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract token mentions from a social media post.
        
        Args:
            content: The text content of the post.
            
        Returns:
            List of dictionaries containing token information.
        """
        logger.info(f"Extracting token mentions from Telegram content")
        
        # Regular expressions for finding token mentions
        # This is a simplified approach; a more sophisticated NLP approach would be better
        
        # Match $SYMBOL pattern (common in crypto)
        dollar_symbol_pattern = r'\$([A-Za-z0-9]{2,10})'
        
        # Match "Token/Coin Name" followed by optional (SYMBOL)
        token_name_pattern = r'([A-Z][A-Za-z0-9]+(?:\s[A-Z][A-Za-z0-9]+)*)\s*(?:\(([A-Z0-9]{2,10})\))?'
        
        # Match contract addresses (Ethereum-style)
        contract_address_pattern = r'0x[a-fA-F0-9]{40}'
        
        mentions = []
        
        # Find $SYMBOL mentions
        dollar_symbols = re.findall(dollar_symbol_pattern, content)
        for symbol in dollar_symbols:
            mentions.append({
                'symbol': symbol.upper(),
                'name': None,
                'address': None,
                'mention_type': 'symbol',
                'confidence': 0.9  # High confidence for $SYMBOL format
            })
        
        # Find token name mentions
        token_names = re.findall(token_name_pattern, content)
        for name_match in token_names:
            name, symbol = name_match
            # Skip common words that might be mistaken for token names
            common_words = ["THE", "AND", "THIS", "THAT", "JUST", "LIKE", "WITH", "FOR"]
            if name.upper() in common_words:
                continue
                
            mentions.append({
                'symbol': symbol.upper() if symbol else None,
                'name': name,
                'address': None,
                'mention_type': 'name',
                'confidence': 0.7 if symbol else 0.5  # Higher confidence if symbol is included
            })
        
        # Find contract addresses
        addresses = re.findall(contract_address_pattern, content)
        for address in addresses:
            mentions.append({
                'symbol': None,
                'name': None,
                'address': address.lower(),
                'mention_type': 'address',
                'confidence': 0.95  # Very high confidence for addresses
            })
        
        # Remove duplicates (prefer higher confidence)
        unique_mentions = {}
        for mention in mentions:
            key = mention['symbol'] or mention['name'] or mention['address']
            if key and (key not in unique_mentions or mention['confidence'] > unique_mentions[key]['confidence']):
                unique_mentions[key] = mention
        
        result = list(unique_mentions.values())
        logger.info(f"Extracted {len(result)} token mentions")
        return result
    
    async def close(self):
        """Close the Telegram client."""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")
