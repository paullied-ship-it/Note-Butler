"""
One-time helper to register (or delete) your Telegram webhook.

Register (point Telegram at your deployed bot):
    python set_telegram_webhook.py https://your-app.onrender.com/telegram

Delete (e.g. to switch back to polling mode):
    python set_telegram_webhook.py --delete

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET from the environment/.env.
"""

import os
import sys

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
API_BASE = f"https://api.telegram.org/bot{TOKEN}"


def main():
    if not TOKEN:
        sys.exit("Set TELEGRAM_BOT_TOKEN first (environment or .env).")

    args = sys.argv[1:]
    if args and args[0] == "--delete":
        print(httpx.get(f"{API_BASE}/deleteWebhook", timeout=15).json())
        return

    if not args:
        sys.exit("Usage: python set_telegram_webhook.py <https-url>/telegram   |   --delete")

    payload = {"url": args[0]}
    if SECRET:
        payload["secret_token"] = SECRET
    print(httpx.post(f"{API_BASE}/setWebhook", json=payload, timeout=15).json())


if __name__ == "__main__":
    main()
