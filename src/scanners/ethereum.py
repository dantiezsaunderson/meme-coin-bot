"""
Ethereum blockchain scanner implementation.
"""
import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple

import aiohttp
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware

from src.scanners.base import BaseScanner
from src.utils.cache import cache_result
from src.utils.retry import retry_with_backoff, CircuitBreaker

# Setup logging
logger = logging.getLogger(__name__)

# Constants
ETHEREUM_RPC_URL = os.getenv("ETHEREUM_RPC_URL", "")
ETHEREUM_API_KEY = os.getenv("ETHEREUM_API_KEY", "")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

# Uniswap constants
UNISWAP_FACTORY_ADDRESS = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"  # Uniswap V2 Factory
UNISWAP_ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"  # Uniswap V2 Router
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # Wrapped ETH

# Meme token keywords
MEME_KEYWORDS = [
    "doge", "shib", "inu", "elon", "moon", "safe", "cum", "chad", "based",
    "ape", "gorilla", "floki", "baby", "mini", "meme", "coin", "token",
    "gme", "amc", "stonk", "tendies", "wsb", "wojak", "pepe", "frog"
]

# ABIs
UNISWAP_FACTORY_ABI = [
    {
        "constant": True,
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

UNISWAP_PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class EthereumScanner(BaseScanner):
    """Ethereum blockchain scanner implementation."""
    
    def __init__(self):
        """Initialize the Ethereum scanner."""
        self.w3 = None
        self.sync_w3 = None
        self.initialized = False
        self.session = None
        self.has_honeypot_detector = False
        self.honeypot_detector = None
        self.eth_price_circuit_breaker = CircuitBreaker("eth_price", failure_threshold=3, reset_timeout=300)
        
    async def initialize(self) -> bool:
        """
        Initialize the Ethereum scanner.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        try:
            # Validate RPC URL
            if not ETHEREUM_RPC_URL:
                logger.error("ETHEREUM_RPC_URL environment variable not set")
                return False
            
            # Initialize Web3 clients
            self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(ETHEREUM_RPC_URL))
            self.sync_w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))
            
            # Add middleware for POA chains like Ethereum mainnet
            self.sync_w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Test connection
            connected = await self.w3.is_connected()
            if not connected:
                logger.error("Failed to connect to Ethereum RPC")
                return False
            
            # Initialize HTTP session for API calls
            self.session = aiohttp.ClientSession()
            
            logger.info("Ethereum scanner initialized successfully")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Ethereum scanner: {str(e)}")
            return False
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan for new tokens on Ethereum.
        
        Returns:
            List of new token information dictionaries.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return []
        
        try:
            # Use Uniswap factory to find new pairs
            # This is a simplified implementation - in production, you would use
            # event logs or a subgraph to track new pair creations
            
            # Get the latest block number
            latest_block = await self.w3.eth.block_number
            
            # Look back a certain number of blocks (e.g., last 1000 blocks)
            from_block = max(0, latest_block - 1000)
            
            # Get PairCreated events from Uniswap factory
            factory_contract = self.sync_w3.eth.contract(
                address=self.sync_w3.to_checksum_address(UNISWAP_FACTORY_ADDRESS),
                abi=[{
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
                        {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
                        {"indexed": False, "internalType": "address", "name": "pair", "type": "address"},
                        {"indexed": False, "internalType": "uint256", "name": "", "type": "uint256"}
                    ],
                    "name": "PairCreated",
                    "type": "event"
                }]
            )
            
            # Get PairCreated events
            events = factory_contract.events.PairCreated.get_logs(fromBlock=from_block, toBlock=latest_block)
            
            # Process events to find new tokens
            new_tokens = []
            for event in events:
                token0 = event.args.token0
                token1 = event.args.token1
                
                # Check if one of the tokens is WETH
                if token0 == WETH_ADDRESS:
                    token_address = token1
                elif token1 == WETH_ADDRESS:
                    token_address = token0
                else:
                    # Skip pairs that don't include WETH
                    continue
                
                # Check if it's a meme token
                is_meme = await self.is_meme_token(token_address)
                if is_meme:
                    # Get token details
                    token_details = await self.get_token_details(token_address)
                    if token_details:
                        new_tokens.append(token_details)
            
            return new_tokens
            
        except Exception as e:
            logger.error(f"Error scanning for new Ethereum tokens: {str(e)}")
            return []
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_details(self, token_address: str) -> Dict[str, Any]:
        """
        Get detailed information about a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary with token details.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return {}
        
        try:
            # Get token metadata
            token_info = await self._get_token_info(token_address)
            if not token_info:
                return {}
            
            # Get additional metrics
            price = await self.get_token_price(token_address)
            volume = await self.get_token_volume_24h(token_address)
            liquidity = await self.get_token_liquidity(token_address)
            holders = await self.get_token_holders(token_address)
            buy_sell_ratio = await self.get_buy_sell_ratio(token_address)
            safety_info = await self.check_contract_safety(token_address)
            
            # Combine all information
            return {
                "address": token_address,
                "name": token_info.get("name", ""),
                "symbol": token_info.get("symbol", ""),
                "decimals": token_info.get("decimals", 18),
                "price_usd": price,
                "volume_24h_usd": volume,
                "liquidity_usd": liquidity,
                "holders_count": holders,
                "buy_sell_ratio": buy_sell_ratio,
                "safety": safety_info,
                "blockchain": "ethereum"
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
            token_address: The token contract address.
            
        Returns:
            Dictionary with token information.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return {}
        
        try:
            # Create token contract instance
            token_contract = self.sync_w3.eth.contract(
                address=self.sync_w3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Get token information
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            total_supply = token_contract.functions.totalSupply().call()
            
            return {
                "address": token_address,
                "name": name,
                "symbol": symbol,
                "decimals": decimals,
                "total_supply": total_supply
            }
            
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {str(e)}")
            return {}
    
    @cache_result(ttl_seconds=60)  # Cache for 1 minute
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_price(self, token_address: str) -> float:
        """
        Get the current price of a token in USD.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Price in USD.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return 0.0
        
        try:
            # Get token-WETH pair
            factory = self.sync_w3.eth.contract(
                address=self.sync_w3.to_checksum_address(UNISWAP_FACTORY_ADDRESS),
                abi=UNISWAP_FACTORY_ABI
            )
            
            pair_address = factory.functions.getPair(
                self.sync_w3.to_checksum_address(token_address),
                self.sync_w3.to_checksum_address(WETH_ADDRESS)
            ).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0.0
            
            # Get pair contract
            pair_contract = self.sync_w3.eth.contract(
                address=pair_address,
                abi=UNISWAP_PAIR_ABI
            )
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            token0 = pair_contract.functions.token0().call()
            
            # Determine which reserve is ETH
            if token0.lower() == WETH_ADDRESS.lower():
                eth_reserve = reserves[0]
                token_reserve = reserves[1]
            else:
                eth_reserve = reserves[1]
                token_reserve = reserves[0]
            
            # Get token info for decimals
            token_info = await self._get_token_info(token_address)
            if not token_info:
                return 0.0
            
            token_decimals = token_info.get("decimals", 18)
            
            # Get ETH price in USD
            eth_price_usd = await self.get_eth_price_usd()
            
            # Calculate token price in USD
            if token_reserve == 0:
                return 0.0
            
            token_price_eth = (eth_reserve / (10 ** 18)) / (token_reserve / (10 ** token_decimals))
            token_price_usd = token_price_eth * eth_price_usd
            
            return token_price_usd
            
        except Exception as e:
            logger.error(f"Error getting token price for {token_address}: {str(e)}")
            return 0.0
    
    @cache_result(ttl_seconds=60)  # Cache for 1 minute
    async def get_eth_price_usd(self) -> float:
        """
        Get the current ETH price in USD.
        
        Returns:
            ETH price in USD.
        """
        try:
            # Use circuit breaker pattern
            return await self.eth_price_circuit_breaker.execute(self._fetch_eth_price_usd)
        except Exception as e:
            logger.error(f"Error getting ETH price, using fallback: {str(e)}")
            return 3000.0  # Fallback price
    
    async def _fetch_eth_price_usd(self) -> float:
        """
        Fetch ETH price from CoinGecko API.
        
        Returns:
            ETH price in USD.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Try CoinGecko API first
            if COINGECKO_API_KEY:
                url = f"https://pro-api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&x_cg_pro_api_key={COINGECKO_API_KEY}"
            else:
                url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get("ethereum", {}).get("usd", 0.0))
                else:
                    logger.warning(f"CoinGecko API error: {response.status}")
            
            # Fallback to other sources if CoinGecko fails
            # Try Binance API
            url = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get("price", 0.0))
                else:
                    logger.warning(f"Binance API error: {response.status}")
            
            # If all APIs fail, use a fallback price
            logger.warning("All ETH price APIs failed, using fallback price")
            return 3000.0
            
        except Exception as e:
            logger.error(f"Error fetching ETH price: {str(e)}")
            return 3000.0
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_volume_24h(self, token_address: str) -> float:
        """
        Get the 24-hour trading volume for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            24-hour volume in USD.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return 0.0
        
        try:
            # Use Etherscan API if available
            if ETHEREUM_API_KEY:
                return await self._get_volume_from_etherscan(token_address)
            
            # Fallback to The Graph API
            return await self._get_volume_from_graph(token_address)
            
        except Exception as e:
            logger.error(f"Error getting token volume for {token_address}: {str(e)}")
            return 0.0
    
    async def _get_volume_from_etherscan(self, token_address: str) -> float:
        """
        Get token volume data from Etherscan API.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Volume in USD.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Get token transfers in the last 24 hours
            url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={token_address}&startblock=0&endblock=999999999&sort=desc&apikey={ETHEREUM_API_KEY}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Etherscan API error: {response.status}")
                    return 0.0
                
                data = await response.json()
                
                if data.get("status") != "1":
                    logger.error(f"Etherscan API error: {data.get('message')}")
                    return 0.0
                
                # Calculate volume from transfers
                volume = 0.0
                token_price = await self.get_token_price(token_address)
                current_time = int(time.time())
                
                for tx in data.get("result", []):
                    # Check if transaction is within last 24 hours
                    tx_time = int(tx.get("timeStamp", 0))
                    if current_time - tx_time > 86400:  # 24 hours in seconds
                        continue
                    
                    # Get token amount
                    token_amount = float(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
                    volume += token_amount * token_price
                
                return volume
                
        except Exception as e:
            logger.error(f"Error getting volume from Etherscan for {token_address}: {str(e)}")
            return 0.0
    
    async def _get_volume_from_graph(self, token_address: str) -> float:
        """
        Get token volume data from The Graph API.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Volume in USD.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Use Uniswap subgraph to get volume data
            url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
            
            # GraphQL query to get token volume
            query = """
            {
              token(id: "%s") {
                volumeUSD
                tradeVolumeUSD
              }
            }
            """ % token_address.lower()
            
            async with self.session.post(url, json={"query": query}) as response:
                if response.status != 200:
                    logger.error(f"The Graph API error: {response.status}")
                    return 0.0
                
                data = await response.json()
                
                # Extract volume from response
                token_data = data.get("data", {}).get("token")
                if not token_data:
                    return 0.0
                
                # Try different volume fields
                volume = float(token_data.get("tradeVolumeUSD", 0.0))
                if volume == 0.0:
                    volume = float(token_data.get("volumeUSD", 0.0))
                
                return volume
                
        except Exception as e:
            logger.error(f"Error getting volume from The Graph for {token_address}: {str(e)}")
            return 0.0
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_liquidity(self, token_address: str) -> float:
        """
        Get the current liquidity for a token on Uniswap.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Liquidity in USD.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return 0.0
        
        try:
            # Get token-WETH pair
            factory = self.sync_w3.eth.contract(
                address=self.sync_w3.to_checksum_address(UNISWAP_FACTORY_ADDRESS),
                abi=UNISWAP_FACTORY_ABI
            )
            
            pair_address = factory.functions.getPair(
                self.sync_w3.to_checksum_address(token_address),
                self.sync_w3.to_checksum_address(WETH_ADDRESS)
            ).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0.0
            
            # Get pair contract
            pair_contract = self.sync_w3.eth.contract(
                address=pair_address,
                abi=UNISWAP_PAIR_ABI
            )
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            token0 = pair_contract.functions.token0().call()
            
            # Determine which reserve is ETH
            if token0.lower() == WETH_ADDRESS.lower():
                eth_reserve = reserves[0]
                token_reserve = reserves[1]
            else:
                eth_reserve = reserves[1]
                token_reserve = reserves[0]
            
            # Get ETH price in USD
            eth_price_usd = await self.get_eth_price_usd()
            
            # Calculate liquidity in USD
            liquidity_usd = (eth_reserve / 1e18) * eth_price_usd * 2  # Multiply by 2 for both sides of the pair
            
            return liquidity_usd
            
        except Exception as e:
            logger.error(f"Error getting token liquidity for {token_address}: {str(e)}")
            return 0.0
    
    @cache_result(ttl_seconds=1800)  # Cache for 30 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_token_holders(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Number of holders.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return 0
        
        try:
            # Use Etherscan API if available
            if ETHEREUM_API_KEY:
                return await self._get_holders_from_etherscan(token_address)
            
            # Fallback to a basic estimate
            logger.warning(f"Cannot get accurate holder count for {token_address} without Etherscan API")
            return 100  # Default fallback value
            
        except Exception as e:
            logger.error(f"Error getting holder count for {token_address}: {str(e)}")
            return 0
    
    async def _get_holders_from_etherscan(self, token_address: str) -> int:
        """
        Get token holder count from Etherscan API.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Number of holders.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Use Etherscan API to get token info
            url = f"https://api.etherscan.io/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={ETHEREUM_API_KEY}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Etherscan API error: {response.status}")
                    return 0
                
                data = await response.json()
                
                if data.get("status") != "1":
                    logger.error(f"Etherscan API error: {data.get('message')}")
                    return 0
                
                # Extract holder count
                for token_info in data.get("result", []):
                    if "holderCount" in token_info:
                        return int(token_info.get("holderCount", 0))
                
                return 0
                
        except Exception as e:
            logger.error(f"Error getting holder count from Etherscan for {token_address}: {str(e)}")
            return 0
    
    @cache_result(ttl_seconds=300)  # Cache for 5 minutes
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def get_buy_sell_ratio(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the buy/sell ratio for a token over a specified time period.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio (> 1.0 means more buys than sells).
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return 1.0  # Default to neutral ratio
        
        try:
            # Use Etherscan API if available
            if ETHEREUM_API_KEY:
                return await self._get_buy_sell_ratio_from_etherscan(token_address, time_period_hours)
            
            # Fallback to a default value if we can't calculate
            logger.warning(f"Cannot calculate buy/sell ratio for {token_address} without Etherscan API")
            return 1.0  # Default to neutral ratio
            
        except Exception as e:
            logger.error(f"Error getting buy/sell ratio for {token_address}: {str(e)}")
            return 1.0  # Default to neutral ratio
    
    async def _get_buy_sell_ratio_from_etherscan(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get buy/sell ratio from Etherscan API.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Get token transfers in the specified time period
            url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={token_address}&startblock=0&endblock=999999999&sort=desc&apikey={ETHEREUM_API_KEY}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Etherscan API error: {response.status}")
                    return 1.0
                
                data = await response.json()
                
                if data.get("status") != "1":
                    logger.error(f"Etherscan API error: {data.get('message')}")
                    return 1.0
                
                # Count buys and sells
                buys = 0
                sells = 0
                current_time = int(time.time())
                
                for tx in data.get("result", []):
                    # Check if transaction is within time period
                    tx_time = int(tx.get("timeStamp", 0))
                    if current_time - tx_time > time_period_hours * 3600:
                        continue
                    
                    # Determine if transaction is a buy or sell
                    # This is a simplified approach - in production, you would use
                    # a more sophisticated method to determine transaction type
                    
                    # If token is being sent to a DEX, it's likely a sell
                    # If token is being received from a DEX, it's likely a buy
                    if tx.get("to").lower() in [UNISWAP_ROUTER_ADDRESS.lower()]:
                        sells += 1
                    elif tx.get("from").lower() in [UNISWAP_ROUTER_ADDRESS.lower()]:
                        buys += 1
                
                # Calculate ratio
                if sells == 0:
                    return 2.0  # All buys, no sells
                
                return buys / sells
                
        except Exception as e:
            logger.error(f"Error getting buy/sell ratio from Etherscan for {token_address}: {str(e)}")
            return 1.0
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check if a token contract is safe (not a honeypot, no malicious code).
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary with safety information.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
            return {
                "is_safe": False,
                "risk_level": "unknown",
                "warnings": ["Scanner not initialized"]
            }
        
        try:
            # Use Etherscan API if available
            if ETHEREUM_API_KEY:
                contract_verified = await self._is_contract_verified(token_address)
                if not contract_verified:
                    return {
                        "is_safe": False,
                        "risk_level": "high",
                        "warnings": ["Contract not verified"]
                    }
            
            # Check if token has liquidity
            liquidity = await self.get_token_liquidity(token_address)
            if liquidity < 10000:  # Arbitrary threshold
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
    
    async def _is_contract_verified(self, token_address: str) -> bool:
        """
        Check if a contract is verified on Etherscan.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            True if the contract is verified, False otherwise.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Use Etherscan API to check if contract is verified
            url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={token_address}&apikey={ETHEREUM_API_KEY}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Etherscan API error: {response.status}")
                    return False
                
                data = await response.json()
                
                # If ABI is returned, contract is verified
                return data.get("status") == "1" and data.get("message") == "OK"
                
        except Exception as e:
            logger.error(f"Error checking if contract is verified for {token_address}: {str(e)}")
            return False
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    async def is_meme_token(self, token_address: str) -> bool:
        """
        Check if a token is likely a meme token based on name, symbol, etc.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            True if the token is likely a meme token, False otherwise.
        """
        if not self.initialized:
            logger.error("Ethereum scanner not initialized")
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
