"""
FastAPI API endpoints for the Meme Coin Signal Bot.

This module defines the API endpoints for the web service.
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_session, Token, Signal, SocialMention, SignalType
from ..scoring.models import TokenScore, TokenDetail

# Create FastAPI app
app = FastAPI(
    title="Meme Coin Signal Bot API",
    description="API for the Meme Coin Signal Bot",
    version="1.0.0",
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Meme Coin Signal Bot API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Token endpoints
@app.get("/tokens", response_model=List[TokenDetail])
async def get_tokens(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    min_score: Optional[float] = None,
    blockchain: Optional[str] = None,
):
    """Get a list of tokens."""
    query = session.query(Token)
    
    if min_score is not None:
        query = query.filter(Token.total_score >= min_score)
    
    if blockchain is not None:
        query = query.filter(Token.blockchain == blockchain)
    
    tokens = query.order_by(Token.total_score.desc()).offset(skip).limit(limit).all()
    return tokens

@app.get("/tokens/{token_id}", response_model=TokenDetail)
async def get_token(token_id: int, session: Session = Depends(get_session)):
    """Get a token by ID."""
    token = session.query(Token).filter(Token.id == token_id).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    return token

# Signal endpoints
@app.get("/signals", response_model=List[Signal])
async def get_signals(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 20,
    signal_type: Optional[str] = None,
    days: Optional[int] = 1,
):
    """Get a list of signals."""
    query = session.query(Signal)
    
    if signal_type is not None:
        query = query.filter(Signal.signal_type == signal_type)
    
    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Signal.timestamp >= cutoff_date)
    
    signals = query.order_by(Signal.timestamp.desc()).offset(skip).limit(limit).all()
    return signals

@app.get("/trending", response_model=List[TokenScore])
async def get_trending(
    session: Session = Depends(get_session),
    limit: int = 10,
    hours: int = 24,
):
    """Get trending tokens based on social mentions and volume."""
    cutoff_date = datetime.utcnow() - timedelta(hours=hours)
    
    # Get tokens with recent social mentions
    social_counts = (
        session.query(
            SocialMention.token_id,
            func.count(SocialMention.id).label("mention_count")
        )
        .filter(SocialMention.timestamp >= cutoff_date)
        .group_by(SocialMention.token_id)
        .subquery()
    )
    
    # Join with tokens and order by score
    tokens = (
        session.query(Token)
        .join(social_counts, Token.id == social_counts.c.token_id, isouter=True)
        .order_by(
            Token.total_score.desc(),
            social_counts.c.mention_count.desc().nullslast(),
            Token.volume_24h_usd.desc()
        )
        .limit(limit)
        .all()
    )
    
    return [
        TokenScore(
            id=token.id,
            symbol=token.symbol,
            name=token.name,
            blockchain=token.blockchain.value,
            price_usd=token.current_price_usd,
            volume_24h_usd=token.volume_24h_usd,
            liquidity_usd=token.liquidity_usd,
            total_score=token.total_score,
        )
        for token in tokens
    ]

# Stats endpoint
@app.get("/stats")
async def get_stats(session: Session = Depends(get_session)):
    """Get current market stats."""
    # Count tokens by blockchain
    eth_count = session.query(Token).filter(Token.blockchain == "ethereum").count()
    sol_count = session.query(Token).filter(Token.blockchain == "solana").count()
    
    # Get signal counts for today
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    buy_signals = (
        session.query(Signal)
        .filter(Signal.timestamp >= today_start)
        .filter(Signal.signal_type.in_([SignalType.BUY, SignalType.STRONG_BUY]))
        .count()
    )
    
    # Get average metrics
    avg_liquidity = session.query(func.avg(Token.liquidity_usd)).scalar() or 0
    avg_volume = session.query(func.avg(Token.volume_24h_usd)).scalar() or 0
    
    return {
        "token_count": {
            "ethereum": eth_count,
            "solana": sol_count,
            "total": eth_count + sol_count,
        },
        "signals_today": buy_signals,
        "avg_liquidity_usd": round(avg_liquidity, 2),
        "avg_volume_24h_usd": round(avg_volume, 2),
        "timestamp": datetime.utcnow().isoformat(),
    }
