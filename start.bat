@echo off
cd /d "%~dp0"

pip install -q -r requirements.txt
python -m playwright install chromium

start "Converter server" python run.py
timeout /t 3 >nul
start "" http://127.0.0.1:5000
