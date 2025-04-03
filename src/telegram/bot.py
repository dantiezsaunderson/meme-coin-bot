"""
Telegram bot implementation for the Meme Coin Bot.
"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional

import aiohttp
from src.signals.models import Signal
from src.utils.retry import retry_with_backoff

# Setup logging
logger = logging.getLogger(__name__)

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

class TelegramBot:
    """Telegram bot for sending signals to a channel."""
    
    def __init__(self):
        """Initialize the Telegram bot."""
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.channel_id = TELEGRAM_CHANNEL_ID
        self.session = None
        self.running = False
        self.initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the Telegram bot.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        try:
            # Validate configuration
            if not self.bot_token:
                logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
                return False
            
            if not self.channel_id:
                logger.error("TELEGRAM_CHANNEL_ID environment variable not set")
                return False
            
            # Check if channel ID is still the default value
            if self.channel_id == "your_telegram_channel_id":
                logger.error("TELEGRAM_CHANNEL_ID is set to the default value 'your_telegram_channel_id'")
                logger.error("Please update it to 'MeMeMasterBotSignals' or your actual channel ID")
                return False
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            
            # Test connection to Telegram API
            me = await self._get_me()
            if not me:
                logger.error("Failed to connect to Telegram API")
                return False
            
            logger.info(f"Telegram bot initialized successfully: @{me.get('username')}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            return False
    
    async def start(self):
        """Start the Telegram bot."""
        if self.running:
            logger.warning("Telegram bot is already running")
            return
        
        # Initialize bot
        success = await self.initialize()
        if not success:
            logger.error("Failed to initialize Telegram bot")
            return
        
        self.running = True
        logger.info("Telegram bot started")
    
    async def stop(self):
        """Stop the Telegram bot."""
        self.running = False
        
        # Close HTTP session
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("Telegram bot stopped")
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def _get_me(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the bot.
        
        Returns:
            Dictionary with bot information.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.error(f"Telegram API error: {response.status}")
                return None
            
            data = await response.json()
            
            if not data.get("ok"):
                logger.error(f"Telegram API error: {data.get('description')}")
                return None
            
            return data.get("result")
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message to the channel.
        
        Args:
            text: Message text.
            parse_mode: Parse mode for the message.
            
        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if not self.initialized:
            logger.error("Telegram bot not initialized")
            return False
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                logger.error(f"Telegram API error: {response.status}")
                return False
            
            data = await response.json()
            
            if not data.get("ok"):
                logger.error(f"Telegram API error: {data.get('description')}")
                return False
            
            return True
    
    async def send_signal(self, signal: Signal) -> bool:
        """
        Send a signal to the channel.
        
        Args:
            signal: Signal to send.
            
        Returns:
            True if the signal was sent successfully, False otherwise.
        """
        if not self.initialized:
            logger.error("Telegram bot not initialized")
            return False
        
        # Get formatted message
        message = signal.get_message()
        
        # Send message
        success = await self.send_message(message)
        
        if success:
            logger.info(f"Sent {signal.signal_type} signal for {signal.symbol} to Telegram channel")
        else:
            logger.error(f"Failed to send {signal.signal_type} signal for {signal.symbol} to Telegram channel")
        
        return success

# Singleton instance
telegram_bot = TelegramBot()
