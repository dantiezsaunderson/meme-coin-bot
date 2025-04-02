from telethon import TelegramClient, sync
import asyncio

# API credentials - ensure API ID is an integer
api_id = 21954686  # Integer, not string
api_hash = 'b19f64a59fab06b05b6bf76420a00839'  # String

async def main():
    # Create the client and connect
    client = TelegramClient('telegram_session', api_id, api_hash)
    await client.start(phone='+12487786949')
    
    # Ensure we're authorized
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Success! Logged in as: {me.username or me.first_name}")
        print(f"Session file created: telegram_session.session")
    else:
        print("Authorization failed")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
