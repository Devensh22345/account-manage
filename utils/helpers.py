import logging
import asyncio
import aiofiles
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import Config
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, FloodWait, AuthKeyUnregistered
)

config = Config()

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )

async def log_to_channel(bot, channel_id: int, message: str, parse_mode: str = "HTML"):
    """Log message to a channel"""
    if channel_id:
        try:
            await bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            logging.error(f"Failed to log to channel {channel_id}: {e}")

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
        
        # You need to implement OTP input mechanism here
        # For now, we return None and handle OTP separately
        return None
        
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        return None
    finally:
        await app.disconnect()

async def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format"""
    # Remove non-digit characters
    digits = ''.join(filter(str.isdigit, phone_number))
    
    # Basic validation
    if len(digits) < 10 or len(digits) > 15:
        return False
    
    return True

async def get_user_accounts(user_id: int) -> List[Dict[str, Any]]:
    """Get all accounts for a user"""
    from database.mongodb import get_accounts_collection
    
    accounts_collection = await get_accounts_collection()
    
    cursor = accounts_collection.find({
        "user_id": user_id,
        "is_deleted": False
    })
    
    accounts = []
    async for account in cursor:
        accounts.append(account)
    
    return accounts

async def check_admin(user_id: int) -> bool:
    """Check if user is admin"""
    from database.mongodb import get_users_collection
    from config import Config
    
    config = Config()
    
    # Owner is always admin
    if user_id == config.OWNER_ID:
        return True
    
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"user_id": user_id})
    
    return user and (user.get("is_admin") or user.get("is_owner"))

async def check_owner(user_id: int) -> bool:
    """Check if user is owner"""
    from config import Config
    
    config = Config()
    return user_id == config.OWNER_ID

async def get_active_accounts_count() -> int:
    """Get count of active accounts"""
    from database.mongodb import get_accounts_collection
    
    accounts_collection = await get_accounts_collection()
    return await accounts_collection.count_documents({"is_active": True, "is_deleted": False})

async def format_account_info(account: Dict[str, Any]) -> str:
    """Format account information for display"""
    status = "✅ Active" if account.get("is_active") else "❌ Inactive"
    if account.get("is_frozen"):
        status = "❄️ Frozen"
    if account.get("is_deleted"):
        status = "🗑️ Deleted"
    
    return (
        f"📱 Account: {account.get('account_name', 'N/A')}\n"
        f"📞 Number: {account.get('phone_number', 'N/A')}\n"
        f"👤 Name: {account.get('first_name', '')} {account.get('last_name', '')}\n"
        f"🔗 Username: @{account.get('username', 'N/A')}\n"
        f"📝 Bio: {account.get('bio', 'N/A')[:50]}...\n"
        f"🔄 Status: {status}\n"
        f"📅 Created: {account.get('created_at').strftime('%Y-%m-%d %H:%M')}"
    )

async def split_list(lst: List, n: int) -> List[List]:
    """Split list into chunks of size n"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]
