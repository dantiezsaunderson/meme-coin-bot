"""
Filter service coordinator for the Meme Coin Bot.
Manages all token filters and coordinates filtering.
"""
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional

from src.filters.base import BaseFilter
from src.filters.liquidity import LiquidityFilter
from src.filters.safety import SafetyFilter

# Setup logging
logger = logging.getLogger(__name__)

class FilterService:
    """Service to coordinate token filters."""
    
    def __init__(self):
        """Initialize the filter service."""
        self.filters = []
        self.initialize_filters()
    
    def initialize_filters(self):
        """Initialize all filters."""
        # Add liquidity filter
        self.filters.append(LiquidityFilter())
        
        # Add safety filter
        self.filters.append(SafetyFilter())
        
        logger.info(f"Filter service initialized with {len(self.filters)} filters")
    
    async def apply_filters(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply all filters to a list of tokens.
        
        Args:
            tokens: List of token information dictionaries.
            
        Returns:
            List of tokens that passed all filters.
        """
        if not tokens:
            return []
        
        filtered_tokens = []
        for token in tokens:
            if await self.apply_filters_to_token(token):
                filtered_tokens.append(token)
        
        logger.info(f"{len(filtered_tokens)}/{len(tokens)} tokens passed all filters")
        return filtered_tokens
    
    async def apply_filters_to_token(self, token: Dict[str, Any]) -> bool:
        """
        Apply all filters to a single token.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            True if the token passed all filters, False otherwise.
        """
        for filter_instance in self.filters:
            try:
                if not await filter_instance.apply(token):
                    logger.info(f"Token {token.get('symbol')} ({token.get('address')}) rejected by {filter_instance.filter_name()}: {filter_instance.get_rejection_reason()}")
                    return False
            except Exception as e:
                logger.error(f"Error applying {filter_instance.filter_name()} to token {token.get('address')}: {str(e)}")
                return False
        
        return True
    
    async def apply_filters_in_parallel(self, tokens: List[Dict[str, Any]], max_concurrency: int = 10) -> List[Dict[str, Any]]:
        """
        Apply all filters to a list of tokens in parallel.
        
        Args:
            tokens: List of token information dictionaries.
            max_concurrency: Maximum number of tokens to process in parallel.
            
        Returns:
            List of tokens that passed all filters.
        """
        if not tokens:
            return []
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def filter_with_limit(token):
            async with semaphore:
                if await self.apply_filters_to_token(token):
                    return token
                return None
        
        # Create tasks for all tokens
        tasks = [filter_with_limit(token) for token in tokens]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None values and exceptions
        filtered_tokens = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error filtering token: {str(result)}")
            elif result is not None:
                filtered_tokens.append(result)
        
        logger.info(f"{len(filtered_tokens)}/{len(tokens)} tokens passed all filters")
        return filtered_tokens

# Singleton instance
filter_service = FilterService()
