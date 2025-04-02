"""
Twitter social media monitor implementation for the Meme Coin Signal Bot.

This module implements the SocialMediaMonitor interface for Twitter/X.
"""
import asyncio
import logging
import re
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import json

from ..config import MEME_KEYWORDS
from .base import SocialMediaMonitor

# Configure logging
logger = logging.getLogger(__name__)

# Flag to track if data_api is available
DATA_API_AVAILABLE = False

# Try to import data_api
try:
    sys.path.append('/opt/.manus/.sandbox-runtime')
    from data_api import ApiClient
    DATA_API_AVAILABLE = True
    logger.info("Successfully imported data_api module")
except ImportError as e:
    logger.warning(f"Could not import data_api module: {str(e)}. Using mock implementation.")

class TwitterMonitor(SocialMediaMonitor):
    """Twitter social media monitor implementation."""
    
    def __init__(self):
        """Initialize the Twitter monitor."""
        self.api_client = None
        self.last_search_time = datetime.utcnow() - timedelta(hours=24)
        self.monitored_keywords = []
        
        # Initialize API client if available
        if DATA_API_AVAILABLE:
            try:
                self.api_client = ApiClient()
                logger.info("Twitter API client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Twitter API client: {str(e)}")
                self.api_client = None
    
    async def search_for_mentions(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for mentions of keywords on Twitter.
        
        Args:
            keywords: List of keywords to search for.
            
        Returns:
            List of dictionaries containing mention information.
        """
        logger.info(f"Searching Twitter for mentions of {len(keywords)} keywords")
        
        # If data_api is not available, return mock data
        if not DATA_API_AVAILABLE or not self.api_client:
            return self._generate_mock_mentions(keywords, 5)
        
        mentions = []
        
        try:
            for keyword in keywords:
                try:
                    # Search Twitter for the keyword
                    query = f"{keyword} crypto OR token OR coin"
                    response = self.api_client.call_api('Twitter/search_twitter', query={
                        'query': query,
                        'count': 20,
                        'type': 'Latest'
                    })
                    
                    # Process search results
                    if response and 'result' in response and 'timeline' in response['result']:
                        timeline = response['result']['timeline']
                        if 'instructions' in timeline:
                            for instruction in timeline['instructions']:
                                if 'entries' in instruction:
                                    for entry in instruction['entries']:
                                        if 'content' in entry and 'items' in entry['content']:
                                            for item in entry['content']['items']:
                                                if 'item' in item and 'itemContent' in item['item']:
                                                    content = item['item']['itemContent']
                                                    if 'user_results' in content and 'result' in content['user_results']:
                                                        user = content['user_results']['result']
                                                        if 'legacy' in user:
                                                            user_info = user['legacy']
                                                            
                                                            # Create mention info
                                                            mention_info = {
                                                                'source': 'twitter',
                                                                'author': user_info.get('screen_name', 'Unknown'),
                                                                'is_influencer': user_info.get('followers_count', 0) > 10000,
                                                                'content': item.get('text', ''),
                                                                'url': f"https://twitter.com/{user_info.get('screen_name')}/status/{item.get('id_str')}",
                                                                'timestamp': datetime.strptime(user_info.get('created_at', ''), '%a %b %d %H:%M:%S +0000 %Y'),
                                                                'followers_count': user_info.get('followers_count', 0)
                                                            }
                                                            
                                                            mentions.append(mention_info)
                
                except Exception as e:
                    logger.error(f"Error searching Twitter for keyword '{keyword}': {str(e)}")
            
            # Update last search time
            self.last_search_time = datetime.utcnow()
            
            logger.info(f"Found {len(mentions)} mentions on Twitter")
            return mentions
        
        except Exception as e:
            logger.error(f"Error searching Twitter: {str(e)}")
            return self._generate_mock_mentions(keywords, 5)
    
    def _generate_mock_mentions(self, keywords: List[str], count: int) -> List[Dict[str, Any]]:
        """Generate mock mention data for testing."""
        mock_mentions = []
        authors = ["crypto_whale", "meme_hunter", "token_scout", "degen_trader", "moon_boy"]
        
        for i in range(count):
            keyword = random.choice(keywords) if keywords else "memecoin"
            author = random.choice(authors)
            
            # Create mock content with the keyword
            content_templates = [
                f"Just found this new {keyword} gem! Looks promising with good liquidity. #crypto #memecoin",
                f"Anyone looking at {keyword}? Chart looks bullish! #crypto #altcoin",
                f"New {keyword} token just launched with solid fundamentals. #crypto #gem",
                f"{keyword} is pumping right now! Get in early. #crypto #moonshot",
                f"This {keyword} could be the next 100x. DYOR! #crypto #altseason"
            ]
            
            content = random.choice(content_templates)
            
            mention_info = {
                'source': 'twitter',
                'author': author,
                'is_influencer': random.choice([True, False, False, False]),
                'content': content,
                'url': f"https://twitter.com/{author}/status/123456789",
                'timestamp': datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                'followers_count': random.randint(1000, 100000)
            }
            
            mock_mentions.append(mention_info)
        
        logger.info(f"Generated {len(mock_mentions)} mock mentions for Twitter")
        return mock_mentions
    
    async def monitor_influencers(self, influencer_accounts: List[str]) -> List[Dict[str, Any]]:
        """
        Monitor influencer accounts for new posts.
        
        Args:
            influencer_accounts: List of influencer Twitter usernames.
            
        Returns:
            List of dictionaries containing post information.
        """
        logger.info(f"Monitoring {len(influencer_accounts)} Twitter influencers")
        
        # If data_api is not available, return mock data
        if not DATA_API_AVAILABLE or not self.api_client:
            return self._generate_mock_influencer_posts(influencer_accounts, 5)
        
        posts = []
        
        try:
            for influencer in influencer_accounts:
                try:
                    # Get user profile
                    user_profile = self.api_client.call_api('Twitter/get_user_profile_by_username', query={
                        'username': influencer
                    })
                    
                    if not user_profile or 'result' not in user_profile or 'data' not in user_profile['result']:
                        logger.warning(f"Could not get profile for Twitter influencer '{influencer}'")
                        continue
                    
                    # Get user ID
                    user_data = user_profile['result']['data']['user']['result']
                    user_id = user_data.get('rest_id')
                    
                    if not user_id:
                        logger.warning(f"Could not get user ID for Twitter influencer '{influencer}'")
                        continue
                    
                    # Get user tweets
                    tweets = self.api_client.call_api('Twitter/get_user_tweets', query={
                        'user': user_id,
                        'count': 20
                    })
                    
                    if not tweets or 'result' not in tweets or 'timeline' not in tweets['result']:
                        logger.warning(f"Could not get tweets for Twitter influencer '{influencer}'")
                        continue
                    
                    # Process tweets
                    timeline = tweets['result']['timeline']
                    if 'instructions' in timeline:
                        for instruction in timeline['instructions']:
                            if 'entries' in instruction:
                                for entry in instruction['entries']:
                                    if 'content' in entry and 'itemContent' in entry['content']:
                                        content = entry['content']['itemContent']
                                        if 'tweet_results' in content and 'result' in content['tweet_results']:
                                            tweet = content['tweet_results']['result']
                                            if 'legacy' in tweet:
                                                tweet_info = tweet['legacy']
                                                
                                                # Check if tweet contains meme-related keywords
                                                if self._contains_meme_keywords(tweet_info.get('full_text', '')):
                                                    # Create post info
                                                    post_info = {
                                                        'source': 'twitter',
                                                        'author': influencer,
                                                        'is_influencer': True,
                                                        'content': tweet_info.get('full_text', ''),
                                                        'url': f"https://twitter.com/{influencer}/status/{tweet_info.get('id_str')}",
                                                        'timestamp': datetime.strptime(tweet_info.get('created_at', ''), '%a %b %d %H:%M:%S +0000 %Y'),
                                                        'likes': tweet_info.get('favorite_count', 0),
                                                        'retweets': tweet_info.get('retweet_count', 0)
                                                    }
                                                    
                                                    posts.append(post_info)
                
                except Exception as e:
                    logger.error(f"Error monitoring Twitter influencer '{influencer}': {str(e)}")
            
            logger.info(f"Found {len(posts)} new posts from Twitter influencers")
            return posts
        
        except Exception as e:
            logger.error(f"Error monitoring Twitter influencers: {str(e)}")
            return self._generate_mock_influencer_posts(influencer_accounts, 5)
    
    def _generate_mock_influencer_posts(self, influencers: List[str], count: int) -> List[Dict[str, Any]]:
        """Generate mock influencer post data for testing."""
        mock_posts = []
        
        # Use provided influencers or generate some if none provided
        if not influencers:
            influencers = ["elonmusk", "ShibaInuHodler", "DogeWhisperer", "CryptoKaleo", "cryptogemfinder"]
        
        for i in range(count):
            influencer = random.choice(influencers)
            
            # Create mock content with meme keywords
            content_templates = [
                "Just found the next big meme coin! This one has real utility and strong community. #crypto #memecoin",
                "ALERT: New gem spotted with 100x potential. Liquidity locked, contract audited. #crypto #altcoin",
                "This new dog-themed token is gaining serious traction. Chart looks bullish! #crypto #doge",
                "Insider info: Major influencers about to promote this new meme coin. Get in early! #crypto #gem",
                "Just bought a bag of this new token. Strong fundamentals and great tokenomics. #crypto #altseason"
            ]
            
            content = random.choice(content_templates)
            
            post_info = {
                'source': 'twitter',
                'author': influencer,
                'is_influencer': True,
                'content': content,
                'url': f"https://twitter.com/{influencer}/status/123456789",
                'timestamp': datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                'likes': random.randint(100, 5000),
                'retweets': random.randint(10, 1000)
            }
            
            mock_posts.append(post_info)
        
        logger.info(f"Generated {len(mock_posts)} mock posts for Twitter influencers")
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
