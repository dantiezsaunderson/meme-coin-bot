"""
Configuration module for the Meme Coin Signal Bot.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# API Keys and credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "25254354")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "f5f087d0e5a711a51b55bcf8b94fd786")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# Blockchain RPC endpoints
ETHEREUM_RPC_URL = os.getenv("ETHEREUM_RPC_URL", "https://eth-mainnet.g.alchemy.com/v2/BJq0c9x7R8IzCaVPERhIPZ0IWSJjVQsz")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://mainnet.helius-rpc.com/?api-key=9ef176a1-6ded-40d6-9f1b-d8cf8ace068f")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/meme_coin_bot.db")

# Scoring thresholds
MIN_LIQUIDITY_USD = 10000  # Minimum liquidity in USD
MIN_HOLDERS = 50  # Minimum number of holders
MIN_VOLUME_24H = 5000  # Minimum 24h volume in USD
BUY_SELL_RATIO_THRESHOLD = 1.5  # Minimum buy/sell ratio

# Social media monitoring
MEME_KEYWORDS = [
    "meme coin", "memecoin", "doge", "shib", "pepe", "moon", "pump", 
    "100x", "1000x", "gem", "moonshot", "new listing", "launch"
]

INFLUENCER_ACCOUNTS = [
    "elonmusk", "ShibaInuHodler", "DogeWhisperer", "CryptoKaleo", 
    "cryptogemfinder", "TheCryptoLark", "100trillionUSD", "CryptoWendyO"
]

# Monitoring intervals (in seconds)
BLOCKCHAIN_SCAN_INTERVAL = 300  # 5 minutes
SOCIAL_MEDIA_SCAN_INTERVAL = 600  # 10 minutes
SCORING_INTERVAL = 900  # 15 minutes
DAILY_REPORT_TIME = "00:00"  # UTC time for daily report

# Web dashboard configuration
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8501))

# Telegram session file paths to check
TELEGRAM_SESSION_PATHS = [
    'telegram_session',
    'secrets/telegram_session',
    'coin_scan_session',
    'secrets/coin_scan_session',
    '/app/secrets/telegram_session',
    '/app/telegram_session'
]
