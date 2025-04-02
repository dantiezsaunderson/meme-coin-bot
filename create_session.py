from telethon.sync import TelegramClient

api_id = 25254354
api_hash = 'f5f087d0e5a711a51b55bcf8b94fd786'

with TelegramClient('telegram_session', api_id, api_hash) as client:
    print("Logged in as:", client.get_me().username)
