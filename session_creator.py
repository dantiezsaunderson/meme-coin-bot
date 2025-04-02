"""
Script to create a Telegram session file for the Meme Coin Signal Bot.

Run this script locally to create a session file that can be uploaded to the repository.
"""
from telethon.sync import TelegramClient

# Telegram API credentials
api_id = 25254354
api_hash = 'f5f087d0e5a711a51b55bcf8b94fd786'

# Create and start the client
with TelegramClient('coin_scan_session', api_id, api_hash) as client:
    me = client.get_me()
    print(f"Session created for: {me.username if me.username else me.first_name}")
    print("Session file 'coin_scan_session.session' has been created.")
    print("Upload this file to your GitHub repository in the /secrets/ directory.")
