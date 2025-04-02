from telethon.sync import TelegramClient

api_id = 21954686
api_hash = 'b19f64a59fab06b05b6bf76420a00839'
phone_number = '+12487786949'

with TelegramClient('telegram_session', api_id, api_hash) as client:
    # Start the client and connect
    client.connect()
    
    # Send code request if not authorized
    if not client.is_user_authorized():
        client.send_code_request(phone_number)
        # The code will be asked in the next step
        print(f"A verification code has been sent to {phone_number}")
        print("Please provide this code when prompted")
    else:
        print("Already authorized")
    
    # Print user info after successful login
    me = client.get_me()
    print("Logged in as:", me.username if hasattr(me, 'username') else me.phone)
