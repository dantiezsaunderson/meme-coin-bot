"""
Token scorer implementation for the Meme Coin Bot.
"""
import logging
import math
from typing import Dict, Any, List, Optional

from src.scoring.models import ScoringWeights, ScoringThresholds, TokenScore

# Setup logging
logger = logging.getLogger(__name__)

class TokenScorer:
    """Scorer for token metrics."""
    
    def __init__(self, weights: Optional[ScoringWeights] = None, thresholds: Optional[ScoringThresholds] = None):
        """
        Initialize the token scorer.
        
        Args:
            weights: Scoring weights.
            thresholds: Scoring thresholds.
        """
        self.weights = weights or ScoringWeights()
        self.thresholds = thresholds or ScoringThresholds()
    
    def score_token(self, token: Dict[str, Any]) -> TokenScore:
        """
        Score a token based on its metrics.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            TokenScore instance.
        """
        token_address = token.get("address", "")
        
        # Calculate individual scores
        volume_score = self._score_volume(token)
        liquidity_score = self._score_liquidity(token)
        holder_score = self._score_holders(token)
        momentum_score = self._score_momentum(token)
        safety_score = self._score_safety(token)
        
        # Calculate weighted total score
        total_score = (
            volume_score * self.weights.volume_weight +
            liquidity_score * self.weights.liquidity_weight +
            holder_score * self.weights.holder_weight +
            momentum_score * self.weights.momentum_weight +
            safety_score * self.weights.safety_weight
        ) * 100  # Scale to 0-100
        
        # Create and return score object
        return TokenScore(
            token_address=token_address,
            total_score=total_score,
            volume_score=volume_score * 100,
            liquidity_score=liquidity_score * 100,
            holder_score=holder_score * 100,
            momentum_score=momentum_score * 100,
            safety_score=safety_score * 100
        )
    
    def _score_volume(self, token: Dict[str, Any]) -> float:
        """
        Score token volume.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            Volume score (0.0-1.0).
        """
        volume = token.get("volume_24h_usd", 0.0)
        
        # Apply logarithmic scaling for volume
        if volume <= 0:
            return 0.0
        
        log_min = math.log10(max(1.0, self.thresholds.min_volume))
        log_max = math.log10(self.thresholds.max_volume)
        log_volume = math.log10(max(1.0, volume))
        
        # Normalize to 0.0-1.0 range
        normalized_score = (log_volume - log_min) / (log_max - log_min)
        
        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, normalized_score))
    
    def _score_liquidity(self, token: Dict[str, Any]) -> float:
        """
        Score token liquidity.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            Liquidity score (0.0-1.0).
        """
        liquidity = token.get("liquidity_usd", 0.0)
        
        # Apply logarithmic scaling for liquidity
        if liquidity <= 0:
            return 0.0
        
        log_min = math.log10(max(1.0, self.thresholds.min_liquidity))
        log_max = math.log10(self.thresholds.max_liquidity)
        log_liquidity = math.log10(max(1.0, liquidity))
        
        # Normalize to 0.0-1.0 range
        normalized_score = (log_liquidity - log_min) / (log_max - log_min)
        
        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, normalized_score))
    
    def _score_holders(self, token: Dict[str, Any]) -> float:
        """
        Score token holder count.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            Holder score (0.0-1.0).
        """
        holders = token.get("holders_count", 0)
        
        # Apply logarithmic scaling for holders
        if holders <= 0:
            return 0.0
        
        log_min = math.log10(max(1.0, self.thresholds.min_holders))
        log_max = math.log10(self.thresholds.max_holders)
        log_holders = math.log10(max(1.0, holders))
        
        # Normalize to 0.0-1.0 range
        normalized_score = (log_holders - log_min) / (log_max - log_min)
        
        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, normalized_score))
    
    def _score_momentum(self, token: Dict[str, Any]) -> float:
        """
        Score token momentum (buy/sell ratio and volume growth).
        
        Args:
            token: Token information dictionary.
            
        Returns:
            Momentum score (0.0-1.0).
        """
        buy_sell_ratio = token.get("buy_sell_ratio", 1.0)
        
        # Normalize buy/sell ratio to 0.0-1.0 range
        # A ratio of 1.0 (equal buys and sells) should score around 0.5
        # Higher ratios (more buys) score higher, lower ratios (more sells) score lower
        
        if buy_sell_ratio <= self.thresholds.min_buy_sell_ratio:
            ratio_score = 0.0
        elif buy_sell_ratio >= self.thresholds.max_buy_sell_ratio:
            ratio_score = 1.0
        else:
            # Linear interpolation between min and max
            ratio_score = (buy_sell_ratio - self.thresholds.min_buy_sell_ratio) / (
                self.thresholds.max_buy_sell_ratio - self.thresholds.min_buy_sell_ratio
            )
        
        # For now, momentum score is just based on buy/sell ratio
        # In a more advanced implementation, we would also consider volume growth
        return ratio_score
    
    def _score_safety(self, token: Dict[str, Any]) -> float:
        """
        Score token safety.
        
        Args:
            token: Token information dictionary.
            
        Returns:
            Safety score (0.0-1.0).
        """
        safety_info = token.get("safety", {})
        
        # If token is marked as unsafe, return 0.0
        if not safety_info.get("is_safe", True):
            return 0.0
        
        # Check risk level
        risk_level = safety_info.get("risk_level", "unknown")
        if risk_level == "high":
            return 0.2
        elif risk_level == "medium":
            return 0.5
        elif risk_level == "low":
            return 0.8
        elif risk_level == "very_low":
            return 1.0
        else:  # unknown
            return 0.3
        
        # In a more advanced implementation, we would consider more factors:
        # - Contract verification status
        # - LP lock status and duration
        # - Contract audit results
        # - Token age
        # - Developer reputation
        # - etc.

# Singleton instance
token_scorer = TokenScorer()
