import requests

# Your bot token
TOKEN = "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg"
# Your chat ID
CHAT_ID = "8430243174"

# Test message
message = "Hello from Haneda Bot 🚗"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": message}

resp = requests.post(url, data=payload)
print(resp.json())
