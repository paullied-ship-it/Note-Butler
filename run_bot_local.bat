@echo off
REM Runs the Telegram bot in polling mode locally (no public URL needed).
cd /d "%~dp0"

REM If you use a virtual environment, uncomment the next line:
REM call .venv\Scripts\activate.bat

python telegram_bot.py
pause
