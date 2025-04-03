# Meme Coin Bot

A powerful bot that scans Solana and Ethereum blockchains for new meme coins, scores them using on-chain metrics and influencer sentiment, and delivers buy signals to a Telegram channel.

## Features

- **Multi-Chain Support**: Scans both Solana and Ethereum blockchains for new tokens
- **Real-Time Data**: Uses on-chain data for accurate token analysis
- **Advanced Scoring**: Evaluates tokens based on volume, liquidity, holder count, momentum, and safety
- **Smart Filtering**: Filters out low-quality tokens based on configurable thresholds
- **Telegram Alerts**: Sends buy signals to your Telegram channel with detailed token information
- **Performance Optimized**: Uses parallel processing, caching, and retry mechanisms for reliability

## Installation

### Prerequisites

- Python 3.10+
- Redis (optional, for enhanced caching)
- Telegram Bot Token
- API Keys for Ethereum and Solana

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/meme-coin-bot.git
cd meme-coin-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the example environment file and edit it with your API keys:
```bash
cp .env.example .env
nano .env  # Edit with your API keys and configuration
```

4. Run the bot:
```bash
python main.py
```

## Configuration

The bot is configured through environment variables in the `.env` file:

### Required Configuration

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHANNEL_ID`: Your Telegram channel ID (e.g., "MeMeMasterBotSignals")
- `ETHEREUM_RPC_URL`: Ethereum RPC URL
- `ETHEREUM_API_KEY`: Etherscan API key
- `SOLANA_RPC_URL`: Solana RPC URL
- `HELIUS_API_KEY`: Helius API key for Solana

### Optional Configuration

- `REDIS_URL`: Redis connection URL (e.g., "redis://localhost:6379/0")
- `COINGECKO_API_KEY`: CoinGecko API key for price data
- `SCAN_INTERVAL_SECONDS`: Interval between scans (default: 60)
- `MAX_CONCURRENT_SCANS`: Maximum number of concurrent scans (default: 10)
- `MINIMUM_LIQUIDITY_USD`: Minimum liquidity threshold in USD (default: 10000)
- `MINIMUM_TOTAL_SCORE`: Minimum score threshold for signals (default: 70)
- `SIGNAL_COOLDOWN_MINUTES`: Cooldown period between signals for the same token (default: 30)
- `MAX_SIGNALS_PER_HOUR`: Maximum number of signals per hour (default: 5)

## Project Structure

```
meme-coin-bot/
├── main.py                 # Main application entry point
├── src/
│   ├── scanners/           # Blockchain scanners
│   │   ├── base.py         # Base scanner interface
│   │   ├── ethereum.py     # Ethereum scanner implementation
│   │   ├── solana.py       # Solana scanner implementation
│   │   └── service.py      # Scanner service coordinator
│   ├── filters/            # Token filtering
│   │   ├── base.py         # Base filter interface
│   │   ├── liquidity.py    # Liquidity threshold filter
│   │   ├── safety.py       # Contract safety filter
│   │   └── service.py      # Filter service coordinator
│   ├── scoring/            # Token scoring
│   │   ├── models.py       # Scoring models and weights
│   │   ├── scorer.py       # Token scorer implementation
│   │   └── service.py      # Scoring service coordinator
│   ├── signals/            # Signal generation
│   │   ├── models.py       # Signal data models
│   │   ├── generator.py    # Signal generator
│   │   └── service.py      # Signal service coordinator
│   ├── telegram/           # Telegram integration
│   │   ├── bot.py          # Telegram bot implementation
│   │   └── formatter.py    # Message formatter
│   ├── utils/              # Utility functions
│   │   ├── cache.py        # Caching utilities
│   │   └── retry.py        # Retry and circuit breaker patterns
│   └── database/           # Database operations
├── .env.example            # Example environment configuration
├── requirements.txt        # Python dependencies
├── CHANGELOG.md            # Project change history
└── performance_summary.md  # Performance metrics
```

## How It Works

1. **Scanning**: The bot scans Ethereum and Solana blockchains for new token creations
2. **Filtering**: Tokens are filtered based on liquidity and safety criteria
3. **Scoring**: Passing tokens are scored based on volume, liquidity, holders, momentum, and safety
4. **Signal Generation**: High-scoring tokens generate buy signals
5. **Notification**: Signals are sent to the configured Telegram channel

## Performance

See [performance_summary.md](performance_summary.md) for detailed performance metrics and improvements.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a history of changes and improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Helius](https://helius.xyz/) for Solana API
- [Etherscan](https://etherscan.io/) for Ethereum API
- [CoinGecko](https://www.coingecko.com/) for price data
- [Telegram Bot API](https://core.telegram.org/bots/api) for notifications
