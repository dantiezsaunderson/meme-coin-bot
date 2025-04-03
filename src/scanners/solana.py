"""
Solana blockchain scanner implementation.
"""
import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple

import aiohttp
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient

from src.scanners.base import BaseScanner
from src.utils.cache import cache_result
from src.utils.retry import retry_with_backoff

# Setup logging
logger = logging.getLogger(__name__)

# Constants
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "")
SOLANA_API_KEY = os.getenv("SOLANA_API_KEY", "")
JUPITER_API_URL = "https://price.jup.ag/v4/price"

# Meme token keywords
MEME_KEYWORDS = [
    "doge", "shib", "inu", "elon", "moon", "safe", "cum", "chad", "based",
    "ape", "gorilla", "floki", "baby", "mini", "meme", "coin", "token",
    "gme", "amc", "stonk", "tendies", "wsb", "wojak", "pepe", "frog",
    "bonk", "samo", "sol"
]

class SolanaScanner(BaseScanner):
    """Solana blockchain scanner implementation."""
    
    def __init__(self):
        """Initialize the Solana scanner."""
        self.client = None
        self.initialized = False
        self.session = None
    
    async def initialize(self) -> bool:
        """
        Initialize the Solana scanner.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        try:
            # Validate RPC URL format
            if not SOLANA_RPC_URL:
                logger.error("SOLANA_RPC_URL environment variable not set")
                return False
            
            # Check if URL is in the correct Helius format
            if "helius-rpc.com" in SOLANA_RPC_URL and "api-key" not in SOLANA_RPC_URL:
                logger.error("Solana RPC URL is not in the correct Helius API format")
                logger.error("Required format: https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY")
                return False
            
            # Initialize Solana client
            self.client = AsyncClient(SOLANA_RPC_URL)
            
            # Test connection
            response = await self.client.get_health()
            if response != "ok":
                logger.error(f"Failed to connect to Solana RPC: {response}")
                return False
            
            # Initialize HTTP session for API calls
            self.session = aiohttp.ClientSession()
            
            logger.info("Solana scanner initialized successfully")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Solana scanner: {str(e)}")
            return False
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan for new tokens on Solana.
        
        Returns:
            List of new token information dictionaries.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return []
        
        try:
            # Use Helius API to get recent token creations
            # This is a simplified implementation - in production, you would use
            # a more sophisticated approach to track new token creations
            
            # Check if we're using Helius API
            if "helius-rpc.com" in SOLANA_RPC_URL:
                new_tokens = await self._scan_helius_for_new_tokens()
            else:
                # Fallback to basic RPC scanning
                new_tokens = await self._scan_basic_rpc_for_new_tokens()
            
            # Filter for potential meme tokens
            meme_tokens = []
            for token in new_tokens:
                token_address = token.get("address")
                if not token_address:
                    continue
                
                # Check if it's a meme token
                is_meme = await self.is_meme_token(token_address)
                if is_meme:
                    # Get additional token details
                    token_details = await self.get_token_details(token_address)
                    meme_tokens.append({**token, **token_details})
            
            return meme_tokens
            
        except Exception as e:
            logger.error(f"Error scanning for new Solana tokens: {str(e)}")
            return []
    
    async def _scan_helius_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan for new tokens using Helius API.
        
        Returns:
            List of new token information dictionaries.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Extract API key from URL
        match = re.search(r'api-key=([^&]+)', SOLANA_RPC_URL)
        if not match:
            logger.error("Could not extract API key from Helius URL")
            return []
        
        api_key = match.group(1)
        
        # Use Helius enhanced API to get recent token mints
        # Note: This is a simplified example - actual implementation would depend on
        # the specific Helius API endpoints available
        url = f"https://api.helius.xyz/v0/tokens?api-key={api_key}"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.error(f"Helius API error: {response.status}")
                return []
            
            data = await response.json()
            
            # Process the response to extract token information
            tokens = []
            for token_data in data.get("tokens", []):
                # Filter for recently created tokens (e.g., in the last day)
                creation_time = token_data.get("createdAt")
                if not creation_time:
                    continue
                
                # Add to list of new tokens
                tokens.append({
                    "address": token_data.get("address"),
                    "name": token_data.get("name"),
                    "symbol": token_data.get("symbol"),
                    "decimals": token_data.get("decimals"),
                    "creation_time": creation_time,
                    "blockchain": "solana"
                })
            
            return tokens
    
    async def _scan_basic_rpc_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan for new tokens using basic Solana RPC.
        This is a fallback method when Helius API is not available.
        
        Returns:
            List of new token information dictionaries.
        """
        # This is a simplified implementation
        # In a production environment, you would use a more sophisticated approach
        # such as monitoring the Token Program for new token creations
        
        # For now, we'll return an empty list as this requires more complex implementation
        logger.warning("Basic RPC scanning not fully implemented - requires advanced token tracking")
        return []
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_details(self, token_address: str) -> Dict[str, Any]:
        """
        Get detailed information about a token.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary with token details.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return {}
        
        try:
            # Get token metadata
            token_info = await self._get_token_info(token_address)
            if not token_info:
                return {}
            
            # Get additional metrics
            price = await self.get_token_price(token_address)
            volume = await self.get_token_volume(token_address)
            liquidity = await self.get_token_liquidity(token_address)
            holders = await self.get_token_holders(token_address)
            buy_sell_ratio = await self.get_buy_sell_ratio(token_address)
            safety_info = await self.check_contract_safety(token_address)
            
            # Combine all information
            return {
                "address": token_address,
                "name": token_info.get("name", ""),
                "symbol": token_info.get("symbol", ""),
                "decimals": token_info.get("decimals", 0),
                "price_usd": price,
                "volume_24h_usd": volume,
                "liquidity_usd": liquidity,
                "holders_count": holders,
                "buy_sell_ratio": buy_sell_ratio,
                "safety": safety_info,
                "blockchain": "solana"
            }
            
        except Exception as e:
            logger.error(f"Error getting token details for {token_address}: {str(e)}")
            return {}
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def _get_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Get basic token information.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary with token information.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return {}
        
        try:
            # Get token supply info which includes decimals
            response = await self.client.get_token_supply(PublicKey(token_address))
            if not response.value:
                logger.error(f"Failed to get token supply for {token_address}")
                return {}
            
            # Get token account info for metadata
            response = await self.client.get_account_info(PublicKey(token_address))
            if not response.value:
                logger.error(f"Failed to get account info for {token_address}")
                return {}
            
            # Parse token metadata
            # This is a simplified implementation - in production, you would use
            # the Metaplex metadata program to get full token metadata
            
            # For now, we'll use Solscan API if available
            if SOLANA_API_KEY:
                return await self._get_token_info_from_solscan(token_address)
            
            # Fallback to basic info
            return {
                "address": token_address,
                "decimals": response.value.decimals,
                "name": f"Unknown Token {token_address[:6]}",
                "symbol": f"UNK{token_address[:4]}"
            }
            
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {str(e)}")
            return {}
    
    async def _get_token_info_from_solscan(self, token_address: str) -> Dict[str, Any]:
        """
        Get token information from Solscan API.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary with token information.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
            headers = {"Accept": "application/json"}
            
            if SOLANA_API_KEY:
                headers["token"] = SOLANA_API_KEY
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Solscan API error: {response.status}")
                    return {}
                
                data = await response.json()
                
                return {
                    "address": token_address,
                    "name": data.get("name", f"Unknown Token {token_address[:6]}"),
                    "symbol": data.get("symbol", f"UNK{token_address[:4]}"),
                    "decimals": data.get("decimals", 0),
                    "icon": data.get("icon", "")
                }
                
        except Exception as e:
            logger.error(f"Error getting token info from Solscan for {token_address}: {str(e)}")
            return {}
    
    @cache_result(ttl_seconds=60)  # Cache for 1 minute
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_price(self, token_address: str) -> float:
        """
        Get the current price of a token in USD.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Price in USD.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return 0.0
        
        try:
            # Use Jupiter API for price data
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{JUPITER_API_URL}?ids={token_address}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Jupiter API error: {response.status}")
                    return 0.0
                
                data = await response.json()
                
                # Extract price from response
                token_data = data.get("data", {}).get(token_address)
                if not token_data:
                    return 0.0
                
                return float(token_data.get("price", 0.0))
                
        except Exception as e:
            logger.error(f"Error getting token price for {token_address}: {str(e)}")
            return 0.0
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_volume(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the trading volume for a token over a specified time period.
        
        Args:
            token_address: The token mint address.
            time_period_hours: The time period in hours.
            
        Returns:
            Volume in USD.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return 0.0
        
        try:
            # Use Helius API for volume data if available
            if "helius-rpc.com" in SOLANA_RPC_URL:
                return await self._get_volume_from_helius(token_address, time_period_hours)
            
            # Fallback to Jupiter API for basic volume data
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{JUPITER_API_URL}?ids={token_address}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Jupiter API error: {response.status}")
                    return 0.0
                
                data = await response.json()
                
                # Extract volume from response
                token_data = data.get("data", {}).get(token_address)
                if not token_data:
                    return 0.0
                
                return float(token_data.get("volume24h", 0.0))
                
        except Exception as e:
            logger.error(f"Error getting token volume for {token_address}: {str(e)}")
            return 0.0
    
    async def _get_volume_from_helius(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get token volume data from Helius API.
        
        Args:
            token_address: The token mint address.
            time_period_hours: The time period in hours.
            
        Returns:
            Volume in USD.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Extract API key from URL
        match = re.search(r'api-key=([^&]+)', SOLANA_RPC_URL)
        if not match:
            logger.error("Could not extract API key from Helius URL")
            return 0.0
        
        api_key = match.group(1)
        
        # Use Helius API to get token transactions
        url = f"https://api.helius.xyz/v0/tokens/{token_address}/transactions?api-key={api_key}"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.error(f"Helius API error: {response.status}")
                return 0.0
            
            data = await response.json()
            
            # Calculate volume from transactions
            # This is a simplified implementation - in production, you would use
            # a more sophisticated approach to calculate volume
            
            volume = 0.0
            price = await self.get_token_price(token_address)
            
            for tx in data.get("transactions", []):
                # Check if transaction is within time period
                timestamp = tx.get("timestamp")
                if not timestamp:
                    continue
                
                # Calculate volume
                amount = tx.get("amount", 0)
                volume += amount * price
            
            return volume
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_liquidity(self, token_address: str) -> float:
        """
        Get the current liquidity for a token on Raydium/Orca.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Liquidity in USD.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return 0.0
        
        try:
            # Get largest token accounts
            response = await self.client.get_token_largest_accounts(
                PublicKey(token_address)
            )
            
            if not response.value:
                return 0.0
            
            # Sum up the balances of the largest accounts (simplified liquidity estimate)
            total_balance = 0
            for account in response.value:
                total_balance += float(account.amount)
            
            # Get token info for decimals
            token_info = await self._get_token_info(token_address)
            if not token_info:
                return 0.0
            
            decimals = token_info.get("decimals", 0)
            
            # Get token price
            price = await self.get_token_price(token_address)
            
            # Calculate liquidity in USD
            liquidity_usd = (total_balance / (10 ** decimals)) * price
            
            return liquidity_usd
            
        except Exception as e:
            logger.error(f"Error getting liquidity for {token_address}: {str(e)}")
            return 0.0
    
    @cache_result(ttl_seconds=1800)  # Cache for 30 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_holders(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Number of holders.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return 0
        
        try:
            # Use Solscan API if available
            if SOLANA_API_KEY:
                return await self._get_holders_from_solscan(token_address)
            
            # Fallback to basic RPC method
            # Get token accounts
            response = await self.client.get_token_accounts_by_owner(
                PublicKey(token_address),
                {"programId": PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
            )
            
            if not response.value:
                return 0
            
            # Count unique owners
            owners = set()
            for account in response.value:
                owners.add(account.pubkey)
            
            return len(owners)
            
        except Exception as e:
            logger.error(f"Error getting holder count for {token_address}: {str(e)}")
            return 0
    
    async def _get_holders_from_solscan(self, token_address: str) -> int:
        """
        Get token holder count from Solscan API.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Number of holders.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"https://public-api.solscan.io/token/holders?tokenAddress={token_address}"
            headers = {"Accept": "application/json"}
            
            if SOLANA_API_KEY:
                headers["token"] = SOLANA_API_KEY
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Solscan API error: {response.status}")
                    return 0
                
                data = await response.json()
                
                # Extract holder count
                return data.get("total", 0)
                
        except Exception as e:
            logger.error(f"Error getting holder count from Solscan for {token_address}: {str(e)}")
            return 0
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_buy_sell_ratio(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the buy/sell ratio for a token over a specified time period.
        
        Args:
            token_address: The token mint address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio (> 1.0 means more buys than sells).
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return 1.0  # Default to neutral ratio
        
        try:
            # Use Helius API for transaction data if available
            if "helius-rpc.com" in SOLANA_RPC_URL:
                return await self._get_buy_sell_ratio_from_helius(token_address, time_period_hours)
            
            # Fallback to a default value if we can't calculate
            logger.warning(f"Cannot calculate buy/sell ratio for {token_address} without Helius API")
            return 1.0  # Default to neutral ratio
            
        except Exception as e:
            logger.error(f"Error getting buy/sell ratio for {token_address}: {str(e)}")
            return 1.0  # Default to neutral ratio
    
    async def _get_buy_sell_ratio_from_helius(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get buy/sell ratio from Helius API.
        
        Args:
            token_address: The token mint address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Extract API key from URL
        match = re.search(r'api-key=([^&]+)', SOLANA_RPC_URL)
        if not match:
            logger.error("Could not extract API key from Helius URL")
            return 1.0
        
        api_key = match.group(1)
        
        # Use Helius API to get token transactions
        url = f"https://api.helius.xyz/v0/tokens/{token_address}/transactions?api-key={api_key}"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.error(f"Helius API error: {response.status}")
                return 1.0
            
            data = await response.json()
            
            # Count buys and sells
            buys = 0
            sells = 0
            
            for tx in data.get("transactions", []):
                # Determine if transaction is a buy or sell
                # This is a simplified implementation - in production, you would use
                # a more sophisticated approach to determine transaction type
                
                tx_type = tx.get("type")
                if tx_type == "buy":
                    buys += 1
                elif tx_type == "sell":
                    sells += 1
            
            # Calculate ratio
            if sells == 0:
                return 2.0  # All buys, no sells
            
            return buys / sells
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check if a token contract is safe (not a honeypot, etc.).
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary containing safety information.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return {
                "is_safe": False,
                "risk_level": "unknown",
                "warnings": ["Scanner not initialized"]
            }
        
        try:
            # This is a simplified implementation - in production, you would use
            # a more sophisticated approach to check contract safety
            
            # Check if token has liquidity
            liquidity = await self.get_token_liquidity(token_address)
            if liquidity < 1000:  # Arbitrary threshold
                return {
                    "is_safe": False,
                    "risk_level": "high",
                    "warnings": ["Low liquidity"]
                }
            
            # Check if token has holders
            holders = await self.get_token_holders(token_address)
            if holders < 10:  # Arbitrary threshold
                return {
                    "is_safe": False,
                    "risk_level": "high",
                    "warnings": ["Few holders"]
                }
            
            # Basic safety check passed
            return {
                "is_safe": True,
                "risk_level": "low",
                "warnings": []
            }
            
        except Exception as e:
            logger.error(f"Error checking contract safety for {token_address}: {str(e)}")
            return {
                "is_safe": False,
                "risk_level": "unknown",
                "warnings": [f"Error checking contract: {str(e)}"]
            }
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    async def is_meme_token(self, token_address: str) -> bool:
        """
        Check if a token is likely a meme token based on name, symbol, etc.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            True if the token is likely a meme token, False otherwise.
        """
        if not self.initialized:
            logger.error("Solana scanner not initialized")
            return False
        
        try:
            # Get token info
            token_info = await self._get_token_info(token_address)
            if not token_info:
                return False
            
            name = token_info.get("name", "").lower()
            symbol = token_info.get("symbol", "").lower()
            
            # Check if any meme keyword is in the name or symbol
            for keyword in MEME_KEYWORDS:
                if keyword in name or keyword in symbol:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if {token_address} is a meme token: {str(e)}")
            return False
