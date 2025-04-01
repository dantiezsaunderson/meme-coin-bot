"""
Base social media monitor interface for the Meme Coin Signal Bot.

This module defines the abstract base class for social media monitors.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class SocialMediaMonitor(ABC):
    """Abstract base class for social media monitors."""
    
    @abstractmethod
    async def search_for_mentions(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for mentions of keywords on social media.
        
        Args:
            keywords: List of keywords to search for.
            
        Returns:
            List of dictionaries containing mention information.
        """
        pass
    
    @abstractmethod
    async def monitor_influencers(self, influencer_accounts: List[str]) -> List[Dict[str, Any]]:
        """
        Monitor influencer accounts for new posts.
        
        Args:
            influencer_accounts: List of influencer account identifiers.
            
        Returns:
            List of dictionaries containing post information.
        """
        pass
    
    @abstractmethod
    async def analyze_sentiment(self, content: str) -> float:
        """
        Analyze the sentiment of a social media post.
        
        Args:
            content: The text content of the post.
            
        Returns:
            Sentiment score between -1.0 (negative) and 1.0 (positive).
        """
        pass
    
    @abstractmethod
    async def extract_token_mentions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract token mentions from a social media post.
        
        Args:
            content: The text content of the post.
            
        Returns:
            List of dictionaries containing token information.
        """
        pass
