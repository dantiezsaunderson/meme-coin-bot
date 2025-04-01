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
        self.ethereum_scanner = get_scanner('ethereum')
        self.solana_scanner = get_scanner('solana')
        self.running = False
    
    async def start(self):
        """Start the blockchain scanner service."""
        self.running = True
        logger.info("Starting blockchain scanner service")
        
        while self.running:
            try:
                # Scan Ethereum
                await self._scan_blockchain('ethereum')
                
                # Scan Solana
                await self._scan_blockchain('solana')
                
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
    
    async def _scan_blockchain(self, blockchain_type: str):
        """
        Scan a blockchain for new tokens and update the database.
        
        Args:
            blockchain_type: The blockchain type ('ethereum' or 'solana').
        """
        logger.info(f"Scanning {blockchain_type} blockchain")
        
        try:
            # Get the appropriate scanner
            scanner = get_scanner(blockchain_type)
            
            # Scan for new tokens
            new_tokens = await scanner.scan_for_new_tokens()
            logger.info(f"Found {len(new_tokens)} new tokens on {blockchain_type}")
            
            # Process each new token
            for token_info in new_tokens:
                await self._process_token(token_info, scanner)
            
            # Update existing tokens
            await self._update_existing_tokens(blockchain_type)
        
        except Exception as e:
            logger.error(f"Error scanning {blockchain_type} blockchain: {str(e)}")
    
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
            price = await scanner.get_token_price(token_address)
            volume = await scanner.get_token_volume(token_address)
            buy_sell_ratio = await scanner.get_buy_sell_ratio(token_address)
            holders_count = await scanner.get_holder_count(token_address)
            safety_check = await scanner.check_contract_safety(token_address)
            
            # Create new token
            new_token = Token(
                address=token_address,
                name=token_info.get('name', ''),
                symbol=token_info.get('symbol', ''),
                blockchain=token_info['blockchain'],
                
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
            logger.info(f"Added new token: {new_token.symbol} ({new_token.blockchain})")
        
        except Exception as e:
            logger.error(f"Error processing token {token_info.get('symbol', 'unknown')}: {str(e)}")
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()
    
    async def _update_existing_tokens(self, blockchain_type: str):
        """
        Update existing tokens in the database.
        
        Args:
            blockchain_type: The blockchain type ('ethereum' or 'solana').
        """
        try:
            # Get a database session
            session = next(get_session())
            
            # Get tokens for this blockchain
            tokens = session.query(Token).filter(Token.blockchain == blockchain_type).all()
            logger.info(f"Updating {len(tokens)} existing tokens on {blockchain_type}")
            
            # Get the appropriate scanner
            scanner = get_scanner(blockchain_type)
            
            # Update each token
            for token in tokens:
                try:
                    # Get updated token information
                    price = await scanner.get_token_price(token.address)
                    volume = await scanner.get_token_volume(token.address)
                    liquidity = await scanner.get_token_liquidity(token.address)
                    buy_sell_ratio = await scanner.get_buy_sell_ratio(token.address)
                    holders_count = await scanner.get_holder_count(token.address)
                    
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
            logger.error(f"Error updating existing tokens on {blockchain_type}: {str(e)}")
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()

# Singleton instance
scanner_service = BlockchainScannerService()
