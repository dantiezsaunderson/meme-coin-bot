"""
Token scoring service for the Meme Coin Signal Bot.

This module provides a service that periodically scores tokens and generates signals.
"""
import asyncio
import logging
from datetime import datetime

from ..config import SCORING_INTERVAL
from .scorer import token_scorer

# Configure logging
logger = logging.getLogger(__name__)

class ScoringService:
    """Service for scoring tokens and generating signals."""
    
    def __init__(self):
        """Initialize the scoring service."""
        self.running = False
    
    async def start(self):
        """Start the scoring service."""
        self.running = True
        logger.info("Starting token scoring service")
        
        while self.running:
            try:
                # Score tokens
                await token_scorer.score_tokens()
                
                # Wait for next scoring interval
                logger.info(f"Token scoring completed. Next scoring in {SCORING_INTERVAL} seconds")
                await asyncio.sleep(SCORING_INTERVAL)
            
            except Exception as e:
                logger.error(f"Error in token scoring service: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def stop(self):
        """Stop the scoring service."""
        self.running = False
        logger.info("Stopping token scoring service")

# Singleton instance
scoring_service = ScoringService()
