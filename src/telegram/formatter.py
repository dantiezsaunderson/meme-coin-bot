"""
Message formatter for Telegram signals.
"""
import logging
from typing import Dict, Any

from src.signals.models import Signal

# Setup logging
logger = logging.getLogger(__name__)

class MessageFormatter:
    """Formatter for Telegram messages."""
    
    @staticmethod
    def format_signal(signal: Signal) -> str:
        """
        Format a signal for Telegram.
        
        Args:
            signal: Signal to format.
            
        Returns:
            Formatted message.
        """
        emoji = "🚀" if signal.signal_type == "buy" else "⚠️" if signal.signal_type == "sell" else "👀"
        blockchain_emoji = "🔷" if signal.blockchain == "ethereum" else "☀️" if signal.blockchain == "solana" else "🔗"
        
        message = f"{emoji} {signal.signal_type.upper()} SIGNAL {emoji}\n\n"
        message += f"{blockchain_emoji} {signal.blockchain.upper()}: {signal.name} ({signal.symbol})\n"
        message += f"💰 Price: ${signal.price_usd:.6f}\n"
        message += f"💧 Liquidity: ${signal.liquidity_usd:,.2f}\n"
        message += f"📊 Volume 24h: ${signal.volume_24h_usd:,.2f}\n"
        message += f"👥 Holders: {signal.holders_count:,}\n"
        message += f"📈 Buy/Sell Ratio: {signal.buy_sell_ratio:.2f}\n\n"
        message += f"🔢 Total Score: {signal.total_score:.2f}/100\n"
        message += f"Contract: `{signal.token_address}`\n\n"
        
        if signal.blockchain == "ethereum":
            message += f"🔍 [Etherscan](https://etherscan.io/token/{signal.token_address})\n"
            message += f"📊 [Dextools](https://www.dextools.io/app/ether/pair-explorer/{signal.token_address})\n"
        elif signal.blockchain == "solana":
            message += f"🔍 [Solscan](https://solscan.io/token/{signal.token_address})\n"
            message += f"📊 [Birdeye](https://birdeye.so/token/{signal.token_address}?chain=solana)\n"
        
        return message
    
    @staticmethod
    def format_error(error_message: str) -> str:
        """
        Format an error message for Telegram.
        
        Args:
            error_message: Error message.
            
        Returns:
            Formatted message.
        """
        return f"⚠️ ERROR ⚠️\n\n{error_message}"
    
    @staticmethod
    def format_status(status: Dict[str, Any]) -> str:
        """
        Format a status message for Telegram.
        
        Args:
            status: Status information.
            
        Returns:
            Formatted message.
        """
        message = "📊 SYSTEM STATUS 📊\n\n"
        
        # Overall status
        overall_status = status.get("status", "unknown")
        if overall_status == "healthy":
            message += "✅ System is healthy\n\n"
        elif overall_status == "degraded":
            message += "⚠️ System is degraded\n\n"
        else:
            message += "❌ System is unhealthy\n\n"
        
        # Component status
        components = status.get("components", {})
        message += "Component Status:\n"
        for component, component_status in components.items():
            if "healthy" in component_status:
                message += f"✅ {component}: {component_status}\n"
            else:
                message += f"❌ {component}: {component_status}\n"
        
        # System metrics
        system = status.get("system", {})
        message += "\nSystem Metrics:\n"
        message += f"CPU Usage: {system.get('cpu_usage', 'N/A')}%\n"
        message += f"Memory Usage: {system.get('memory_usage', 'N/A')}%\n"
        message += f"Uptime: {system.get('uptime_seconds', 'N/A')} seconds\n"
        
        return message

# Singleton instance
message_formatter = MessageFormatter()
