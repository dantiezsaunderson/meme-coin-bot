"""
Safety filter for the Meme Coin Bot.
"""
import logging
import os
from typing import Dict, Any

from src.filters.base import BaseFilter

# Setup logging
logger = logging.getLogger(__name__)

class SafetyFilter(BaseFilter):
    """Filter tokens based on contract safety."""
    
    def __init__(self):
        """Initialize the safety filter."""
        self.last_rejection_reason = ""
    
    def filter_name(self) -> str:
        """
        Get the name of the filter.
        
        Returns:
            Filter name.
        """
        return "Safety Filter"
    
    async def apply(self, token: Dict[str, Any]) -> bool:
        """
        Apply the filter to a token.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            True if the token passes the filter, False otherwise.
        """
        safety_info = token.get("safety", {})
        
        # Check if token is marked as unsafe
        if not safety_info.get("is_safe", True):
            self.last_rejection_reason = f"Token failed safety check: {', '.join(safety_info.get('warnings', ['Unknown reason']))}"
            return False
        
        # Check risk level
        risk_level = safety_info.get("risk_level", "unknown")
        if risk_level == "high":
            self.last_rejection_reason = f"Token has high risk level: {', '.join(safety_info.get('warnings', ['Unknown reason']))}"
            return False
        
        return True
    
    def get_rejection_reason(self) -> str:
        """
        Get the reason why the token was rejected by the filter.
        
        Returns:
            Rejection reason.
        """
        return self.last_rejection_reason
