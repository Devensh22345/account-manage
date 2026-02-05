
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8212386488:AAFFJm55JruEPc5lRP0MijbYe_nXz4eFSh4")
    OWNER_ID = int(os.getenv("OWNER_ID", "6872968794"))
    
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://10:10@cluster0.rbnwfqt.mongodb.net/?appName=Cluster0")
    DB_NAME = os.getenv("DB_NAME", "telegram_account_manager")
    
    # Log Channels (can be set via bot or .env)
    MAIN_LOG_CHANNEL = int(os.getenv("MAIN_LOG_CHANNEL", 0)) if os.getenv("MAIN_LOG_CHANNEL") else None
    STRING_CHANNEL = int(os.getenv("STRING_CHANNEL", 0)) if os.getenv("STRING_CHANNEL") else None
    REPORT_LOG_CHANNEL = int(os.getenv("REPORT_LOG_CHANNEL", 0)) if os.getenv("REPORT_LOG_CHANNEL") else None
    SEND_LOG_CHANNEL = int(os.getenv("SEND_LOG_CHANNEL", 0)) if os.getenv("SEND_LOG_CHANNEL") else None
    OTP_LOG_CHANNEL = int(os.getenv("OTP_LOG_CHANNEL", 0)) if os.getenv("OTP_LOG_CHANNEL") else None
    JOIN_LOG_CHANNEL = int(os.getenv("JOIN_LOG_CHANNEL", 0)) if os.getenv("JOIN_LOG_CHANNEL") else None
    LEAVE_LOG_CHANNEL = int(os.getenv("LEAVE_LOG_CHANNEL", 0)) if os.getenv("LEAVE_LOG_CHANNEL") else None
    
    # Bot Settings
    MAX_ACCOUNTS_PER_USER = int(os.getenv("MAX_ACCOUNTS_PER_USER", 50))
    MAX_TOTAL_ACCOUNTS = int(os.getenv("MAX_TOTAL_ACCOUNTS", 10000))
    SESSION_DIR = os.getenv("SESSION_DIR", "sessions")
    
    # Redis for rate limiting (optional)
    REDIS_URL = os.getenv("REDIS_URL", "")
    
    # Worker Settings
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 10))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
    
    # Security
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "default-encryption-key-change-this")
    
    def validate(self):
        """Validate configuration"""
        errors = []
        
        if not self.BOT_TOKEN or self.BOT_TOKEN == "your_bot_token_here":
            errors.append("BOT_TOKEN is not set in .env file")
        
        if self.OWNER_ID == 0:
            errors.append("OWNER_ID is not set in .env file")
        
        if not self.MONGO_URI:
            errors.append("MONGO_URI is not set in .env file")
        
        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"   - {error}")
            print("\nPlease edit the .env file with your credentials")
            return False
        
        return True
