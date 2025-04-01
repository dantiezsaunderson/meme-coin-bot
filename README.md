# Meme Coin Signal Bot

A fully automated Telegram bot that identifies and sends high-potential meme coin buy signals based on on-chain metrics and influencer sentiment.

## Features

- Scans Ethereum and Solana chains for new meme coin launches
- Analyzes on-chain data (liquidity, volume, buy/sell ratio, holders, contract safety)
- Monitors Twitter/X and Telegram for meme-related keywords and influencer posts
- Scores tokens based on multiple factors
- Sends buy signal alerts to a private Telegram channel
- Provides useful commands: `/stats`, `/trending`, `/top5today`
- Daily summary reports

## Architecture

The bot is built with a modular architecture:

- **Blockchain Scanners**: Monitor Ethereum and Solana for new tokens and on-chain metrics
- **Social Media Monitors**: Track Twitter/X and Telegram for mentions and sentiment
- **Scoring Engine**: Evaluate tokens based on multiple factors
- **Telegram Bot**: Interface for users with commands and signal delivery
- **API**: Health check endpoints for monitoring

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables in a `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHANNEL_ID=your_telegram_channel_id
   ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/your_api_key
   SOLANA_RPC_URL=https://api.mainnet-beta.solana.com/your_api_key
   ```

## Usage

Run the bot:
```
python main.py
```

## Commands

- `/start` - Start the bot and get welcome message
- `/help` - Show help information
- `/stats` - Show current market stats
- `/trending` - Show trending meme coins
- `/top5today` - Show today's best signals

## Deployment

See [deployment.md](docs/deployment.md) for instructions on deploying to Render.

## License

MIT
