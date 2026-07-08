"""
WhatsApp inbound webhook (Twilio Sandbox).

Twilio POSTs form-encoded data here whenever you send a WhatsApp message to the
sandbox number. We store the message body as a note and reply with a short
confirmation using TwiML.

Run locally:
    uvicorn webhook:app --host 0.0.0.0 --port 8000

Deploy start command (Render etc.):
    uvicorn webhook:app --host 0.0.0.0 --port $PORT

Then point Twilio's "When a message comes in" (Sandbox settings) to:
    https://<your-host>/whatsapp      (method: POST)
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from models import add_note, init_db

# Optional request-signature checking so a random passer-by can't forge notes.
VALIDATE = os.environ.get("VALIDATE_TWILIO_SIGNATURE", "false").lower() == "true"
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
PUBLIC_WEBHOOK_URL = os.environ.get("PUBLIC_WEBHOOK_URL", "")  # exact https URL if behind a proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="WhatsApp Notes Webhook", lifespan=lifespan)


@app.get("/health")
def health():
    # A simple endpoint you can ping (e.g. UptimeRobot) to keep a free host warm.
    return {"status": "ok"}


@app.post("/whatsapp")
async def whatsapp(request: Request):
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}

    if VALIDATE and AUTH_TOKEN:
        validator = RequestValidator(AUTH_TOKEN)
        signature = request.headers.get("X-Twilio-Signature", "")
        url = PUBLIC_WEBHOOK_URL or str(request.url)
        if not validator.validate(url, params, signature):
            return Response(status_code=403, content="Invalid signature")

    body = (params.get("Body") or "").strip()
    sender = params.get("From", "")
    name = params.get("ProfileName", "")

    resp = MessagingResponse()

    # Ignore the Twilio "join <code>" handshake and empty/blank messages.
    if not body or body.lower().startswith("join "):
        resp.message("👋 Connected. Send me any thought and I'll save it as a note.")
        return Response(content=str(resp), media_type="application/xml")

    try:
        note = add_note(body=body, source="whatsapp", sender=sender, sender_name=name)
        resp.message(f"✅ Saved (#{note.id}).")
    except Exception:
        resp.message("⚠️ Couldn't save that one — please try again.")

    return Response(content=str(resp), media_type="application/xml")
