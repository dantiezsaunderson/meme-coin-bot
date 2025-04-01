"""
Ethereum blockchain scanner implementation for the Meme Coin Signal Bot.

This module implements the BlockchainScanner interface for the Ethereum blockchain.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from web3 import Web3, AsyncWeb3
from web3.exceptions import ContractLogicError
import json

from ..config import ETHEREUM_RPC_URL, MIN_LIQUIDITY_USD
from .base import BlockchainScanner
from ..database.models import BlockchainType

# Configure logging
logger = logging.getLogger(__name__)

# Standard ERC20 ABI for token interactions
ERC20_ABI = json.loads('''[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
]''')

# Uniswap V2 Factory ABI for pair creation events
UNISWAP_FACTORY_ABI = json.loads('''[
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"address","name":"pair","type":"address"},{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"PairCreated","type":"event"},
    {"constant":true,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"allPairs","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[],"name":"allPairsLength","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
]''')

# Uniswap V2 Pair ABI for liquidity and reserves
UNISWAP_PAIR_ABI = json.loads('''[
    {"constant":true,"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},
    {"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"}
]''')

# Honeypot detector ABI (simplified)
HONEYPOT_DETECTOR_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"address","name":"_router","type":"address"}],"name":"scanToken","outputs":[{"internalType":"bool","name":"honeypot","type":"bool"},{"internalType":"string","name":"message","type":"string"}],"stateMutability":"view","type":"function"}
]''')

# Common addresses
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
UNISWAP_FACTORY_ADDRESS = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
HONEYPOT_DETECTOR_ADDRESS = "0x5E2898aA42ff89cd2a0fD391A312D9d60F91A7B0"  # Example address

class EthereumScanner(BlockchainScanner):
    """Ethereum blockchain scanner implementation."""
    
    def __init__(self):
        """Initialize the Ethereum scanner."""
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(ETHEREUM_RPC_URL))
        self.sync_w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))
        
        # Initialize contracts
        self.uniswap_factory = self.w3.eth.contract(
            address=self.w3.to_checksum_address(UNISWAP_FACTORY_ADDRESS),
            abi=UNISWAP_FACTORY_ABI
        )
        
        # For honeypot detection (if available)
        try:
            self.honeypot_detector = self.w3.eth.contract(
                address=self.w3.to_checksum_address(HONEYPOT_DETECTOR_ADDRESS),
                abi=HONEYPOT_DETECTOR_ABI
            )
            self.has_honeypot_detector = True
        except:
            self.has_honeypot_detector = False
            logger.warning("Honeypot detector contract not available")
    
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan the Ethereum blockchain for new token launches via Uniswap pair creation events.
        
        Returns:
            List of dictionaries containing token information.
        """
        logger.info("Scanning Ethereum blockchain for new token launches")
        new_tokens = []
        
        # Get the latest block number
        latest_block = await self.w3.eth.block_number
        
        # Look back approximately 1 hour (assuming 15-second block time)
        from_block = latest_block - 240
        
        # Get PairCreated events from Uniswap Factory
        pair_created_filter = self.uniswap_factory.events.PairCreated.create_filter(
            fromBlock=from_block,
            toBlock=latest_block
        )
        
        events = await pair_created_filter.get_all_entries()
        logger.info(f"Found {len(events)} new Uniswap pairs")
        
        for event in events:
            token0 = event.args.token0
            token1 = event.args.token1
            pair_address = event.args.pair
            
            # Determine which token is the new one (not WETH)
            if token0.lower() == WETH_ADDRESS.lower():
                token_address = token1
            elif token1.lower() == WETH_ADDRESS.lower():
                token_address = token0
            else:
                # Skip pairs that don't include WETH
                continue
            
            # Get token information
            token_info = await self._get_token_info(token_address)
            if not token_info:
                continue
            
            # Check liquidity
            liquidity = await self.get_token_liquidity(token_address)
            if liquidity < MIN_LIQUIDITY_USD:
                continue
            
            # Add liquidity to token info
            token_info["liquidity_usd"] = liquidity
            token_info["pair_address"] = pair_address
            token_info["blockchain"] = BlockchainType.ETHEREUM.value
            
            # Check if it's a potential meme coin based on name/symbol
            if self._is_potential_meme_coin(token_info):
                new_tokens.append(token_info)
        
        logger.info(f"Found {len(new_tokens)} potential new meme coins on Ethereum")
        return new_tokens
    
    async def _get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get basic information about a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary containing token information or None if error.
        """
        try:
            token_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Get token details
            name_task = token_contract.functions.name().call()
            symbol_task = token_contract.functions.symbol().call()
            decimals_task = token_contract.functions.decimals().call()
            total_supply_task = token_contract.functions.totalSupply().call()
            
            # Execute all tasks concurrently
            name, symbol, decimals, total_supply = await asyncio.gather(
                name_task, symbol_task, decimals_task, total_supply_task
            )
            
            return {
                "address": token_address,
                "name": name,
                "symbol": symbol,
                "decimals": decimals,
                "total_supply": total_supply / (10 ** decimals)
            }
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {str(e)}")
            return None
    
    def _is_potential_meme_coin(self, token_info: Dict[str, Any]) -> bool:
        """
        Check if a token is potentially a meme coin based on its name and symbol.
        
        Args:
            token_info: Dictionary containing token information.
            
        Returns:
            True if the token is potentially a meme coin, False otherwise.
        """
        # Common meme coin keywords
        meme_keywords = [
            "doge", "shib", "pepe", "moon", "elon", "inu", "cat", "safe", "cum", 
            "chad", "based", "wojak", "frog", "rocket", "lambo", "diamond", "hands",
            "ape", "gorilla", "floki", "baby", "mini", "meme", "coin", "token",
            "gme", "amc", "stonk", "tendies", "wsb", "wojak", "pepe", "frog"
        ]
        
        name = token_info.get("name", "").lower()
        symbol = token_info.get("symbol", "").lower()
        
        # Check if any meme keyword is in the name or symbol
        for keyword in meme_keywords:
            if keyword in name or keyword in symbol:
                return True
        
        return False
    
    async def get_token_liquidity(self, token_address: str) -> float:
        """
        Get the current liquidity for a token on Uniswap.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Liquidity in USD.
        """
        try:
            # Find the token-WETH pair
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
            
            # Determine which reserve is ETH and which is the token
            if token0.lower() == token_address.lower():
                token_reserve = reserves[0]
                eth_reserve = reserves[1]
            else:
                token_reserve = reserves[1]
                eth_reserve = reserves[0]
            
            # Get ETH price in USD (simplified - in production use a price oracle)
            eth_price = await self._get_eth_price()
            
            # Calculate liquidity in USD (2 * ETH value)
            liquidity_usd = 2 * (eth_reserve / 1e18) * eth_price
            
            return liquidity_usd
        except Exception as e:
            logger.error(f"Error getting liquidity for {token_address}: {str(e)}")
            return 0.0
    
    async def _get_eth_price(self) -> float:
        """
        Get the current ETH price in USD.
        
        Returns:
            ETH price in USD.
        """
        # In a real implementation, use a price oracle or API
        # For simplicity, we'll use a hardcoded value
        return 3500.0  # Example ETH price
    
    async def get_token_volume(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the trading volume for a token over a specified time period.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Volume in USD.
        """
        # In a real implementation, query an indexer like The Graph
        # For simplicity, we'll return a random value
        import random
        return random.uniform(1000, 100000)
    
    async def get_buy_sell_ratio(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the buy/sell ratio for a token over a specified time period.
        
        Args:
            token_address: The token contract address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio (buys/sells).
        """
        # In a real implementation, query an indexer like The Graph
        # For simplicity, we'll return a random value
        import random
        return random.uniform(0.5, 3.0)
    
    async def get_holder_count(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Number of holders.
        """
        # In a real implementation, query an indexer or Etherscan API
        # For simplicity, we'll return a random value
        import random
        return random.randint(50, 5000)
    
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check the safety of a token's smart contract.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary containing safety information.
        """
        result = {
            "is_honeypot": False,
            "contract_verified": False,
            "contract_audit_score": 0.0,
            "issues": []
        }
        
        try:
            # Check if contract is verified (would use Etherscan API in production)
            result["contract_verified"] = True
            
            # Check for honeypot
            if self.has_honeypot_detector:
                honeypot_check = await self.honeypot_detector.functions.scanToken(
                    self.w3.to_checksum_address(token_address),
                    self.w3.to_checksum_address(UNISWAP_ROUTER_ADDRESS)
                ).call()
                
                result["is_honeypot"] = honeypot_check[0]
                if honeypot_check[0]:
                    result["issues"].append(f"Honeypot detected: {honeypot_check[1]}")
            
            # Calculate safety score (0-100)
            # In production, this would be more sophisticated
            base_score = 0 if result["is_honeypot"] else 70
            verification_bonus = 30 if result["contract_verified"] else 0
            result["contract_audit_score"] = base_score + verification_bonus
            
        except Exception as e:
            logger.error(f"Error checking contract safety for {token_address}: {str(e)}")
            result["issues"].append(f"Error during safety check: {str(e)}")
            result["contract_audit_score"] = 0.0
        
        return result
    
    async def get_token_price(self, token_address: str) -> float:
        """
        Get the current price of a token in USD.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Price in USD.
        """
        try:
            # Find the token-WETH pair
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
            
            # Get token contract for decimals
            token_contract = self.sync_w3.eth.contract(
                address=self.sync_w3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            token_decimals = token_contract.functions.decimals().call()
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            token0 = pair_contract.functions.token0().call()
            
            # Determine which reserve is ETH and which is the token
            if token0.lower() == token_address.lower():
                token_reserve = reserves[0]
                eth_reserve = reserves[1]
            else:
                token_reserve = reserves[1]
                eth_reserve = reserves[0]
            
            # Get ETH price in USD
            eth_price = await self._get_eth_price()
            
            # Calculate token price in USD
            # price = (eth_reserve / token_reserve) * (eth_price / 10^(18 - token_decimals))
            price_in_eth = eth_reserve / token_reserve
            price_in_usd = price_in_eth * eth_price / (10 ** (18 - token_decimals))
            
            return price_in_usd
        except Exception as e:
            logger.error(f"Error getting price for {token_address}: {str(e)}")
            return 0.0
