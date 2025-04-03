"""
Signal generator for the Meme Coin Bot.
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

from src.signals.models import Signal

# Setup logging
logger = logging.getLogger(__name__)

# Signal configuration
MINIMUM_TOTAL_SCORE = float(os.getenv("MINIMUM_TOTAL_SCORE", "70"))
SIGNAL_COOLDOWN_MINUTES = int(os.getenv("SIGNAL_COOLDOWN_MINUTES", "30"))
MAX_SIGNALS_PER_HOUR = int(os.getenv("MAX_SIGNALS_PER_HOUR", "5"))

class SignalGenerator:
    """Generator for token signals."""
    
    def __init__(self):
        """Initialize the signal generator."""
        self.recent_signals = {}  # token_address -> timestamp
        self.signal_count_last_hour = 0
        self.last_signal_time = datetime.min
    
    def can_generate_signal(self, token_address: str) -> bool:
        """
        Check if a signal can be generated for a token.
        
        Args:
            token_address: The token address.
            
        Returns:
            True if a signal can be generated, False otherwise.
        """
        # Check if token has been signaled recently
        if token_address in self.recent_signals:
            last_signal_time = self.recent_signals[token_address]
            cooldown_period = timedelta(minutes=SIGNAL_COOLDOWN_MINUTES)
            if datetime.utcnow() - last_signal_time < cooldown_period:
                logger.info(f"Token {token_address} is in cooldown period")
                return False
        
        # Check if we've reached the maximum signals per hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        if self.last_signal_time > one_hour_ago:
            if self.signal_count_last_hour >= MAX_SIGNALS_PER_HOUR:
                logger.info(f"Maximum signals per hour ({MAX_SIGNALS_PER_HOUR}) reached")
                return False
        else:
            # Reset counter if last signal was more than an hour ago
            self.signal_count_last_hour = 0
        
        return True
    
    def record_signal(self, token_address: str):
        """
        Record that a signal was generated for a token.
        
        Args:
            token_address: The token address.
        """
        self.recent_signals[token_address] = datetime.utcnow()
        self.last_signal_time = datetime.utcnow()
        self.signal_count_last_hour += 1
        
        # Clean up old signals
        self._cleanup_old_signals()
    
    def _cleanup_old_signals(self):
        """Clean up old signals from the recent signals dictionary."""
        cooldown_period = timedelta(minutes=SIGNAL_COOLDOWN_MINUTES)
        current_time = datetime.utcnow()
        
        # Remove signals that are past the cooldown period
        self.recent_signals = {
            addr: time for addr, time in self.recent_signals.items()
            if current_time - time < cooldown_period
        }
    
    async def generate_signals(self, tokens: List[Dict[str, Any]], scores: Dict[str, Dict[str, float]]) -> List[Signal]:
        """
        Generate signals for tokens.
        
        Args:
            tokens: List of token information dictionaries.
            scores: Dictionary mapping token addresses to score dictionaries.
            
        Returns:
            List of generated signals.
        """
        signals = []
        
        for token in tokens:
            token_address = token.get("address")
            if not token_address:
                continue
            
            # Get scores for token
            token_scores = scores.get(token_address, {})
            total_score = token_scores.get("total", 0.0)
            
            # Check if token meets minimum score threshold
            if total_score < MINIMUM_TOTAL_SCORE:
                logger.info(f"Token {token.get('symbol')} ({token_address}) score {total_score} below threshold {MINIMUM_TOTAL_SCORE}")
                continue
            
            # Check if we can generate a signal for this token
            if not self.can_generate_signal(token_address):
                continue
            
            # Determine signal type based on scores
            signal_type = self._determine_signal_type(token_scores)
            
            # Create signal
            signal = Signal.from_token(token, token_scores, signal_type)
            signals.append(signal)
            
            # Record that we generated a signal
            self.record_signal(token_address)
            
            logger.info(f"Generated {signal_type} signal for {token.get('symbol')} ({token_address}) with score {total_score}")
        
        return signals
    
    def _determine_signal_type(self, scores: Dict[str, float]) -> str:
        """
        Determine the signal type based on scores.
        
        Args:
            scores: Dictionary of scores.
            
        Returns:
            Signal type.
        """
        total_score = scores.get("total", 0.0)
        
        # Simple logic for now - can be enhanced with more sophisticated rules
        if total_score >= 90:
            return "buy"
        elif total_score >= 70:
            return "watch"
        else:
            return "ignore"  # This should not happen due to minimum score threshold

# Singleton instance
signal_generator = SignalGenerator()
