"""
Telegram note-capture bot.

You message your Telegram bot; it saves each message as a note in the shared
database (the same one your Streamlit app reads). Two ways to run it:

  WEBHOOK MODE (recommended — always-on capture):
      uvicorn telegram_bot:app --host 0.0.0.0 --port $PORT
      Then register the webhook once with set_telegram_webhook.py.

  POLLING MODE (zero setup — great for local testing / PC-on-only):
      python telegram_bot.py
      No public URL needed; it long-polls Telegram directly.

Config (put in your environment, or a local .env):
      TELEGRAM_BOT_TOKEN         (required) from @BotFather
      TELEGRAM_ALLOWED_CHAT_ID   (optional) lock the bot to your chat only
      TELEGRAM_WEBHOOK_SECRET    (optional, webhook mode) shared secret header
      DATABASE_URL               (shared with the Streamlit app)
"""

import os
import time
from contextlib import asynccontextmanager

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request, Response
from starlette.concurrency import run_in_threadpool

from models import add_note, init_db

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()

API_BASE = f"https://api.telegram.org/bot{TOKEN}"

WELCOME = (
    "👋 Connected! Send me any thought and I'll save it as a note.\n\n"
    "Your chat ID is {chat_id} — set TELEGRAM_ALLOWED_CHAT_ID to this value "
    "to keep the bot private to you."
)


def send_message(chat_id, text):
    """Send a reply via the Telegram Bot API (best-effort; never raises)."""
    if not TOKEN:
        return
    try:
        httpx.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception:
        pass


def _authorized(chat_id) -> bool:
    if not ALLOWED_CHAT_ID:
        return True
    return str(chat_id) == ALLOWED_CHAT_ID


def handle_update(update: dict) -> None:
    """Process one Telegram update: save its text as a note and reply."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    sender = message.get("from", {})
    name = sender.get("first_name") or sender.get("username") or ""
    text = (message.get("text") or "").strip()

    if chat_id is None:
        return

    if not _authorized(chat_id):
        send_message(chat_id, "⛔ This is a private notes bot.")
        return

    if text in ("/start", "/help"):
        send_message(chat_id, WELCOME.format(chat_id=chat_id))
        return

    if not text:
        send_message(chat_id, "I can only save text notes right now.")
        return

    try:
        note = add_note(body=text, source="telegram", sender=str(chat_id), sender_name=name)
        send_message(chat_id, f"✅ Saved (#{note.id}).")
    except Exception:
        send_message(chat_id, "⚠️ Couldn't save that one — please try again.")


# ---------------------------------------------------------------------------
# Webhook mode (FastAPI)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Telegram Notes Bot", lifespan=lifespan)


@app.get("/health")
def health():
    # Ping this (e.g. UptimeRobot) to keep a free host warm.
    return {"status": "ok"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    if WEBHOOK_SECRET:
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if got != WEBHOOK_SECRET:
            return Response(status_code=403, content="forbidden")
    try:
        update = await request.json()
    except Exception:
        return {"ok": True}  # ignore anything unparseable
    await run_in_threadpool(handle_update, update)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Polling mode (no public URL needed)
# ---------------------------------------------------------------------------
def run_polling():
    if not TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN first (environment or .env).")
    init_db()
    # A webhook and getUpdates can't both be active, so clear any webhook first.
    try:
        httpx.get(f"{API_BASE}/deleteWebhook", timeout=10)
    except Exception:
        pass

    print("Polling for messages… (Ctrl+C to stop)")
    offset = None
    with httpx.Client(timeout=40) as client:
        while True:
            try:
                params = {"timeout": 30}
                if offset is not None:
                    params["offset"] = offset
                r = client.get(f"{API_BASE}/getUpdates", params=params)
                for update in r.json().get("result", []):
                    offset = update["update_id"] + 1
                    handle_update(update)
            except Exception as e:
                print("poll error:", e)
                time.sleep(3)


if __name__ == "__main__":
    run_polling()
