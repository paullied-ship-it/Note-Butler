# Notes Bot (Telegram)

A personal "brain-dump inbox." Fire a thought off to your Telegram bot anytime;
it gets saved as a note. Review, search, pin, edit, and delete them in a small
Streamlit app you run off your desktop.

*(The folder is still named `whatsapp_notes` from an earlier draft — the name is
incidental; everything now runs on Telegram.)*

## How it fits together

```
Telegram  ->  telegram_bot.py  ->  database  <-  app.py (Streamlit, on your PC)
```

- **Capture** runs in the cloud (webhook mode) so it works even when your PC is off.
- **Review** runs locally, launched by `run_notes.bat`, like your other apps.
- Both share one database via `DATABASE_URL`. Recommended = free Neon Postgres;
  the same code also runs on local SQLite.

---

## Quickest test (2 minutes, no cloud, no public URL)

1. In Telegram, message **@BotFather**, send `/newbot`, pick a name and a
   username. Copy the token it gives you.
2. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN=` to that token.
   Leave `DATABASE_URL` blank (uses a local `notes.db`).
3. `pip install -r requirements.txt`
4. Run the bot in polling mode: `python telegram_bot.py` (or `run_bot_local.bat`).
5. Message your bot `/start`, then send any text. You'll get **"✅ Saved (#1)."**
6. In another terminal, run the UI: `run_notes.bat` (or `streamlit run app.py`).

That's the whole loop. Polling mode only captures while the bot is running, so
for always-on capture, set up the cloud version below.

---

## Always-on setup (recommended)

### 1. Create the bot
Message **@BotFather** -> `/newbot` -> copy the token.

### 2. Database — Neon Postgres (free, durable)
Sign up at https://neon.tech, create a project, copy the connection string
(`postgresql://...`). You'll use it in Render and in your local `.env`.

### 3. Deploy the bot to Render (free)
1. Push this folder to a GitHub repo.
2. On https://render.com create a **New -> Web Service** from the repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn telegram_bot:app --host 0.0.0.0 --port $PORT`
   - **Environment variables:** `DATABASE_URL` (Neon string),
     `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_WEBHOOK_SECRET` (any long random string).
4. Deploy and note the URL, e.g. `https://notes-bot.onrender.com`.
5. *(Optional)* Free Render services sleep when idle. Telegram retries webhook
   delivery, so notes still arrive after a short cold-start delay. To avoid the
   delay, ping `https://<your-url>/health` every 5 min with https://uptimerobot.com.

### 4. Register the webhook (one time)
Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` in your local `.env`
(same values as Render), then run:
```
python set_telegram_webhook.py https://<your-render-url>/telegram
```

### 5. Lock the bot to you
Message your bot `/start`; it replies with your **chat ID**. Add that as
`TELEGRAM_ALLOWED_CHAT_ID` in Render's env vars and redeploy. Now anyone else
who finds the bot is ignored.

### 6. Run the review UI (local)
1. Copy `.env.example` to `.env`; set `DATABASE_URL` to the **same** Neon string.
2. Double-click `run_notes.bat` (or `streamlit run app.py`).

### 7. Test
Send your bot a message -> **"✅ Saved (#1)."** -> it appears in the Streamlit app.

---

## Using it
- **Search:** type in the box to filter by text.
- **Pinned toggle:** show only pinned notes; pinned notes sort to the top.
- **Pin / Edit / Delete:** buttons on each note; delete asks for a one-click confirm.

---

## Good to know
- **Webhook vs polling are mutually exclusive.** Running `python telegram_bot.py`
  (polling) deletes any webhook. To go back to the cloud webhook, re-run
  `set_telegram_webhook.py`.
- **Keep your bot token secret.** It lives in `.env`, which `.gitignore` keeps
  out of the repo. On Render, set it as an env var — never commit it.
- **Cost:** Telegram's Bot API is free with no limits relevant to personal use,
  no verification, and no phone number.
