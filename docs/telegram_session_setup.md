# Telegram Session Setup Instructions

This document explains how to set up a Telegram session file for the Meme Coin Signal Bot.

## Why a Session File is Needed

The bot uses the Telethon library to monitor Telegram groups for meme coin mentions. In a headless environment like Render, Telethon cannot prompt for interactive authentication. A pre-authenticated session file solves this problem.

## Steps to Create a Session File

1. Make sure you have Python installed on your local computer
2. Install the Telethon package:
   ```
   pip install telethon
   ```
3. Save the following script as `session_creator.py`:
   ```python
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
   ```
4. Run the script:
   ```
   python session_creator.py
   ```
5. When prompted, enter your phone number (with country code, e.g., +1234567890)
6. Enter the verification code sent to your Telegram account
7. The script will create a file named `coin_scan_session.session` in the same directory

## Uploading the Session File

1. Upload the `coin_scan_session.session` file to the `/secrets/` directory in your GitHub repository
2. Commit and push the changes
3. Redeploy your bot on Render

## Security Considerations

The session file contains authentication information for your Telegram account. While it doesn't include your password, it does allow access to your account. Consider the following security measures:

1. Use a dedicated Telegram account for the bot, not your personal account
2. After deployment is complete and working, you may want to remove the session file from the public repository
3. For long-term production use, consider using environment variables or secure storage for sensitive files

## Fallback Mechanism

If a valid session file is not found, the bot will automatically fall back to using mock data for Telegram monitoring. This ensures the bot remains functional even without Telegram authentication.
