"""
Token scoring algorithm for the Meme Coin Signal Bot.

This module implements the scoring algorithm for meme coins based on
on-chain metrics and social media sentiment.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import (
    MIN_LIQUIDITY_USD, MIN_HOLDERS, MIN_VOLUME_24H,
    BUY_SELL_RATIO_THRESHOLD
)
from ..database import get_session, Token, SocialMention, Signal, SignalType

# Configure logging
logger = logging.getLogger(__name__)

class TokenScorer:
    """Token scoring algorithm implementation."""
    
    def __init__(self):
        """Initialize the token scorer."""
        pass
    
    async def score_tokens(self):
        """
        Score all tokens in the database and generate signals.
        """
        logger.info("Scoring tokens")
        
        try:
            # Get a database session
            session = next(get_session())
            
            try:
                # Get all tokens
                tokens = session.query(Token).all()
                logger.info(f"Scoring {len(tokens)} tokens")
                
                for token in tokens:
                    # Score the token
                    scores = self._calculate_token_scores(token, session)
                    
                    # Update token scores
                    token.liquidity_score = scores['liquidity_score']
                    token.volume_score = scores['volume_score']
                    token.social_score = scores['social_score']
                    token.safety_score = scores['safety_score']
                    token.total_score = scores['total_score']
                    
                    # Generate signal if score is high enough
                    if scores['total_score'] >= 70:
                        signal_type = SignalType.STRONG_BUY if scores['total_score'] >= 85 else SignalType.BUY
                        await self._generate_signal(token, signal_type, scores, session)
                    
                    # Commit changes
                    session.commit()
                
                logger.info("Token scoring completed")
            
            except Exception as e:
                logger.error(f"Error scoring tokens: {str(e)}")
                session.rollback()
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error in token scoring: {str(e)}")
    
    def _calculate_token_scores(self, token: Token, session: Session) -> Dict[str, float]:
        """
        Calculate scores for a token based on various metrics.
        
        Args:
            token: The token to score.
            session: Database session.
            
        Returns:
            Dictionary containing scores for different metrics and total score.
        """
        # Initialize scores
        scores = {
            'liquidity_score': 0.0,
            'volume_score': 0.0,
            'social_score': 0.0,
            'safety_score': 0.0,
            'total_score': 0.0
        }
        
        # Calculate liquidity score (0-25)
        if token.liquidity_usd >= MIN_LIQUIDITY_USD:
            # Scale logarithmically from MIN_LIQUIDITY_USD to 10x that value
            liquidity_factor = min(1.0, (token.liquidity_usd - MIN_LIQUIDITY_USD) / (9 * MIN_LIQUIDITY_USD))
            scores['liquidity_score'] = 15 + (10 * liquidity_factor)
        else:
            # Scale linearly from 0 to MIN_LIQUIDITY_USD
            liquidity_factor = token.liquidity_usd / MIN_LIQUIDITY_USD
            scores['liquidity_score'] = 15 * liquidity_factor
        
        # Calculate volume score (0-25)
        if token.volume_24h_usd >= MIN_VOLUME_24H:
            # Scale logarithmically from MIN_VOLUME_24H to 10x that value
            volume_factor = min(1.0, (token.volume_24h_usd - MIN_VOLUME_24H) / (9 * MIN_VOLUME_24H))
            scores['volume_score'] = 15 + (10 * volume_factor)
        else:
            # Scale linearly from 0 to MIN_VOLUME_24H
            volume_factor = token.volume_24h_usd / MIN_VOLUME_24H
            scores['volume_score'] = 15 * volume_factor
        
        # Calculate social score (0-25)
        # Count recent social mentions (last 24 hours)
        recent_mentions_count = session.query(func.count(SocialMention.id)).filter(
            SocialMention.token_id == token.id,
            SocialMention.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar()
        
        # Count influencer mentions
        influencer_mentions_count = session.query(func.count(SocialMention.id)).filter(
            SocialMention.token_id == token.id,
            SocialMention.is_influencer == True,
            SocialMention.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar()
        
        # Calculate average sentiment
        avg_sentiment = session.query(func.avg(SocialMention.sentiment_score)).filter(
            SocialMention.token_id == token.id,
            SocialMention.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar() or 0.0
        
        # Calculate social score based on mentions and sentiment
        mention_score = min(15.0, recent_mentions_count * 1.5)
        influencer_score = min(5.0, influencer_mentions_count * 2.5)
        sentiment_score = 5.0 * (avg_sentiment + 1.0) / 2.0  # Scale from [-1, 1] to [0, 5]
        
        scores['social_score'] = mention_score + influencer_score + sentiment_score
        
        # Calculate safety score (0-25)
        # Base score from contract audit
        safety_score = token.contract_audit_score / 4.0  # Scale from [0, 100] to [0, 25]
        
        # Penalize honeypots
        if token.is_honeypot:
            safety_score = 0.0
        
        # Bonus for verified contracts
        if token.contract_verified:
            safety_score = min(25.0, safety_score + 5.0)
        
        # Bonus for good buy/sell ratio
        if token.buy_sell_ratio >= BUY_SELL_RATIO_THRESHOLD:
            safety_score = min(25.0, safety_score + 5.0)
        
        # Bonus for many holders
        if token.holders_count >= MIN_HOLDERS:
            holder_bonus = min(5.0, (token.holders_count - MIN_HOLDERS) / 200)
            safety_score = min(25.0, safety_score + holder_bonus)
        
        scores['safety_score'] = safety_score
        
        # Calculate total score (0-100)
        scores['total_score'] = (
            scores['liquidity_score'] +
            scores['volume_score'] +
            scores['social_score'] +
            scores['safety_score']
        )
        
        return scores
    
    async def _generate_signal(self, token: Token, signal_type: SignalType, scores: Dict[str, float], session: Session):
        """
        Generate a signal for a token.
        
        Args:
            token: The token to generate a signal for.
            signal_type: The type of signal to generate.
            scores: Dictionary containing token scores.
            session: Database session.
        """
        # Check if we already sent a signal for this token recently
        recent_signal = session.query(Signal).filter(
            Signal.token_id == token.id,
            Signal.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if recent_signal:
            logger.info(f"Signal already sent for {token.symbol} in the last 24 hours")
            return
        
        # Generate reason text
        reasons = []
        if scores['liquidity_score'] >= 20:
            reasons.append(f"Strong liquidity (${token.liquidity_usd:.2f})")
        elif scores['liquidity_score'] >= 15:
            reasons.append(f"Good liquidity (${token.liquidity_usd:.2f})")
        
        if scores['volume_score'] >= 20:
            reasons.append(f"High volume (${token.volume_24h_usd:.2f})")
        elif scores['volume_score'] >= 15:
            reasons.append(f"Good volume (${token.volume_24h_usd:.2f})")
        
        if scores['social_score'] >= 20:
            reasons.append("Strong social buzz")
        elif scores['social_score'] >= 15:
            reasons.append("Good social activity")
        
        if scores['safety_score'] >= 20:
            reasons.append("Very safe contract")
        elif scores['safety_score'] >= 15:
            reasons.append("Safe contract")
        
        if token.buy_sell_ratio >= BUY_SELL_RATIO_THRESHOLD:
            reasons.append(f"Positive buy/sell ratio ({token.buy_sell_ratio:.2f})")
        
        reason_text = ", ".join(reasons)
        
        # Count recent social mentions
        social_mentions_count = session.query(func.count(SocialMention.id)).filter(
            SocialMention.token_id == token.id,
            SocialMention.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar()
        
        # Create signal
        signal = Signal(
            token_id=token.id,
            signal_type=signal_type,
            timestamp=datetime.utcnow(),
            score=scores['total_score'],
            reason=reason_text,
            sent_to_telegram=False,
            
            # Snapshot of metrics at signal time
            price_usd=token.current_price_usd,
            liquidity_usd=token.liquidity_usd,
            volume_24h_usd=token.volume_24h_usd,
            holders_count=token.holders_count,
            buy_sell_ratio=token.buy_sell_ratio,
            social_mentions_count=social_mentions_count
        )
        
        # Add to database
        session.add(signal)
        logger.info(f"Generated {signal_type.value} signal for {token.symbol} with score {scores['total_score']:.2f}")

# Singleton instance
token_scorer = TokenScorer()
