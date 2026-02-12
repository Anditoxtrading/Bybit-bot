import os
from dotenv import load_dotenv

load_dotenv()

# API Credentials
api_key = os.getenv('BYBIT_API_KEY', '')
api_secret = os.getenv('BYBIT_API_SECRET', '')

# Telegram Bot Configuration
token_telegram = os.getenv('TELEGRAM_BOT_TOKEN', '')
chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

# Trading Parameters
TESTNET = False  # Cambiar a False para usar mainnet
