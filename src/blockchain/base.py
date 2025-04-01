"""
Base blockchain scanner interface for the Meme Coin Signal Bot.

This module defines the abstract base class for blockchain scanners.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class BlockchainScanner(ABC):
    """Abstract base class for blockchain scanners."""
    
    @abstractmethod
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan the blockchain for new token launches.
        
        Returns:
            List of dictionaries containing token information.
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
    async def get_buy_sell_ratio(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the buy/sell ratio for a token over a specified time period.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio (buys/sells).
        """
        pass
    
    @abstractmethod
    async def get_holder_count(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Number of holders.
        """
        pass
    
    @abstractmethod
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check the safety of a token's smart contract.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary containing safety information.
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
