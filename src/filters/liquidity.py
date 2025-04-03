"""
Liquidity threshold filter for the Meme Coin Bot.
"""
import logging
import os
from typing import Dict, Any

from src.filters.base import BaseFilter

# Setup logging
logger = logging.getLogger(__name__)

# Get minimum liquidity threshold from environment variable
MINIMUM_LIQUIDITY_USD = float(os.getenv("MINIMUM_LIQUIDITY_USD", "10000"))

class LiquidityFilter(BaseFilter):
    """Filter tokens based on liquidity threshold."""
    
    def __init__(self, min_liquidity_usd: float = MINIMUM_LIQUIDITY_USD):
        """
        Initialize the liquidity filter.
        
        Args:
            min_liquidity_usd: Minimum liquidity in USD.
        """
        self.min_liquidity_usd = min_liquidity_usd
        self.last_rejection_reason = ""
    
    def filter_name(self) -> str:
        """
        Get the name of the filter.
        
        Returns:
            Filter name.
        """
        return "Liquidity Filter"
    
    async def apply(self, token: Dict[str, Any]) -> bool:
        """
        Apply the filter to a token.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            True if the token passes the filter, False otherwise.
        """
        liquidity = token.get("liquidity_usd", 0.0)
        
        if liquidity < self.min_liquidity_usd:
            self.last_rejection_reason = f"Insufficient liquidity: ${liquidity:.2f} < ${self.min_liquidity_usd:.2f}"
            return False
        
        return True
    
    def get_rejection_reason(self) -> str:
        """
        Get the reason why the token was rejected by the filter.
        
        Returns:
            Rejection reason.
        """
        return self.last_rejection_reason
