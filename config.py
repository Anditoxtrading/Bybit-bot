import os
from dotenv import load_dotenv

load_dotenv()

# API Credentials
api_key = os.getenv('BYBIT_API_KEY', 'coloca tu api key aqui')
api_secret = os.getenv('BYBIT_API_SECRET', 'coloca tu api secret aqui')

# Telegram Bot Configuration
token_telegram = os.getenv('TELEGRAM_BOT_TOKEN', 'coloca tu token bot de telegram aqui')
chat_id = os.getenv('TELEGRAM_CHAT_ID', 'coloca tu chat ID aqui')

# Trading Parameters
TESTNET = False  # Cambiar a False para usar mainnet
