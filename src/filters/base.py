"""
Base filter interface for the Meme Coin Bot.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

# Setup logging
logger = logging.getLogger(__name__)

class BaseFilter(ABC):
    """Abstract base class for token filters."""
    
    @abstractmethod
    def filter_name(self) -> str:
        """
        Get the name of the filter.
        
        Returns:
            Filter name.
        """
        pass
    
    @abstractmethod
    async def apply(self, token: Dict[str, Any]) -> bool:
        """
        Apply the filter to a token.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            True if the token passes the filter, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_rejection_reason(self) -> str:
        """
        Get the reason why the token was rejected by the filter.
        
        Returns:
            Rejection reason.
        """
        pass
