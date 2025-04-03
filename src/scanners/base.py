"""
Base scanner interface for blockchain scanners.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# Setup logging
logger = logging.getLogger(__name__)

class BaseScanner(ABC):
    """Abstract base class for blockchain scanners."""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the scanner.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan for new tokens on the blockchain.
        
        Returns:
            List of new token information dictionaries.
        """
        pass
    
    @abstractmethod
    async def get_token_details(self, token_address: str) -> Dict[str, Any]:
        """
        Get detailed information about a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary with token details.
        """
        pass
    
    @abstractmethod
    async def get_token_price(self, token_address: str) -> float:
        """
        Get the current price of a token in USD.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Price in USD.
        """
        pass
    
    @abstractmethod
    async def get_token_volume(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the trading volume for a token over a specified time period.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Volume in USD.
        """
        pass
    
    @abstractmethod
    async def get_token_liquidity(self, token_address: str) -> float:
        """
        Get the current liquidity for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Liquidity in USD.
        """
        pass
    
    @abstractmethod
    async def get_token_holders(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Number of holders.
        """
        pass
    
    @abstractmethod
    async def get_buy_sell_ratio(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the buy/sell ratio for a token over a specified time period.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio (> 1.0 means more buys than sells).
        """
        pass
    
    @abstractmethod
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check if a token contract is safe (not a honeypot, etc.).
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary with safety information.
        """
        pass
    
    @abstractmethod
    async def is_meme_token(self, token_address: str) -> bool:
        """
        Check if a token is likely a meme token based on name, symbol, etc.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            True if the token is likely a meme token, False otherwise.
        """
        pass
