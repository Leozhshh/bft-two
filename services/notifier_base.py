import requests
from config.secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram(msg: str):
    """底层 Telegram 发送函数"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram 发送失败: {e}")