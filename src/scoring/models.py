"""
Pydantic models for API responses in the Meme Coin Signal Bot.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TokenScore(BaseModel):
    """Basic token score model for API responses."""
    id: int
    symbol: str
    name: Optional[str] = None
    blockchain: str
    price_usd: float
    volume_24h_usd: float
    liquidity_usd: float
    total_score: float

class TokenDetail(BaseModel):
    """Detailed token model for API responses."""
    id: int
    address: str
    name: Optional[str] = None
    symbol: str
    blockchain: str
    created_at: datetime
    updated_at: datetime
    
    # Contract details
    contract_verified: bool
    is_honeypot: bool
    contract_audit_score: float
    
    # Token metrics
    current_price_usd: float
    market_cap_usd: float
    liquidity_usd: float
    volume_24h_usd: float
    holders_count: int
    buy_sell_ratio: float
    
    # Scoring
    total_score: float
    liquidity_score: float
    volume_score: float
    social_score: float
    safety_score: float

class SocialMentionResponse(BaseModel):
    """Social mention model for API responses."""
    id: int
    source: str
    author: Optional[str] = None
    is_influencer: bool
    content: Optional[str] = None
    url: Optional[str] = None
    timestamp: datetime
    sentiment_score: float

class SignalResponse(BaseModel):
    """Signal model for API responses."""
    id: int
    token_id: int
    token_symbol: str
    signal_type: str
    timestamp: datetime
    score: float
    reason: Optional[str] = None
    
    # Snapshot of metrics at signal time
    price_usd: float
    liquidity_usd: float
    volume_24h_usd: float
    holders_count: int
    buy_sell_ratio: float
    social_mentions_count: int
