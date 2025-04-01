"""
Twitter/X social media monitor implementation for the Meme Coin Signal Bot.

This module implements the SocialMediaMonitor interface for Twitter/X.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import json

from ..config import (
    TWITTER_API_KEY, TWITTER_API_SECRET, 
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET,
    MEME_KEYWORDS, INFLUENCER_ACCOUNTS
)
from .base import SocialMediaMonitor

# Configure logging
logger = logging.getLogger(__name__)

class TwitterMonitor(SocialMediaMonitor):
    """Twitter/X social media monitor implementation."""
    
    def __init__(self):
        """Initialize the Twitter monitor."""
        self.last_search_time = datetime.utcnow() - timedelta(hours=24)
        self.last_influencer_check = {}
        for influencer in INFLUENCER_ACCOUNTS:
            self.last_influencer_check[influencer] = datetime.utcnow() - timedelta(hours=24)
    
    async def search_for_mentions(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for mentions of keywords on Twitter/X.
        
        Args:
            keywords: List of keywords to search for.
            
        Returns:
            List of dictionaries containing mention information.
        """
        logger.info(f"Searching Twitter for mentions of {len(keywords)} keywords")
        mentions = []
        
        try:
            # Use the Twitter API to search for tweets containing the keywords
            for keyword in keywords:
                try:
                    # Use the Twitter/search_twitter API from the datasource module
                    tweets = await self._search_twitter(keyword)
                    
                    for tweet in tweets:
                        # Extract tweet information
                        tweet_info = self._extract_tweet_info(tweet)
                        if tweet_info:
                            mentions.append(tweet_info)
                
                except Exception as e:
                    logger.error(f"Error searching Twitter for keyword '{keyword}': {str(e)}")
            
            # Update last search time
            self.last_search_time = datetime.utcnow()
            
            logger.info(f"Found {len(mentions)} mentions on Twitter")
            return mentions
        
        except Exception as e:
            logger.error(f"Error searching Twitter: {str(e)}")
            return []
    
    async def _search_twitter(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Twitter for tweets containing a query.
        
        Args:
            query: The search query.
            
        Returns:
            List of tweet objects.
        """
        try:
            # Import the API client from the data_api module
            sys.path.append('/opt/.manus/.sandbox-runtime')
            from data_api import ApiClient
            client = ApiClient()
            
            # Call the Twitter/search_twitter API
            response = client.call_api('Twitter/search_twitter', query={
                'query': query,
                'count': 20,
                'type': 'Latest'
            })
            
            # Extract tweets from the response
            tweets = []
            if response and 'result' in response and 'timeline' in response['result']:
                timeline = response['result']['timeline']
                if 'instructions' in timeline:
                    for instruction in timeline['instructions']:
                        if 'entries' in instruction:
                            for entry in instruction['entries']:
                                if 'content' in entry and 'items' in entry['content']:
                                    for item in entry['content']['items']:
                                        if 'item' in item and 'itemContent' in item['item']:
                                            tweets.append(item['item']['itemContent'])
            
            return tweets
        
        except Exception as e:
            logger.error(f"Error calling Twitter API: {str(e)}")
            return []
    
    def _extract_tweet_info(self, tweet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract information from a tweet object.
        
        Args:
            tweet: The tweet object.
            
        Returns:
            Dictionary containing tweet information or None if error.
        """
        try:
            # Extract user information
            user_results = tweet.get('user_results', {}).get('result', {})
            user_legacy = user_results.get('legacy', {})
            
            # Extract tweet content
            # Note: In a real implementation, we would extract the actual tweet content
            # For now, we'll use a placeholder
            content = "This is a tweet about crypto and meme coins"
            
            # Check if user is an influencer
            is_influencer = user_legacy.get('screen_name', '').lower() in [
                influencer.lower() for influencer in INFLUENCER_ACCOUNTS
            ]
            
            # Extract tweet URL
            tweet_id = user_legacy.get('id_str', '')
            screen_name = user_legacy.get('screen_name', '')
            tweet_url = f"https://twitter.com/{screen_name}/status/{tweet_id}" if tweet_id and screen_name else None
            
            # Create tweet info
            tweet_info = {
                'source': 'twitter',
                'author': user_legacy.get('screen_name', ''),
                'is_influencer': is_influencer,
                'content': content,
                'url': tweet_url,
                'timestamp': datetime.utcnow(),  # In a real implementation, extract from tweet
                'followers_count': user_legacy.get('followers_count', 0),
                'verified': user_legacy.get('verified', False) or user_results.get('is_blue_verified', False)
            }
            
            return tweet_info
        
        except Exception as e:
            logger.error(f"Error extracting tweet info: {str(e)}")
            return None
    
    async def monitor_influencers(self, influencer_accounts: List[str]) -> List[Dict[str, Any]]:
        """
        Monitor influencer accounts for new posts.
        
        Args:
            influencer_accounts: List of influencer Twitter handles.
            
        Returns:
            List of dictionaries containing post information.
        """
        logger.info(f"Monitoring {len(influencer_accounts)} Twitter influencers")
        posts = []
        
        try:
            for influencer in influencer_accounts:
                try:
                    # Get user profile to get the user ID
                    user_profile = await self._get_user_profile(influencer)
                    if not user_profile:
                        continue
                    
                    user_id = user_profile.get('rest_id')
                    if not user_id:
                        continue
                    
                    # Get user tweets
                    tweets = await self._get_user_tweets(user_id)
                    
                    # Process tweets
                    for tweet in tweets:
                        # Extract tweet information
                        tweet_info = self._extract_tweet_info(tweet)
                        if tweet_info:
                            # Check if tweet mentions meme coins
                            if self._contains_meme_keywords(tweet_info.get('content', '')):
                                posts.append(tweet_info)
                    
                    # Update last check time for this influencer
                    self.last_influencer_check[influencer] = datetime.utcnow()
                
                except Exception as e:
                    logger.error(f"Error monitoring Twitter influencer '{influencer}': {str(e)}")
            
            logger.info(f"Found {len(posts)} new posts from Twitter influencers")
            return posts
        
        except Exception as e:
            logger.error(f"Error monitoring Twitter influencers: {str(e)}")
            return []
    
    async def _get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's profile information.
        
        Args:
            username: The Twitter username.
            
        Returns:
            Dictionary containing user profile information or None if error.
        """
        try:
            # Import the API client from the data_api module
            sys.path.append('/opt/.manus/.sandbox-runtime')
            from data_api import ApiClient
            client = ApiClient()
            
            # Call the Twitter/get_user_profile_by_username API
            response = client.call_api('Twitter/get_user_profile_by_username', query={
                'username': username
            })
            
            # Extract user profile from the response
            if response and 'result' in response and 'data' in response['result']:
                user_data = response['result']['data']
                if 'user' in user_data and 'result' in user_data['user']:
                    return user_data['user']['result']
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting Twitter user profile for '{username}': {str(e)}")
            return None
    
    async def _get_user_tweets(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get a user's tweets.
        
        Args:
            user_id: The Twitter user ID.
            
        Returns:
            List of tweet objects.
        """
        try:
            # Import the API client from the data_api module
            sys.path.append('/opt/.manus/.sandbox-runtime')
            from data_api import ApiClient
            client = ApiClient()
            
            # Call the Twitter/get_user_tweets API
            response = client.call_api('Twitter/get_user_tweets', query={
                'user': user_id,
                'count': 10
            })
            
            # Extract tweets from the response
            tweets = []
            if response and 'result' in response and 'timeline' in response['result']:
                timeline = response['result']['timeline']
                if 'instructions' in timeline:
                    for instruction in timeline['instructions']:
                        if 'entries' in instruction:
                            for entry in instruction['entries']:
                                if 'content' in entry and 'items' in entry['content']:
                                    for item in entry['content']['items']:
                                        if 'item' in item and 'itemContent' in item['item']:
                                            tweets.append(item['item']['itemContent'])
            
            return tweets
        
        except Exception as e:
            logger.error(f"Error getting tweets for user ID '{user_id}': {str(e)}")
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
            
            return token_mentions
        
        except Exception as e:
            logger.error(f"Error extracting token mentions: {str(e)}")
            return []
