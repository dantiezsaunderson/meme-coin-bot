from telethon import TelegramClient

# Create the client
client = TelegramClient('telegram_session', 21954686, 'b19f64a59fab06b05b6bf76420a00839')

# Start the client (this will prompt for phone number)
client.start()

# Get info about yourself
me = client.get_me()
print(f"Successfully logged in as {me.first_name} ({me.username})")

# Disconnect the client
client.disconnect()
