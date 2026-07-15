@echo off
REM Launches the Notes review UI.
cd /d "%~dp0"

REM If you use a virtual environment, uncomment the next line:
REM call .venv\Scripts\activate.bat

python -m streamlit run app.py

echo.
echo If Streamlit did not open, read any message above.
pause
