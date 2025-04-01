# Meme Coin Signal Bot - Deployment Guide

This guide explains how to deploy the Meme Coin Signal Bot on Render.

## Prerequisites

1. A Render account (https://render.com)
2. A GitHub account for repository hosting
3. Telegram Bot API token (from BotFather)
4. Ethereum and Solana API keys

## Environment Variables

The following environment variables need to be set in Render:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=your_telegram_channel_id
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/DE3J7IZAIN7FS327J5RR9TMBBEGBHQN6CD
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com/020da7f45b05497f951bc2218489ee73
DATABASE_URL=your_database_url (if using external database)
```

## Deployment Steps

1. Push the code to GitHub:
   ```
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/meme-coin-bot.git
   git push -u origin master
   ```

2. Create a new Web Service on Render:
   - Connect your GitHub repository
   - Set the name to "meme-coin-signal-bot"
   - Set the build command: `pip install -r requirements.txt`
   - Set the start command: `python main.py`
   - Add the environment variables listed above
   - Select an appropriate instance type (at least 1GB RAM recommended)
   - Click "Create Web Service"

3. Configure auto-restart:
   - In the Render dashboard, go to your web service
   - Under "Settings" > "Health", enable health checks
   - Set the health check path to `/health` (requires implementing a health endpoint)
   - Enable auto-restart on failure

## Monitoring and Maintenance

- Check the Render logs for any errors or issues
- Set up Render alerts for service downtime
- Periodically check the database for growth and performance

## Updating the Bot

1. Make changes to your local repository
2. Commit and push to GitHub
3. Render will automatically deploy the updated code

## Troubleshooting

- If the bot stops responding, check the Render logs for errors
- Ensure all environment variables are correctly set
- Verify that the Telegram bot token is valid
- Check that the Telegram channel ID is correct
