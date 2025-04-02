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
        try:
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
                
            self.initialization_successful = True
        except Exception as e:
            logger.error(f"Error initializing Ethereum scanner: {str(e)}")
            self.initialization_successful = False
    
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan the Ethereum blockchain for new token launches via Uniswap pair creation events.
        
        Returns:
            List of dictionaries containing token information.
        """
        if not hasattr(self, 'initialization_successful') or not self.initialization_successful:
            logger.warning("Ethereum scanner not properly initialized. Returning empty list.")
            return []
            
        logger.info("Scanning Ethereum blockchain for new token launches")
        new_tokens = []
        
        try:
            # Get the latest block number
            latest_block = await self.w3.eth.block_number
            
            # Look back approximately 1 hour (assuming 15-second block time)
            # Convert to hex string format to avoid invalid fromBlock argument issues
            from_block = hex(latest_block - 240)
            
            # Use get_logs instead of create_filter for better compatibility
            pair_created_event_signature = self.w3.keccak(text="PairCreated(address,address,address,uint256)").hex()
            logs = await self.w3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': 'latest',
                'address': self.w3.to_checksum_address(UNISWAP_FACTORY_ADDRESS),
                'topics': [pair_created_event_signature]
            })
            
            logger.info(f"Found {len(logs)} new Uniswap pairs")
            
            for log in logs:
                # Decode the log data
                decoded_log = self.uniswap_factory.events.PairCreated().process_log(log)
                token0 = decoded_log['args']['token0']
                token1 = decoded_log['args']['token1']
                pair_address = decoded_log['args']['pair']
                
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
            
        except Exception as e:
            logger.error(f"Error scanning Ethereum blockchain: {str(e)}")
            return []
    
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
            
            # Determine which reserve is ETH
            if token0.lower() == WETH_ADDRESS.lower():
                eth_reserve = reserves[0]
                token_reserve = reserves[1]
            else:
                eth_reserve = reserves[1]
                token_reserve = reserves[0]
            
            # Get ETH price in USD (simplified, would use an oracle in production)
            eth_price_usd = 3000  # Example fixed price, would use an oracle in production
            
            # Calculate liquidity in USD
            liquidity_usd = (eth_reserve / 1e18) * eth_price_usd * 2  # Multiply by 2 for both sides of the pair
            
            return liquidity_usd
        
        except Exception as e:
            logger.error(f"Error getting token liquidity for {token_address}: {str(e)}")
            return 0.0
    
    async def get_token_volume_24h(self, token_address: str) -> float:
        """
        Get the 24-hour trading volume for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            24-hour volume in USD.
        """
        # In a real implementation, this would query trading volume from a DEX API or subgraph
        # For simplicity, we'll return a random value between 0 and 100K
        import random
        return random.uniform(0, 100000)
    
    async def get_token_holders(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Number of holders.
        """
        # In a real implementation, this would query holder count from Etherscan API or similar
        # For simplicity, we'll return a random value between 10 and 1000
        import random
        return random.randint(10, 1000)
    
    async def get_buy_sell_ratio(self, token_address: str) -> float:
        """
        Get the buy/sell ratio for a token.
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Buy/sell ratio.
        """
        # In a real implementation, this would analyze recent transactions
        # For simplicity, we'll return a random value between 0.5 and 3.0
        import random
        return random.uniform(0.5, 3.0)
    
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check if a token contract is safe (not a honeypot, no malicious code).
        
        Args:
            token_address: The token contract address.
            
        Returns:
            Dictionary with safety information.
        """
        if not self.has_honeypot_detector:
            # If no honeypot detector, return a basic safety check
            return {
                "is_safe": True,
                "risk_level": "unknown",
                "warnings": ["No honeypot detection available"]
            }
        
        try:
            # Use honeypot detector contract
            result = await self.honeypot_detector.functions.scanToken(
                self.w3.to_checksum_address(token_address),
                self.w3.to_checksum_address(UNISWAP_ROUTER_ADDRESS)
            ).call()
            
            is_honeypot = result[0]
            message = result[1]
            
            if is_honeypot:
                return {
                    "is_safe": False,
                    "risk_level": "high",
                    "warnings": [f"Potential honeypot: {message}"]
                }
            else:
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
