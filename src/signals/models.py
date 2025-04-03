"""
Signal models for the Meme Coin Bot.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """Signal data model."""
    
    token_address: str
    blockchain: str
    name: str
    symbol: str
    price_usd: float
    volume_24h_usd: float
    liquidity_usd: float
    holders_count: int
    buy_sell_ratio: float
    total_score: float
    volume_score: float
    liquidity_score: float
    holder_score: float
    momentum_score: float
    safety_score: float
    signal_type: str  # "buy", "sell", "watch"
    timestamp: datetime
    extra_data: Dict[str, Any]
    
    @classmethod
    def from_token(cls, token: Dict[str, Any], scores: Dict[str, float], signal_type: str) -> 'Signal':
        """
        Create a signal from a token and scores.
        
        Args:
            token: Token information dictionary.
            scores: Dictionary of scores.
            signal_type: Signal type.
            
        Returns:
            Signal instance.
        """
        return cls(
            token_address=token.get("address", ""),
            blockchain=token.get("blockchain", ""),
            name=token.get("name", ""),
            symbol=token.get("symbol", ""),
            price_usd=token.get("price_usd", 0.0),
            volume_24h_usd=token.get("volume_24h_usd", 0.0),
            liquidity_usd=token.get("liquidity_usd", 0.0),
            holders_count=token.get("holders_count", 0),
            buy_sell_ratio=token.get("buy_sell_ratio", 1.0),
            total_score=scores.get("total", 0.0),
            volume_score=scores.get("volume", 0.0),
            liquidity_score=scores.get("liquidity", 0.0),
            holder_score=scores.get("holder", 0.0),
            momentum_score=scores.get("momentum", 0.0),
            safety_score=scores.get("safety", 0.0),
            signal_type=signal_type,
            timestamp=datetime.utcnow(),
            extra_data={}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert signal to dictionary.
        
        Returns:
            Dictionary representation of the signal.
        """
        return {
            "token_address": self.token_address,
            "blockchain": self.blockchain,
            "name": self.name,
            "symbol": self.symbol,
            "price_usd": self.price_usd,
            "volume_24h_usd": self.volume_24h_usd,
            "liquidity_usd": self.liquidity_usd,
            "holders_count": self.holders_count,
            "buy_sell_ratio": self.buy_sell_ratio,
            "total_score": self.total_score,
            "volume_score": self.volume_score,
            "liquidity_score": self.liquidity_score,
            "holder_score": self.holder_score,
            "momentum_score": self.momentum_score,
            "safety_score": self.safety_score,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp.isoformat(),
            "extra_data": self.extra_data
        }
    
    def get_message(self) -> str:
        """
        Get a formatted message for the signal.
        
        Returns:
            Formatted message.
        """
        emoji = "🚀" if self.signal_type == "buy" else "⚠️" if self.signal_type == "sell" else "👀"
        blockchain_emoji = "🔷" if self.blockchain == "ethereum" else "☀️" if self.blockchain == "solana" else "🔗"
        
        message = f"{emoji} {self.signal_type.upper()} SIGNAL {emoji}\n\n"
        message += f"{blockchain_emoji} {self.blockchain.upper()}: {self.name} ({self.symbol})\n"
        message += f"💰 Price: ${self.price_usd:.6f}\n"
        message += f"💧 Liquidity: ${self.liquidity_usd:,.2f}\n"
        message += f"📊 Volume 24h: ${self.volume_24h_usd:,.2f}\n"
        message += f"👥 Holders: {self.holders_count:,}\n"
        message += f"📈 Buy/Sell Ratio: {self.buy_sell_ratio:.2f}\n\n"
        message += f"🔢 Total Score: {self.total_score:.2f}/100\n"
        message += f"Contract: `{self.token_address}`\n\n"
        
        if self.blockchain == "ethereum":
            message += f"🔍 [Etherscan](https://etherscan.io/token/{self.token_address})\n"
            message += f"📊 [Dextools](https://www.dextools.io/app/ether/pair-explorer/{self.token_address})\n"
        elif self.blockchain == "solana":
            message += f"🔍 [Solscan](https://solscan.io/token/{self.token_address})\n"
            message += f"📊 [Birdeye](https://birdeye.so/token/{self.token_address}?chain=solana)\n"
        
        return message
