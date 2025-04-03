"""
Scoring models for the Meme Coin Bot.
"""
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class ScoringWeights:
    """Weights for different scoring factors."""
    
    volume_weight: float = 0.25
    liquidity_weight: float = 0.20
    holder_weight: float = 0.15
    momentum_weight: float = 0.25
    safety_weight: float = 0.15
    
    def __post_init__(self):
        """Validate that weights sum to 1.0."""
        total = (self.volume_weight + self.liquidity_weight + 
                self.holder_weight + self.momentum_weight + 
                self.safety_weight)
        
        if abs(total - 1.0) > 0.001:
            logger.warning(f"Scoring weights do not sum to 1.0: {total}")
            # Normalize weights
            factor = 1.0 / total
            self.volume_weight *= factor
            self.liquidity_weight *= factor
            self.holder_weight *= factor
            self.momentum_weight *= factor
            self.safety_weight *= factor

@dataclass
class ScoringThresholds:
    """Thresholds for different scoring factors."""
    
    # Volume thresholds in USD
    min_volume: float = 1000.0
    max_volume: float = 1000000.0
    
    # Liquidity thresholds in USD
    min_liquidity: float = 10000.0
    max_liquidity: float = 1000000.0
    
    # Holder count thresholds
    min_holders: int = 50
    max_holders: int = 5000
    
    # Buy/sell ratio thresholds
    min_buy_sell_ratio: float = 0.5
    max_buy_sell_ratio: float = 3.0
    
    # LP lock thresholds (percentage of liquidity locked)
    min_lp_lock_percent: float = 0.0
    max_lp_lock_percent: float = 100.0
    
    # Safety thresholds
    min_safety_score: float = 0.0
    max_safety_score: float = 100.0

@dataclass
class TokenScore:
    """Token score data model."""
    
    token_address: str
    total_score: float
    volume_score: float
    liquidity_score: float
    holder_score: float
    momentum_score: float
    safety_score: float
    
    def to_dict(self) -> Dict[str, float]:
        """
        Convert score to dictionary.
        
        Returns:
            Dictionary representation of the score.
        """
        return {
            "total": self.total_score,
            "volume": self.volume_score,
            "liquidity": self.liquidity_score,
            "holder": self.holder_score,
            "momentum": self.momentum_score,
            "safety": self.safety_score
        }
