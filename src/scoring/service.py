"""
Scoring service coordinator for the Meme Coin Bot.
Manages token scoring and coordinates with other services.
"""
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional

from src.scoring.models import TokenScore
from src.scoring.scorer import token_scorer

# Setup logging
logger = logging.getLogger(__name__)

class ScoringService:
    """Service to coordinate token scoring."""
    
    def __init__(self):
        """Initialize the scoring service."""
        self.running = False
        self.scanner_service = None  # Will be set by main.py
        self.filter_service = None   # Will be set by main.py
        self.signal_service = None   # Will be set by main.py
        self.max_concurrent_scores = int(os.getenv("MAX_CONCURRENT_SCANS", "10"))
    
    async def initialize(self, scanner_service, filter_service, signal_service) -> bool:
        """
        Initialize the scoring service.
        
        Args:
            scanner_service: Scanner service for getting token data.
            filter_service: Filter service for filtering tokens.
            signal_service: Signal service for generating signals.
            
        Returns:
            True if initialization was successful, False otherwise.
        """
        self.scanner_service = scanner_service
        self.filter_service = filter_service
        self.signal_service = signal_service
        logger.info("Scoring service initialized successfully")
        return True
    
    async def start(self):
        """Start the scoring service."""
        if self.running:
            logger.warning("Scoring service is already running")
            return
        
        self.running = True
        logger.info("Scoring service started")
        
        # Start processing loop
        while self.running:
            try:
                await self.process_new_tokens()
                await asyncio.sleep(60)  # Process every minute
            except asyncio.CancelledError:
                logger.info("Scoring service task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scoring service: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def stop(self):
        """Stop the scoring service."""
        self.running = False
        logger.info("Scoring service stopped")
    
    async def process_new_tokens(self):
        """Process new tokens from scanner service."""
        if not self.running:
            logger.warning("Scoring service is not running")
            return
        
        if not self.scanner_service:
            logger.error("Scanner service not initialized")
            return
        
        try:
            # Scan for new tokens
            tokens = await self.scanner_service.scan_all_blockchains()
            
            if not tokens:
                logger.info("No new tokens found")
                return
            
            logger.info(f"Processing {len(tokens)} new tokens")
            
            # Filter tokens
            if self.filter_service:
                tokens = await self.filter_service.apply_filters_in_parallel(tokens, self.max_concurrent_scores)
            
            if not tokens:
                logger.info("No tokens passed filters")
                return
            
            # Score tokens
            scores = await self.score_tokens_in_parallel(tokens)
            
            # Generate signals
            if self.signal_service:
                signals = await self.signal_service.process_tokens(tokens, scores)
                logger.info(f"Generated {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"Error processing new tokens: {str(e)}")
    
    async def score_token(self, token: Dict[str, Any]) -> Dict[str, float]:
        """
        Score a token based on its metrics.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            Dictionary of scores.
        """
        try:
            # Score token
            score = token_scorer.score_token(token)
            
            # Return scores as dictionary
            return {
                score.token_address: score.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error scoring token {token.get('address')}: {str(e)}")
            return {}
    
    async def score_tokens_in_parallel(self, tokens: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Score multiple tokens in parallel.
        
        Args:
            tokens: List of token information dictionaries.
            
        Returns:
            Dictionary mapping token addresses to score dictionaries.
        """
        if not tokens:
            return {}
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_scores)
        
        async def score_with_limit(token):
            async with semaphore:
                return await self.score_token(token)
        
        # Create tasks for all tokens
        tasks = [score_with_limit(token) for token in tokens]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_scores = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error scoring token: {str(result)}")
            elif result:
                all_scores.update(result)
        
        return all_scores

# Singleton instance
scoring_service = ScoringService()
