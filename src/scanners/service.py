"""
Scanner service coordinator for the Meme Coin Bot.
Manages all blockchain scanners and coordinates token scanning.
"""
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional

from src.scanners.ethereum import EthereumScanner
from src.scanners.solana import SolanaScanner

# Setup logging
logger = logging.getLogger(__name__)

class ScannerService:
    """Service to coordinate blockchain scanners."""
    
    def __init__(self):
        """Initialize the scanner service."""
        self.scanners = {}
        self.running = False
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
        self.max_concurrent_scans = int(os.getenv("MAX_CONCURRENT_SCANS", "10"))
        self.scan_semaphore = asyncio.Semaphore(self.max_concurrent_scans)
    
    async def initialize(self) -> bool:
        """
        Initialize all scanners.
        
        Returns:
            True if at least one scanner was initialized successfully, False otherwise.
        """
        # Initialize Ethereum scanner
        eth_scanner = EthereumScanner()
        if await eth_scanner.initialize():
            self.scanners["ethereum"] = eth_scanner
            logger.info("Ethereum scanner initialized successfully")
        else:
            logger.error("Failed to initialize Ethereum scanner")
        
        # Initialize Solana scanner
        sol_scanner = SolanaScanner()
        if await sol_scanner.initialize():
            self.scanners["solana"] = sol_scanner
            logger.info("Solana scanner initialized successfully")
        else:
            logger.error("Failed to initialize Solana scanner")
        
        # Check if at least one scanner was initialized
        if not self.scanners:
            logger.error("No scanners could be initialized")
            return False
        
        logger.info(f"Scanner service initialized with {len(self.scanners)} scanners")
        return True
    
    async def start(self):
        """Start the scanner service."""
        if self.running:
            logger.warning("Scanner service is already running")
            return
        
        # Initialize scanners
        success = await self.initialize()
        if not success:
            logger.error("Failed to initialize scanner service")
            return
        
        self.running = True
        logger.info("Scanner service started")
        
        # Start scanning loop
        while self.running:
            try:
                await self.scan_all_blockchains()
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                logger.info("Scanner service task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scanner service: {str(e)}")
                await asyncio.sleep(self.scan_interval)
    
    async def stop(self):
        """Stop the scanner service."""
        self.running = False
        logger.info("Scanner service stopped")
    
    async def scan_all_blockchains(self):
        """Scan all blockchains for new tokens in parallel."""
        if not self.scanners:
            logger.error("No scanners available")
            return []
        
        # Create tasks for all scanners
        tasks = []
        for blockchain, scanner in self.scanners.items():
            tasks.append(self.scan_blockchain(blockchain))
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        all_tokens = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error scanning blockchain: {str(result)}")
            elif isinstance(result, list):
                all_tokens.extend(result)
        
        logger.info(f"Found {len(all_tokens)} new tokens across all blockchains")
        return all_tokens
    
    async def scan_blockchain(self, blockchain: str) -> List[Dict[str, Any]]:
        """
        Scan a specific blockchain for new tokens.
        
        Args:
            blockchain: The blockchain to scan.
            
        Returns:
            List of new token information dictionaries.
        """
        async with self.scan_semaphore:
            scanner = self.scanners.get(blockchain)
            if not scanner:
                logger.error(f"No scanner available for {blockchain}")
                return []
            
            try:
                logger.info(f"Scanning {blockchain} for new tokens")
                tokens = await scanner.scan_for_new_tokens()
                logger.info(f"Found {len(tokens)} new tokens on {blockchain}")
                return tokens
            except Exception as e:
                logger.error(f"Error scanning {blockchain}: {str(e)}")
                return []
    
    async def get_token_details(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Get detailed information about a token.
        
        Args:
            token_address: The token contract address.
            blockchain: The blockchain the token is on.
            
        Returns:
            Dictionary with token details.
        """
        scanner = self.scanners.get(blockchain)
        if not scanner:
            logger.error(f"No scanner available for {blockchain}")
            return {}
        
        try:
            return await scanner.get_token_details(token_address)
        except Exception as e:
            logger.error(f"Error getting token details for {token_address} on {blockchain}: {str(e)}")
            return {}
    
    async def process_tokens_in_parallel(self, tokens: List[Dict[str, Any]], processor_func) -> List[Dict[str, Any]]:
        """
        Process multiple tokens in parallel with concurrency limit.
        
        Args:
            tokens: List of token information dictionaries.
            processor_func: Function to process each token.
            
        Returns:
            List of processed token information dictionaries.
        """
        if not tokens:
            return []
        
        async def process_with_limit(token):
            async with self.scan_semaphore:
                return await processor_func(token)
        
        # Create tasks for all tokens
        tasks = [process_with_limit(token) for token in tokens]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        processed_tokens = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing token: {str(result)}")
            elif result:
                processed_tokens.append(result)
        
        return processed_tokens

# Singleton instance
scanner_service = ScannerService()
