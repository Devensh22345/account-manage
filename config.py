import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "telegram_account_manager")
    
    # Log Channels
    MAIN_LOG_CHANNEL = os.getenv("MAIN_LOG_CHANNEL", "")
    STRING_CHANNEL = os.getenv("STRING_CHANNEL", "")
    REPORT_LOG_CHANNEL = os.getenv("REPORT_LOG_CHANNEL", "")
    SEND_LOG_CHANNEL = os.getenv("SEND_LOG_CHANNEL", "")
    OTP_LOG_CHANNEL = os.getenv("OTP_LOG_CHANNEL", "")
    JOIN_LOG_CHANNEL = os.getenv("JOIN_LOG_CHANNEL", "")
    LEAVE_LOG_CHANNEL = os.getenv("LEAVE_LOG_CHANNEL", "")
    
    # Bot Settings
    MAX_ACCOUNTS_PER_USER = 50
    MAX_TOTAL_ACCOUNTS = 10000
    SESSION_DIR = "sessions"
    
    # Redis for rate limiting (optional)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Worker Settings
    MAX_WORKERS = 10
    REQUEST_TIMEOUT = 30
