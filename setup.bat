@echo off
echo ===============================
echo Python Packages Auto Installer
echo ===============================

python -m pip install --upgrade pip setuptools wheel

pip install python-dotenv cryptography httpx

pip install "python-telegram-bot<23,>=22.0"

pip install instagrapi

pip install playwright

pip install "playwright-stealth==1.0.6"

playwright install

pip install setuptools

pip install psutil

pip install APScheduler==3.9.1
pip install pytz

echo ===============================
echo ALL PACKAGES INSTALLED SUCCESSFULLY 🎉
echo ===============================
pause
