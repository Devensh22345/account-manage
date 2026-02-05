import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import Config
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, FloodWait, AuthKeyUnregistered
)
import re

config = Config()

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Set specific log levels
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    logging.getLogger('motor').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("✅ Logging setup complete")

async def log_to_channel(bot, channel_id: int, message: str, parse_mode: str = "HTML"):
    """Log message to a channel"""
    if channel_id:
        try:
            await bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logging.error(f"❌ Failed to log to channel {channel_id}: {e}")
    return False

async def create_pyrogram_session(
    api_id: int,
    api_hash: str,
    phone_number: str,
    session_name: str = None
) -> Optional[str]:
    """Create Pyrogram session and return session string"""
    if not session_name:
        session_name = f"sessions/{phone_number}"
    
    app = Client(
        session_name,
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone_number
    )
    
    try:
        await app.connect()
        sent_code = await app.send_code(phone_number)
        return None  # OTP needed
        
    except Exception as e:
        logging.error(f"❌ Error creating session: {e}")
        return None
    finally:
        await app.disconnect()

def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format"""
    # Remove non-digit characters except +
    if phone_number.startswith('+'):
        digits = '+' + ''.join(filter(str.isdigit, phone_number[1:]))
    else:
        digits = ''.join(filter(str.isdigit, phone_number))
    
    # Check length
    if len(digits) < 10 or len(digits) > 15:
        return False
    
    # Check if it looks like a phone number
    if not re.match(r'^\+?[0-9]{10,15}$', digits):
        return False
    
    return True

async def get_user_accounts(user_id: int) -> List[Dict[str, Any]]:
    """Get all accounts for a user"""
    from database.mongodb import get_accounts_collection
    
    try:
        accounts_collection = await get_accounts_collection()
        
        cursor = accounts_collection.find({
            "user_id": user_id,
            "is_deleted": False
        })
        
        accounts = []
        async for account in cursor:
            accounts.append(account)
        
        return accounts
        
    except Exception as e:
        logging.error(f"❌ Error getting user accounts: {e}")
        return []

async def check_admin(user_id: int) -> bool:
    """Check if user is admin"""
    from database.mongodb import get_users_collection
    from config import Config
    
    config = Config()
    
    # Owner is always admin
    if user_id == config.OWNER_ID:
        return True
    
    try:
        users_collection = await get_users_collection()
        user = await users_collection.find_one({"user_id": user_id})
        
        return user and (user.get("is_admin") or user.get("is_owner"))
        
    except Exception as e:
        logging.error(f"❌ Error checking admin status: {e}")
        return False

async def check_owner(user_id: int) -> bool:
    """Check if user is owner"""
    from config import Config
    
    config = Config()
    return user_id == config.OWNER_ID

async def get_active_accounts_count() -> int:
    """Get count of active accounts"""
    from database.mongodb import get_accounts_collection
    
    try:
        accounts_collection = await get_accounts_collection()
        return await accounts_collection.count_documents({
            "is_active": True,
            "is_deleted": False
        })
    except Exception as e:
        logging.error(f"❌ Error getting active accounts count: {e}")
        return 0

async def format_account_info(account: Dict[str, Any]) -> str:
    """Format account information for display"""
    try:
        status = "✅ Active" if account.get("is_active") else "❌ Inactive"
        if account.get("is_frozen"):
            status = "❄️ Frozen"
        if account.get("is_deleted"):
            status = "🗑️ Deleted"
        
        created_at = account.get("created_at")
        if isinstance(created_at, datetime):
            created_str = created_at.strftime('%Y-%m-%d %H:%M')
        else:
            created_str = str(created_at)
        
        return (
            f"📱 **Account:** {account.get('account_name', 'N/A')}\n"
            f"📞 **Number:** {account.get('phone_number', 'N/A')}\n"
            f"👤 **Name:** {account.get('first_name', '')} {account.get('last_name', '')}\n"
            f"🔗 **Username:** @{account.get('username', 'N/A')}\n"
            f"📝 **Bio:** {account.get('bio', 'N/A')[:50]}...\n"
            f"🔄 **Status:** {status}\n"
            f"📅 **Created:** {created_str}"
        )
    except Exception as e:
        logging.error(f"❌ Error formatting account info: {e}")
        return "Error formatting account information"

async def split_list(lst: List, n: int) -> List[List]:
    """Split list into chunks of size n"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def extract_otp_from_text(text: str) -> Optional[str]:
    """Extract OTP from text message"""
    if not text:
        return None
    
    # Common OTP patterns
    patterns = [
        r'\b\d{4,6}\b',  # 4-6 digit OTP
        r'code[\s:]*(\d{4,6})',
        r'OTP[\s:]*(\d{4,6})',
        r'password[\s:]*(\d{4,6})',
        r'verification[\s:]*(\d{4,6})',
        r'\b(\d{4,6})\s+is your',
        r'your code is[\s:]*(\d{4,6})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
    
    return None

def format_time_delta(delta_seconds: float) -> str:
    """Format time delta in human readable format"""
    if delta_seconds < 60:
        return f"{int(delta_seconds)} seconds"
    elif delta_seconds < 3600:
        minutes = int(delta_seconds // 60)
        seconds = int(delta_seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(delta_seconds // 3600)
        minutes = int((delta_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def sanitize_text(text: str, max_length: int = 200) -> str:
    """Sanitize text for safe display"""
    if not text:
        return ""
    
    # Remove newlines and extra spaces
    text = ' '.join(text.split())
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Escape HTML special characters
    text = (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
    )
    
    return text
