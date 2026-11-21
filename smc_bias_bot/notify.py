import os, time
import requests

def send(text):
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("---- (no Telegram keys, printing) ----\n" + text + "\n")
        return
    for _ in range(3):
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              data={"chat_id": chat, "text": text[:4000]}, timeout=15)
            if r.ok:
                return
        except Exception as e:
            print("telegram error:", e)
        time.sleep(2)
