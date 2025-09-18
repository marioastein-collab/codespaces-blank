import requests

TELEGRAM_TOKEN = "8402262632:AAHLXhtlueDYepJd8LUEK6J4mSh1UF2MHxg"
CHAT_ID = "8430243174"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
resp = requests.post(url, data={"chat_id": CHAT_ID, "text": "Test message from Codespaces!"})
print("Status:", resp.status_code)
print("Response:", resp.text)
