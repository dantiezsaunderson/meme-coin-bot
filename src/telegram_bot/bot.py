"""
Telegram bot interface for the Meme Coin Signal Bot.

This module implements the Telegram bot that sends signals and handles commands.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
from sqlalchemy import func, desc

from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, DAILY_REPORT_TIME
from ..database import get_session, Token, Signal, SignalType

# Configure logging
logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot implementation."""
    
    def __init__(self):
        """Initialize the Telegram bot."""
        self.application = None
        self.running = False
    
    async def start(self):
        """Start the Telegram bot."""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("Telegram bot token not set")
            return
        
        self.running = True
        logger.info("Starting Telegram bot")
        
        # Create the Application
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("stats", self._stats_command))
        self.application.add_handler(CommandHandler("trending", self._trending_command))
        self.application.add_handler(CommandHandler("top5today", self._top5today_command))
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        
        # Start signal monitoring
        asyncio.create_task(self._monitor_signals())
        
        # Start daily report scheduler
        asyncio.create_task(self._schedule_daily_report())
        
        logger.info("Telegram bot started")
    
    async def stop(self):
        """Stop the Telegram bot."""
        self.running = False
        logger.info("Stopping Telegram bot")
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        await update.message.reply_text(
            "👋 Welcome to the Meme Coin Signal Bot!\n\n"
            "I'll send you high-potential meme coin buy signals based on on-chain metrics and influencer sentiment.\n\n"
            "Available commands:\n"
            "/stats - Show current market stats\n"
            "/trending - Show trending meme coins\n"
            "/top5today - Show today's best signals\n"
            "/help - Show help message"
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        await update.message.reply_text(
            "📚 Meme Coin Signal Bot Help\n\n"
            "This bot scans Ethereum and Solana chains for new meme coins and sends buy signals based on:\n"
            "• Token liquidity (min $10K)\n"
            "• 24h volume\n"
            "• Buy/sell ratio\n"
            "• Number of holders\n"
            "• Smart contract safety\n"
            "• Social media mentions\n\n"
            "Available commands:\n"
            "/stats - Show current market stats\n"
            "/trending - Show trending meme coins\n"
            "/top5today - Show today's best signals\n"
            "/help - Show this help message"
        )
    
    async def _stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stats command."""
        try:
            # Get a database session
            session = next(get_session())
            
            try:
                # Count tokens by blockchain
                eth_count = session.query(func.count(Token.id)).filter(Token.blockchain == "ethereum").scalar() or 0
                sol_count = session.query(func.count(Token.id)).filter(Token.blockchain == "solana").scalar() or 0
                total_count = eth_count + sol_count
                
                # Get signal counts for today
                today = datetime.utcnow().date()
                today_start = datetime.combine(today, datetime.min.time())
                
                buy_signals = session.query(func.count(Signal.id)).filter(
                    Signal.timestamp >= today_start,
                    Signal.signal_type.in_([SignalType.BUY, SignalType.STRONG_BUY])
                ).scalar() or 0
                
                # Get average metrics
                avg_liquidity = session.query(func.avg(Token.liquidity_usd)).scalar() or 0
                avg_volume = session.query(func.avg(Token.volume_24h_usd)).scalar() or 0
                
                # Get top token by score
                top_token = session.query(Token).order_by(Token.total_score.desc()).first()
                top_token_info = f"🏆 Top token: {top_token.symbol} (Score: {top_token.total_score:.1f})" if top_token else ""
                
                # Format stats message
                stats_message = (
                    "📊 Current Market Stats\n\n"
                    f"Tokens tracked: {total_count} ({eth_count} ETH, {sol_count} SOL)\n"
                    f"Buy signals today: {buy_signals}\n"
                    f"Avg. liquidity: ${avg_liquidity:,.2f}\n"
                    f"Avg. 24h volume: ${avg_volume:,.2f}\n\n"
                    f"{top_token_info}"
                )
                
                await update.message.reply_text(stats_message)
            
            except Exception as e:
                logger.error(f"Error getting stats: {str(e)}")
                await update.message.reply_text("Error getting stats. Please try again later.")
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error in stats command: {str(e)}")
            await update.message.reply_text("An error occurred. Please try again later.")
    
    async def _trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /trending command."""
        try:
            # Get a database session
            session = next(get_session())
            
            try:
                # Get trending tokens (high score + recent social mentions)
                trending_tokens = session.query(Token).order_by(
                    Token.total_score.desc()
                ).limit(5).all()
                
                if not trending_tokens:
                    await update.message.reply_text("No trending tokens found.")
                    return
                
                # Format trending message
                trending_message = "🔥 Trending Meme Coins\n\n"
                
                for i, token in enumerate(trending_tokens, 1):
                    # Get recent social mentions count
                    recent_mentions = session.query(func.count(Signal.id)).filter(
                        Signal.token_id == token.id,
                        Signal.timestamp >= datetime.utcnow() - timedelta(hours=24)
                    ).scalar() or 0
                    
                    # Format token info
                    trending_message += (
                        f"{i}. {token.symbol} ({token.blockchain})\n"
                        f"   Price: ${token.current_price_usd:.8f}\n"
                        f"   Score: {token.total_score:.1f}/100\n"
                        f"   24h Volume: ${token.volume_24h_usd:,.2f}\n"
                        f"   Social mentions: {recent_mentions}\n\n"
                    )
                
                await update.message.reply_text(trending_message)
            
            except Exception as e:
                logger.error(f"Error getting trending tokens: {str(e)}")
                await update.message.reply_text("Error getting trending tokens. Please try again later.")
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error in trending command: {str(e)}")
            await update.message.reply_text("An error occurred. Please try again later.")
    
    async def _top5today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /top5today command."""
        try:
            # Get a database session
            session = next(get_session())
            
            try:
                # Get today's date
                today = datetime.utcnow().date()
                today_start = datetime.combine(today, datetime.min.time())
                
                # Get top 5 signals from today
                top_signals = session.query(Signal).filter(
                    Signal.timestamp >= today_start,
                    Signal.signal_type.in_([SignalType.BUY, SignalType.STRONG_BUY])
                ).order_by(Signal.score.desc()).limit(5).all()
                
                if not top_signals:
                    await update.message.reply_text("No signals generated today yet.")
                    return
                
                # Format top signals message
                top_message = "🚀 Today's Top Signals\n\n"
                
                for i, signal in enumerate(top_signals, 1):
                    # Get token info
                    token = session.query(Token).filter(Token.id == signal.token_id).first()
                    if not token:
                        continue
                    
                    # Format signal info
                    signal_emoji = "🔥" if signal.signal_type == SignalType.STRONG_BUY else "✅"
                    top_message += (
                        f"{i}. {signal_emoji} {token.symbol} ({token.blockchain})\n"
                        f"   Signal: {signal.signal_type.value.upper()}\n"
                        f"   Score: {signal.score:.1f}/100\n"
                        f"   Price: ${signal.price_usd:.8f}\n"
                        f"   Liquidity: ${signal.liquidity_usd:,.2f}\n"
                        f"   Reason: {signal.reason}\n\n"
                    )
                
                await update.message.reply_text(top_message)
            
            except Exception as e:
                logger.error(f"Error getting top signals: {str(e)}")
                await update.message.reply_text("Error getting top signals. Please try again later.")
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error in top5today command: {str(e)}")
            await update.message.reply_text("An error occurred. Please try again later.")
    
    async def _monitor_signals(self):
        """Monitor for new signals and send them to the channel."""
        logger.info("Starting signal monitoring")
        
        while self.running:
            try:
                # Get a database session
                session = next(get_session())
                
                try:
                    # Get unsent signals
                    unsent_signals = session.query(Signal).filter(
                        Signal.sent_to_telegram == False
                    ).order_by(Signal.timestamp.desc()).all()
                    
                    for signal in unsent_signals:
                        # Get token info
                        token = session.query(Token).filter(Token.id == signal.token_id).first()
                        if not token:
                            continue
                        
                        # Send signal to channel
                        await self._send_signal_to_channel(token, signal)
                        
                        # Mark signal as sent
                        signal.sent_to_telegram = True
                        session.commit()
                
                except Exception as e:
                    logger.error(f"Error monitoring signals: {str(e)}")
                    if 'session' in locals():
                        session.rollback()
                finally:
                    if 'session' in locals():
                        session.close()
                
                # Wait before checking again
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error in signal monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _send_signal_to_channel(self, token: Token, signal: Signal):
        """
        Send a signal to the Telegram channel.
        
        Args:
            token: The token object.
            signal: The signal object.
        """
        if not TELEGRAM_CHANNEL_ID:
            logger.error("Telegram channel ID not set")
            return
        
        try:
            # Format signal message
            signal_emoji = "🔥" if signal.signal_type == SignalType.STRONG_BUY else "✅"
            
            # Get DEX link
            dex_link = self._get_dex_link(token)
            
            message = (
                f"{signal_emoji} {signal.signal_type.value.upper()} SIGNAL: {token.symbol} ({token.blockchain})\n\n"
                f"💰 Price: ${signal.price_usd:.8f}\n"
                f"💧 Liquidity: ${signal.liquidity_usd:,.2f}\n"
                f"📊 24h Volume: ${signal.volume_24h_usd:,.2f}\n"
                f"👥 Holders: {signal.holders_count}\n"
                f"📈 Buy/Sell Ratio: {signal.buy_sell_ratio:.2f}\n"
                f"🗣️ Social Mentions: {signal.social_mentions_count}\n\n"
                f"🔍 Score: {signal.score:.1f}/100\n"
                f"📝 Reason: {signal.reason}\n\n"
                f"🔗 {dex_link}\n\n"
                f"⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            
            # Send message to channel
            await self.application.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message,
                disable_web_page_preview=False
            )
            
            logger.info(f"Sent {signal.signal_type.value} signal for {token.symbol} to channel")
        
        except Exception as e:
            logger.error(f"Error sending signal to channel: {str(e)}")
    
    def _get_dex_link(self, token: Token) -> str:
        """
        Get a DEX link for a token.
        
        Args:
            token: The token object.
            
        Returns:
            DEX link as a string.
        """
        if token.blockchain == "ethereum":
            return f"https://app.uniswap.org/#/swap?outputCurrency={token.address}"
        elif token.blockchain == "solana":
            return f"https://raydium.io/swap/?inputCurrency=sol&outputCurrency={token.address}"
        else:
            return "No DEX link available"
    
    async def _schedule_daily_report(self):
        """Schedule and send daily summary reports."""
        logger.info("Starting daily report scheduler")
        
        while self.running:
            try:
                # Get current time
                now = datetime.utcnow()
                
                # Parse report time
                report_hour, report_minute = map(int, DAILY_REPORT_TIME.split(':'))
                
                # Calculate time until next report
                next_report = datetime(now.year, now.month, now.day, report_hour, report_minute)
                if now.hour > report_hour or (now.hour == report_hour and now.minute >= report_minute):
                    # Already passed for today, schedule for tomorrow
                    next_report = next_report + timedelta(days=1)
                
                # Calculate seconds until next report
                seconds_until_report = (next_report - now).total_seconds()
                
                # Wait until report time
                logger.info(f"Next daily report in {seconds_until_report:.1f} seconds")
                await asyncio.sleep(seconds_until_report)
                
                # Send daily report
                await self._send_daily_report()
                
                # Wait a minute to avoid sending duplicate reports
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"Error in daily report scheduler: {str(e)}")
                await asyncio.sleep(3600)  # Wait an hour before retrying
    
    async def _send_daily_report(self):
        """Send a daily summary report to the channel."""
        if not TELEGRAM_CHANNEL_ID:
            logger.error("Telegram channel ID not set")
            return
        
        try:
            # Get a database session
            session = next(get_session())
            
            try:
                # Get yesterday's date range
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                yesterday_start = datetime.combine(yesterday, datetime.min.time())
                yesterday_end = datetime.combine(yesterday, datetime.max.time())
                
                # Count signals by type
                buy_signals = session.query(func.count(Signal.id)).filter(
                    Signal.timestamp.between(yesterday_start, yesterday_end),
                    Signal.signal_type == SignalType.BUY
                ).scalar() or 0
                
                strong_buy_signals = session.query(func.count(Signal.id)).filter(
                    Signal.timestamp.between(yesterday_start, yesterday_end),
                    Signal.signal_type == SignalType.STRONG_BUY
                ).scalar() or 0
                
                # Get top performing tokens (by score)
                top_tokens = session.query(Token).order_by(
                    Token.total_score.desc()
                ).limit(3).all()
                
                # Format daily report
                report = (
                    "📅 Daily Summary Report\n\n"
                    f"Date: {yesterday.strftime('%Y-%m-%d')}\n\n"
                    f"📊 Signal Summary:\n"
                    f"• STRONG BUY signals: {strong_buy_signals}\n"
                    f"• BUY signals: {buy_signals}\n"
                    f"• Total signals: {strong_buy_signals + buy_signals}\n\n"
                )
                
                if top_tokens:
                    report += "🏆 Top Performing Tokens:\n"
                    for i, token in enumerate(top_tokens, 1):
                        report += (
                            f"{i}. {token.symbol} ({token.blockchain})\n"
                            f"   Score: {token.total_score:.1f}/100\n"
                            f"   Price: ${token.current_price_usd:.8f}\n"
                            f"   24h Volume: ${token.volume_24h_usd:,.2f}\n\n"
                        )
                
                report += "Stay tuned for today's signals! 🚀"
                
                # Send report to channel
                await self.application.bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=report
                )
                
                logger.info("Sent daily report to channel")
            
            except Exception as e:
                logger.error(f"Error generating daily report: {str(e)}")
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}")

# Singleton instance
telegram_bot = TelegramBot()
