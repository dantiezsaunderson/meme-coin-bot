"""
Blockchain scanner service for the Meme Coin Signal Bot.

This module provides a service that periodically scans blockchains for new tokens
and updates the database with token information.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..config import BLOCKCHAIN_SCAN_INTERVAL
from ..database import get_session, Token, BlockchainType
from . import get_scanner

# Configure logging
logger = logging.getLogger(__name__)

class BlockchainScannerService:
    """Service for scanning blockchains and updating the database."""
    
    def __init__(self):
        """Initialize the blockchain scanner service."""
        self.ethereum_scanner = None
        self.solana_scanner = None
        self.running = False
    
    async def start(self):
        """Start the blockchain scanner service."""
        self.running = True
        logger.info("Starting blockchain scanner service")
        
        # Initialize scanners with error handling
        try:
            self.ethereum_scanner = get_scanner('ethereum')
            logger.info("Ethereum scanner initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Ethereum scanner: {str(e)}")
            self.ethereum_scanner = None
        
        try:
            self.solana_scanner = get_scanner('solana')
            logger.info("Solana scanner initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Solana scanner: {str(e)}")
            self.solana_scanner = None
        
        if not self.ethereum_scanner and not self.solana_scanner:
            logger.error("No blockchain scanners could be initialized. Service will not scan blockchains.")
            return
        
        while self.running:
            try:
                # Scan Ethereum if scanner is available
                if self.ethereum_scanner:
                    await self._scan_blockchain(BlockchainType.ETHEREUM)
                
                # Scan Solana if scanner is available
                if self.solana_scanner:
                    await self._scan_blockchain(BlockchainType.SOLANA)
                
                # Wait for next scan
                logger.info(f"Blockchain scan completed. Next scan in {BLOCKCHAIN_SCAN_INTERVAL} seconds")
                await asyncio.sleep(BLOCKCHAIN_SCAN_INTERVAL)
            
            except Exception as e:
                logger.error(f"Error in blockchain scanner service: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def stop(self):
        """Stop the blockchain scanner service."""
        self.running = False
        logger.info("Stopping blockchain scanner service")
    
    async def _scan_blockchain(self, blockchain_type: BlockchainType):
        """
        Scan a blockchain for new tokens and update the database.
        
        Args:
            blockchain_type: The blockchain type (BlockchainType.ETHEREUM or BlockchainType.SOLANA).
        """
        logger.info(f"Scanning {blockchain_type.name} blockchain")
        
        try:
            # Get the appropriate scanner
            scanner = self.ethereum_scanner if blockchain_type == BlockchainType.ETHEREUM else self.solana_scanner
            if not scanner:
                logger.warning(f"No scanner available for {blockchain_type.name}. Skipping scan.")
                return
            
            # Scan for new tokens
            new_tokens = await scanner.scan_for_new_tokens()
            logger.info(f"Found {len(new_tokens)} new tokens on {blockchain_type.name}")
            
            # Process each new token
            for token_info in new_tokens:
                await self._process_token(token_info, scanner)
            
            # Update existing tokens
            await self._update_existing_tokens(blockchain_type, scanner)
        
        except Exception as e:
            logger.error(f"Error scanning {blockchain_type.name} blockchain: {str(e)}")
    
    async def _process_token(self, token_info: Dict[str, Any], scanner):
        """
        Process a new token and add it to the database.
        
        Args:
            token_info: Dictionary containing token information.
            scanner: The blockchain scanner instance.
        """
        try:
            # Get a database session
            session = next(get_session())
            
            # Check if token already exists
            existing_token = session.query(Token).filter(Token.address == token_info['address']).first()
            if existing_token:
                logger.info(f"Token {token_info['symbol']} already exists, updating")
                return
            
            # Get additional token information
            token_address = token_info['address']
            
            try:
                price = await scanner.get_token_price(token_address)
            except Exception as e:
                logger.warning(f"Error getting price for {token_info.get('symbol', 'unknown')}: {str(e)}")
                price = 0.0
            
            try:
                volume = await scanner.get_token_volume(token_address)
            except Exception as e:
                logger.warning(f"Error getting volume for {token_info.get('symbol', 'unknown')}: {str(e)}")
                volume = 0.0
            
            try:
                buy_sell_ratio = await scanner.get_buy_sell_ratio(token_address)
            except Exception as e:
                logger.warning(f"Error getting buy/sell ratio for {token_info.get('symbol', 'unknown')}: {str(e)}")
                buy_sell_ratio = 1.0
            
            try:
                holders_count = await scanner.get_holder_count(token_address)
            except Exception as e:
                logger.warning(f"Error getting holder count for {token_info.get('symbol', 'unknown')}: {str(e)}")
                holders_count = 0
            
            try:
                safety_check = await scanner.check_contract_safety(token_address)
            except Exception as e:
                logger.warning(f"Error checking contract safety for {token_info.get('symbol', 'unknown')}: {str(e)}")
                safety_check = {
                    'contract_verified': False,
                    'is_honeypot': False,
                    'contract_audit_score': 0.0
                }
            
            # Ensure blockchain type is the enum value, not string
            blockchain_enum = BlockchainType.ETHEREUM if token_info['blockchain'].upper() == 'ETHEREUM' else BlockchainType.SOLANA
            
            # Create new token
            new_token = Token(
                address=token_address,
                name=token_info.get('name', ''),
                symbol=token_info.get('symbol', ''),
                blockchain=blockchain_enum,
                
                # Contract details
                contract_verified=safety_check.get('contract_verified', False),
                is_honeypot=safety_check.get('is_honeypot', False),
                contract_audit_score=safety_check.get('contract_audit_score', 0.0),
                
                # Token metrics
                current_price_usd=price,
                market_cap_usd=price * token_info.get('total_supply', 0),
                liquidity_usd=token_info.get('liquidity_usd', 0),
                volume_24h_usd=volume,
                holders_count=holders_count,
                buy_sell_ratio=buy_sell_ratio,
                
                # Initial scores (will be updated by scoring engine)
                total_score=0.0,
                liquidity_score=0.0,
                volume_score=0.0,
                social_score=0.0,
                safety_score=0.0,
            )
            
            # Add to database
            session.add(new_token)
            session.commit()
            logger.info(f"Added new token: {new_token.symbol} ({new_token.blockchain.name})")
        
        except Exception as e:
            logger.error(f"Error processing token {token_info.get('symbol', 'unknown')}: {str(e)}")
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()
    
    async def _update_existing_tokens(self, blockchain_type: BlockchainType, scanner):
        """
        Update existing tokens in the database.
        
        Args:
            blockchain_type: The blockchain type (BlockchainType.ETHEREUM or BlockchainType.SOLANA).
            scanner: The blockchain scanner instance.
        """
        try:
            # Get a database session
            session = next(get_session())
            
            # Get tokens for this blockchain
            tokens = session.query(Token).filter(Token.blockchain == blockchain_type).all()
            logger.info(f"Updating {len(tokens)} existing tokens on {blockchain_type.name}")
            
            # Update each token
            for token in tokens:
                try:
                    # Get updated token information
                    try:
                        price = await scanner.get_token_price(token.address)
                    except Exception as e:
                        logger.warning(f"Error getting price for {token.symbol}: {str(e)}")
                        price = token.current_price_usd
                    
                    try:
                        volume = await scanner.get_token_volume(token.address)
                    except Exception as e:
                        logger.warning(f"Error getting volume for {token.symbol}: {str(e)}")
                        volume = token.volume_24h_usd
                    
                    try:
                        liquidity = await scanner.get_token_liquidity(token.address)
                    except Exception as e:
                        logger.warning(f"Error getting liquidity for {token.symbol}: {str(e)}")
                        liquidity = token.liquidity_usd
                    
                    try:
                        buy_sell_ratio = await scanner.get_buy_sell_ratio(token.address)
                    except Exception as e:
                        logger.warning(f"Error getting buy/sell ratio for {token.symbol}: {str(e)}")
                        buy_sell_ratio = token.buy_sell_ratio
                    
                    try:
                        holders_count = await scanner.get_holder_count(token.address)
                    except Exception as e:
                        logger.warning(f"Error getting holder count for {token.symbol}: {str(e)}")
                        holders_count = token.holders_count
                    
                    # Update token
                    token.current_price_usd = price
                    token.volume_24h_usd = volume
                    token.liquidity_usd = liquidity
                    token.buy_sell_ratio = buy_sell_ratio
                    token.holders_count = holders_count
                    token.updated_at = datetime.utcnow()
                    
                    # Commit changes
                    session.commit()
                
                except Exception as e:
                    logger.error(f"Error updating token {token.symbol}: {str(e)}")
                    session.rollback()
        
        except Exception as e:
            logger.error(f"Error updating existing tokens on {blockchain_type.name}: {str(e)}")
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()

# Singleton instance
scanner_service = BlockchainScannerService()
