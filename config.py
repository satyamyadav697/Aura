import os

# Get from environment variables or use defaults for development
TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Other configuration options
ADMIN_IDS = [123456789]  # Replace with your Telegram user ID
MAX_MESSAGE_LENGTH = 4096  # Telegram message limit
