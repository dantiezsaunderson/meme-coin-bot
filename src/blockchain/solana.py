"""
Solana blockchain scanner implementation for the Meme Coin Signal Bot.

This module implements the BlockchainScanner interface for the Solana blockchain.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import base64
import random

from ..config import SOLANA_RPC_URL, MIN_LIQUIDITY_USD
from .base import BlockchainScanner
from ..database.models import BlockchainType

# Configure logging
logger = logging.getLogger(__name__)

# Common addresses
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL_MINT = "So11111111111111111111111111111111111111112"
RAYDIUM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_PROGRAM_ID = "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP"

# Import required packages for Solana and Helius integration
import helius
from helius import BalancesAPI, NFTAPI, TransactionsAPI

# Set Solana as available since we're using live integration
SOLANA_AVAILABLE = True

# Extract Helius API key from the RPC URL
HELIUS_API_KEY = SOLANA_RPC_URL.split('api-key=')[-1] if 'api-key=' in SOLANA_RPC_URL else None
if not HELIUS_API_KEY:
    logger.warning("Helius API key not found in SOLANA_RPC_URL. Some features may not work properly.")
    
# Initialize Helius APIs
try:
    balances_api = BalancesAPI(HELIUS_API_KEY) if HELIUS_API_KEY else None
    nft_api = NFTAPI(HELIUS_API_KEY) if HELIUS_API_KEY else None
    transactions_api = TransactionsAPI(HELIUS_API_KEY) if HELIUS_API_KEY else None
    logger.info("Helius API clients initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Helius API clients: {str(e)}")

class SolanaScanner(BlockchainScanner):
    """Solana blockchain scanner implementation."""
    
    def __init__(self):
        """Initialize the Solana scanner."""
        # Use requests directly instead of AsyncClient
        self.helius_balances_api = balances_api
        self.helius_nft_api = nft_api
        self.helius_transactions_api = transactions_api
    
    async def scan_for_new_tokens(self) -> List[Dict[str, Any]]:
        """
        Scan the Solana blockchain for new token launches using Helius API.
        
        Returns:
            List of dictionaries containing token information.
        """
        logger.info("Scanning Solana blockchain for new token launches using Helius API")
        
        new_tokens = []
        
        try:
            # Use Helius TransactionsAPI to get recent transactions for Raydium and Orca
            # to find new token pool creations
            
            # Get recent transactions for Raydium program
            raydium_txs = []
            if self.helius_transactions_api:
                try:
                    # Get recent transactions for Raydium program
                    raydium_txs = self.helius_transactions_api.get_parsed_transaction_history(
                        RAYDIUM_PROGRAM_ID,
                        limit=50
                    )
                    logger.info(f"Retrieved {len(raydium_txs) if raydium_txs else 0} Raydium transactions")
                except Exception as e:
                    logger.error(f"Error getting Raydium transactions: {str(e)}")
            
            # Get recent transactions for Orca program
            orca_txs = []
            if self.helius_transactions_api:
                try:
                    # Get recent transactions for Orca program
                    orca_txs = self.helius_transactions_api.get_parsed_transaction_history(
                        ORCA_PROGRAM_ID,
                        limit=50
                    )
                    logger.info(f"Retrieved {len(orca_txs) if orca_txs else 0} Orca transactions")
                except Exception as e:
                    logger.error(f"Error getting Orca transactions: {str(e)}")
            
            # Process Raydium transactions to find new token pools
            for tx in raydium_txs or []:
                try:
                    # Extract token addresses from transaction
                    token_addresses = self._extract_token_addresses_from_tx(tx)
                    
                    for token_address in token_addresses:
                        # Skip known tokens
                        if token_address in [USDC_MINT, WSOL_MINT]:
                            continue
                        
                        # Get token info
                        token_info = await self._get_token_info(token_address)
                        if not token_info:
                            continue
                        
                        # Check liquidity
                        liquidity = await self.get_token_liquidity(token_address)
                        if liquidity < MIN_LIQUIDITY_USD:
                            continue
                        
                        # Add liquidity to token info
                        token_info["liquidity_usd"] = liquidity
                        token_info["blockchain"] = BlockchainType.SOLANA.value
                        
                        # Check if it's a potential meme coin based on name/symbol
                        if self._is_potential_meme_coin(token_info):
                            # Avoid duplicates
                            if not any(t["address"] == token_address for t in new_tokens):
                                new_tokens.append(token_info)
                
                except Exception as e:
                    logger.error(f"Error processing Raydium transaction: {str(e)}")
                    continue
            
            # Process Orca transactions to find new token pools
            for tx in orca_txs or []:
                try:
                    # Extract token addresses from transaction
                    token_addresses = self._extract_token_addresses_from_tx(tx)
                    
                    for token_address in token_addresses:
                        # Skip known tokens
                        if token_address in [USDC_MINT, WSOL_MINT]:
                            continue
                        
                        # Skip tokens we've already processed
                        if any(t["address"] == token_address for t in new_tokens):
                            continue
                        
                        # Get token info
                        token_info = await self._get_token_info(token_address)
                        if not token_info:
                            continue
                        
                        # Check liquidity
                        liquidity = await self.get_token_liquidity(token_address)
                        if liquidity < MIN_LIQUIDITY_USD:
                            continue
                        
                        # Add liquidity to token info
                        token_info["liquidity_usd"] = liquidity
                        token_info["blockchain"] = BlockchainType.SOLANA.value
                        
                        # Check if it's a potential meme coin based on name/symbol
                        if self._is_potential_meme_coin(token_info):
                            new_tokens.append(token_info)
                
                except Exception as e:
                    logger.error(f"Error processing Orca transaction: {str(e)}")
                    continue
            
            logger.info(f"Found {len(new_tokens)} potential new meme coins on Solana")
            return new_tokens
        
        except Exception as e:
            logger.error(f"Error scanning Solana blockchain: {str(e)}")
            # We don't want to return mock data in production
            return []
    
    def _extract_token_addresses_from_tx(self, tx: Dict[str, Any]) -> List[str]:
        """
        Extract token addresses from a transaction.
        
        Args:
            tx: Transaction data from Helius API.
            
        Returns:
            List of token addresses.
        """
        token_addresses = []
        
        try:
            # Extract token addresses from transaction data
            # This is a simplified implementation - in production, would need more robust parsing
            
            # Check if we have account keys
            if 'accountKeys' in tx:
                # Look for token program interactions
                token_program_id = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                for account in tx['accountKeys']:
                    if account.get('program') == 'spl-token':
                        token_address = account.get('pubkey')
                        if token_address and token_address != token_program_id:
                            token_addresses.append(token_address)
            
            # Check for token balances
            if 'meta' in tx and 'postTokenBalances' in tx['meta']:
                for balance in tx['meta']['postTokenBalances']:
                    if 'mint' in balance:
                        token_addresses.append(balance['mint'])
            
            # Check for instructions that might contain token addresses
            if 'instructions' in tx:
                for instruction in tx['instructions']:
                    if 'accounts' in instruction:
                        for account in instruction['accounts']:
                            # Heuristic: token addresses are usually 32-44 characters
                            if isinstance(account, str) and len(account) >= 32 and len(account) <= 44:
                                token_addresses.append(account)
            
            # Remove duplicates
            token_addresses = list(set(token_addresses))
            
            return token_addresses
        
        except Exception as e:
            logger.error(f"Error extracting token addresses from transaction: {str(e)}")
            return []
    
    async def _get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get basic information about a token using Helius API.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary containing token information or None if error.
        """
        try:
            # First try to use Helius BalancesAPI to get token info
            if self.helius_balances_api:
                try:
                    # Get token metadata from Helius
                    token_metadata = self.helius_balances_api.get_token_metadata(token_address)
                    
                    if token_metadata:
                        # Extract token data from Helius response
                        name = token_metadata.get('name', f"Solana Token {token_address[:6]}")
                        symbol = token_metadata.get('symbol', f"SOL{token_address[:4]}")
                        decimals = token_metadata.get('decimals', 9)
                        
                        # For supply, use a default value since we can't get it from RPC now
                        total_supply = 1000000000  # Default large supply
                        
                        return {
                            "address": token_address,
                            "name": name,
                            "symbol": symbol,
                            "decimals": decimals,
                            "total_supply": total_supply
                        }
                except Exception as e:
                    logger.warning(f"Error getting token info from Helius for {token_address}: {str(e)}")
            
            # Fallback to basic info if Helius API failed
            logger.info(f"Using basic token info for {token_address}")
            
            return {
                "address": token_address,
                "name": f"Solana Token {token_address[:6]}",
                "symbol": f"SOL{token_address[:4]}",
                "decimals": 9,
                "total_supply": 1000000000  # Default large supply
            }
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {str(e)}")
            return None
    
    async def _get_token_metadata(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token metadata from Metaplex using Helius API.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary containing token metadata or None if error.
        """
        try:
            # Try to use Helius NFTAPI to get token metadata
            if self.helius_nft_api:
                try:
                    # Get NFT metadata from Helius
                    nft_metadata = self.helius_nft_api.get_nft_metadata(token_address)
                    
                    if nft_metadata and 'onChainMetadata' in nft_metadata:
                        metadata = nft_metadata['onChainMetadata'].get('metadata', {})
                        return {
                            "name": metadata.get('name', f"Solana Token {token_address[:6]}"),
                            "symbol": metadata.get('symbol', f"SOL{token_address[:4]}"),
                            "uri": metadata.get('uri', '')
                        }
                except Exception as e:
                    logger.warning(f"Error getting NFT metadata from Helius for {token_address}: {str(e)}")
            
            # Fallback to empty metadata
            return None
            
        except Exception as e:
            logger.error(f"Error getting token metadata for {token_address}: {str(e)}")
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
            "gme", "amc", "stonk", "tendies", "wsb", "wojak", "pepe", "frog",
            "bonk", "samo", "sol"
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
        Get the current liquidity for a token on Raydium/Orca.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Liquidity in USD.
        """
        if not SOLANA_AVAILABLE:
            # Return mock data
            return random.uniform(10000, 100000)
        
        try:
            # In a real implementation, query Raydium/Orca pools
            # For simplicity, we'll check for token accounts with large balances
            
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
            
            # Get token price (simplified)
            price = await self.get_token_price(token_address)
            
            # Calculate liquidity in USD
            liquidity_usd = (total_balance / (10 ** decimals)) * price
            
            return liquidity_usd
        except Exception as e:
            logger.error(f"Error getting liquidity for {token_address}: {str(e)}")
            return 0.0
    
    async def get_token_volume(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the trading volume for a token over a specified time period.
        
        Args:
            token_address: The token mint address.
            time_period_hours: The time period in hours.
            
        Returns:
            Volume in USD.
        """
        # In a real implementation, query an indexer or DEX API
        # For simplicity, we'll return a random value
        return random.uniform(1000, 100000)
    
    async def get_buy_sell_ratio(self, token_address: str, time_period_hours: int = 24) -> float:
        """
        Get the buy/sell ratio for a token over a specified time period.
        
        Args:
            token_address: The token mint address.
            time_period_hours: The time period in hours.
            
        Returns:
            Buy/sell ratio (> 1.0 means more buys than sells).
        """
        # In a real implementation, query an indexer or DEX API
        # For simplicity, we'll return a random value
        return random.uniform(0.5, 2.0)
    
    async def get_holder_count(self, token_address: str) -> int:
        """
        Get the number of holders for a token.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Number of holders.
        """
        # In a real implementation, query an indexer or token accounts
        # For simplicity, we'll return a random value
        return random.randint(100, 10000)
    
    async def get_token_price(self, token_address: str) -> float:
        """
        Get the current price of a token in USD.
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Price in USD.
        """
        # In a real implementation, query a price oracle or DEX
        # For simplicity, we'll return a random value
        return random.uniform(0.00001, 0.1)
    
    async def check_contract_safety(self, token_address: str) -> Dict[str, Any]:
        """
        Check if a token contract is safe (not a honeypot, etc.).
        
        Args:
            token_address: The token mint address.
            
        Returns:
            Dictionary containing safety information.
        """
        # In a real implementation, check for honeypot, rugpull risks, etc.
        # For simplicity, we'll return random values
        return {
            "contract_verified": random.choice([True, False]),
            "is_honeypot": random.choice([True, False, False, False]),  # Less likely to be a honeypot
            "contract_audit_score": random.uniform(0, 100)
        }
