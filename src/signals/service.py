"""
Signal service coordinator for the Meme Coin Bot.
Manages signal generation and delivery.
"""
import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.signals.generator import signal_generator
from src.signals.models import Signal

# Setup logging
logger = logging.getLogger(__name__)

class SignalService:
    """Service to coordinate signal generation and delivery."""
    
    def __init__(self):
        """Initialize the signal service."""
        self.running = False
        self.telegram_service = None  # Will be set by main.py
    
    async def initialize(self, telegram_service) -> bool:
        """
        Initialize the signal service.
        
        Args:
            telegram_service: Telegram service for sending signals.
            
        Returns:
            True if initialization was successful, False otherwise.
        """
        self.telegram_service = telegram_service
        logger.info("Signal service initialized successfully")
        return True
    
    async def start(self):
        """Start the signal service."""
        if self.running:
            logger.warning("Signal service is already running")
            return
        
        self.running = True
        logger.info("Signal service started")
    
    async def stop(self):
        """Stop the signal service."""
        self.running = False
        logger.info("Signal service stopped")
    
    async def process_tokens(self, tokens: List[Dict[str, Any]], scores: Dict[str, Dict[str, float]]) -> List[Signal]:
        """
        Process tokens and generate signals.
        
        Args:
            tokens: List of token information dictionaries.
            scores: Dictionary mapping token addresses to score dictionaries.
            
        Returns:
            List of generated signals.
        """
        if not self.running:
            logger.warning("Signal service is not running")
            return []
        
        try:
            # Generate signals
            signals = await signal_generator.generate_signals(tokens, scores)
            
            # Send signals to Telegram
            if signals and self.telegram_service:
                for signal in signals:
                    await self.telegram_service.send_signal(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error processing tokens for signals: {str(e)}")
            return []
    
    async def process_tokens_in_parallel(self, tokens: List[Dict[str, Any]], scores: Dict[str, Dict[str, float]], max_concurrency: int = 10) -> List[Signal]:
        """
        Process tokens and generate signals in parallel.
        
        Args:
            tokens: List of token information dictionaries.
            scores: Dictionary mapping token addresses to score dictionaries.
            max_concurrency: Maximum number of tokens to process in parallel.
            
        Returns:
            List of generated signals.
        """
        if not self.running:
            logger.warning("Signal service is not running")
            return []
        
        if not tokens:
            return []
        
        try:
            # Generate signals
            signals = await signal_generator.generate_signals(tokens, scores)
            
            # Send signals to Telegram in parallel
            if signals and self.telegram_service:
                # Create semaphore to limit concurrency
                semaphore = asyncio.Semaphore(max_concurrency)
                
                async def send_with_limit(signal):
                    async with semaphore:
                        await self.telegram_service.send_signal(signal)
                        return signal
                
                # Create tasks for all signals
                tasks = [send_with_limit(signal) for signal in signals]
                
                # Wait for all tasks to complete
                await asyncio.gather(*tasks, return_exceptions=True)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error processing tokens for signals in parallel: {str(e)}")
            return []

# Singleton instance
signal_service = SignalService()
