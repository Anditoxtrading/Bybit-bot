import os
from dotenv import load_dotenv

load_dotenv()

# API Credentials
api_key = os.getenv('BYBIT_API_KEY', 'QO6N3niIzluPxWbgdr')
api_secret = os.getenv('BYBIT_API_SECRET', '7X2BRfOfixay6bXm2yRqKKnQYDBpz8S0kvLJ')

# Telegram Bot Configuration
token_telegram = os.getenv('TELEGRAM_BOT_TOKEN', '6858227834:AAFCrkSvOocikihP8HWsfBhcmUgGji-fRic')
chat_id = os.getenv('TELEGRAM_CHAT_ID', '1741049813')

# Trading Parameters
TESTNET = False  # Cambiar a False para usar mainnet