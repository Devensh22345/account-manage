import logging
import asyncio
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Store login states
login_states: Dict[int, Dict[str, Any]] = {}

async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command"""
    user_id = update.effective_user.id
    
    # Check max accounts per user
    try:
        from utils.helpers import get_user_accounts
        from config import Config
        
        config = Config()
        accounts = await get_user_accounts(user_id)
        
        if len(accounts) >= config.MAX_ACCOUNTS_PER_USER:
            await update.message.reply_text(
                f"❌ You have reached the maximum limit of {config.MAX_ACCOUNTS_PER_USER} accounts!"
            )
            return
        
        # Check total accounts limit
        from utils.helpers import get_active_accounts_count
        total_accounts = await get_active_accounts_count()
        if total_accounts >= config.MAX_TOTAL_ACCOUNTS:
            await update.message.reply_text(
                f"❌ Bot has reached maximum capacity of {config.MAX_TOTAL_ACCOUNTS} accounts!"
            )
            return
        
    except Exception as e:
        logger.error(f"Error checking account limits: {e}")
        await update.message.reply_text("❌ Error checking account limits. Please try again.")
        return
    
    # Initialize login state
    login_states[user_id] = {
        "step": "api_id",
        "data": {}
    }
    
    await update.message.reply_text(
        "🔐 **Login to Telegram Account**\n\n"
        "Please send your API ID:\n"
        "You can get it from https://my.telegram.org\n\n"
        "To cancel, send /cancel",
        parse_mode="Markdown"
    )

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    # Remove all non-digit characters except +
    if phone.startswith('+'):
        digits = '+' + ''.join(filter(str.isdigit, phone[1:]))
    else:
        digits = ''.join(filter(str.isdigit, phone))
    
    # Check length
    if len(digits) < 10 or len(digits) > 15:
        return False
    
    # Check if it looks like a phone number
    if not re.match(r'^\+?[0-9]{10,15}$', digits):
        return False
    
    return True

async def handle_login_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle login process messages"""
    user_id = update.effective_user.id
    
    if user_id not in login_states:
        return
    
    state = login_states[user_id]
    step = state["step"]
    text = update.message.text.strip()
    
    try:
        if step == "api_id":
            # Validate API ID
            if not text.isdigit():
                await update.message.reply_text("❌ Please send a valid numeric API ID!")
                return
            
            api_id = int(text)
            if api_id < 10000 or api_id > 999999999:
                await update.message.reply_text("❌ Invalid API ID. Must be between 10000 and 999999999")
                return
            
            state["data"]["api_id"] = api_id
            state["step"] = "api_hash"
            
            await update.message.reply_text(
                "✅ API ID saved!\n\n"
                "🔑 Now send your API Hash:\n"
                "You can get it from https://my.telegram.org\n\n"
                "To cancel, send /cancel"
            )
            
        elif step == "api_hash":
            # Validate API Hash
            if len(text) != 32 or not re.match(r'^[a-f0-9]{32}$', text, re.IGNORECASE):
                await update.message.reply_text("❌ Invalid API Hash! Must be 32 hexadecimal characters")
                return
            
            state["data"]["api_hash"] = text
            state["step"] = "phone_number"
            
            await update.message.reply_text(
                "✅ API Hash saved!\n\n"
                "📱 Now send your phone number in international format:\n"
                "Example: +1234567890 or +441234567890\n\n"
                "To cancel, send /cancel"
            )
            
        elif step == "phone_number":
            # Validate phone number
            if not validate_phone_number(text):
                await update.message.reply_text(
                    "❌ Invalid phone number format!\n"
                    "Please use international format: +1234567890"
                )
                return
            
            # Check if phone number already exists
            try:
                from database.mongodb import get_accounts_collection
                accounts_collection = await get_accounts_collection()
                existing_account = await accounts_collection.find_one({
                    "phone_number": text,
                    "is_deleted": False
                })
                
                if existing_account:
                    await update.message.reply_text(
                        "❌ This phone number is already registered!\n"
                        "Please use a different number or contact admin."
                    )
                    del login_states[user_id]
                    return
            except Exception as e:
                logger.error(f"Error checking existing account: {e}")
            
            state["data"]["phone_number"] = text
            state["step"] = "account_name"
            
            await update.message.reply_text(
                "✅ Phone number saved!\n\n"
                "👤 Now send a name for this account (2-50 characters):\n"
                "Example: My Personal Account\n\n"
                "To cancel, send /cancel"
            )
            
        elif step == "account_name":
            if len(text) < 2 or len(text) > 50:
                await update.message.reply_text("❌ Account name must be 2-50 characters!")
                return
            
            # Check for invalid characters
            if re.search(r'[<>:"/\\|?*]', text):
                await update.message.reply_text("❌ Account name contains invalid characters!")
                return
            
            state["data"]["account_name"] = text
            
            # Start Pyrogram login process
            await start_pyrogram_login(update, context, state)
            
        elif step == "otp":
            if not text.isdigit() or len(text) < 4 or len(text) > 8:
                await update.message.reply_text("❌ Please send a valid OTP (4-8 digits)!")
                return
            
            state["data"]["otp_code"] = text
            await verify_otp(update, context, state)
            
        elif step == "password":
            if len(text) < 1:
                await update.message.reply_text("❌ Please send your 2FA password!")
                return
            
            state["data"]["password"] = text
            await verify_password(update, context, state)
            
    except Exception as e:
        logger.error(f"❌ Login error at step {step}: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}\n\n"
            "Please start over with /login"
        )
        # Clean up
        if user_id in login_states:
            app = login_states[user_id].get("app")
            if app:
                try:
                    await app.disconnect()
                except:
                    pass
            del login_states[user_id]

async def start_pyrogram_login(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    """Start Pyrogram login process"""
    user_id = update.effective_user.id
    
    await update.message.reply_text("🔄 Connecting to Telegram...")
    
    try:
        from pyrogram import Client
        
        # Create session name
        phone = state["data"]["phone_number"]
        session_name = f"sessions/{user_id}_{phone.replace('+', '')}"
        
        # Create Pyrogram client
        app = Client(
            name=session_name,
            api_id=state["data"]["api_id"],
            api_hash=state["data"]["api_hash"],
            phone_number=phone,
            workdir="sessions"
        )
        
        await app.connect()
        
        # Send verification code
        sent_code = await app.send_code(phone_number=phone)
        
        # Store app instance and phone code hash
        state["app"] = app
        state["data"]["phone_code_hash"] = sent_code.phone_code_hash
        state["step"] = "otp"
        
        await update.message.reply_text(
            "📲 **Verification Code Sent!**\n\n"
            "A 5-digit code has been sent to your Telegram app.\n"
            "Please send the code you received:\n\n"
            "Example: 12345\n\n"
            "To cancel, send /cancel"
        )
        
    except Exception as e:
        logger.error(f"❌ Pyrogram connection error: {e}", exc_info=True)
        
        error_msg = str(e).lower()
        if "flood" in error_msg:
            await update.message.reply_text(
                "⏳ **Flood wait error!**\n\n"
                "Telegram has rate limited this phone number.\n"
                "Please wait a few minutes and try again."
            )
        elif "phone" in error_msg and "invalid" in error_msg:
            await update.message.reply_text(
                "❌ **Invalid phone number!**\n\n"
                "Please check your phone number and try again."
            )
        elif "api_id" in error_msg:
            await update.message.reply_text(
                "❌ **Invalid API credentials!**\n\n"
                "Please check your API ID and API Hash from https://my.telegram.org"
            )
        else:
            await update.message.reply_text(
                f"❌ **Connection failed:** {str(e)[:100]}\n\n"
                "Please check your credentials and try again."
            )
        
        # Clean up
        if user_id in login_states:
            app = login_states[user_id].get("app")
            if app:
                try:
                    await app.disconnect()
                except:
                    pass
            del login_states[user_id]

async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    """Verify OTP code"""
    user_id = update.effective_user.id
    
    await update.message.reply_text("🔐 Verifying OTP...")
    
    app = state.get("app")
    if not app:
        await update.message.reply_text("❌ Session expired. Please start over!")
        if user_id in login_states:
            del login_states[user_id]
        return
    
    try:
        from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
        
        # Sign in with OTP
        signed_in = await app.sign_in(
            phone_number=state["data"]["phone_number"],
            phone_code_hash=state["data"]["phone_code_hash"],
            phone_code=state["data"]["otp_code"]
        )
        
        # If we get here, OTP was successful
        await complete_session_setup(update, context, state, signed_in)
        
    except SessionPasswordNeeded:
        # 2FA password required
        state["step"] = "password"
        await update.message.reply_text(
            "🔒 **Two-Step Verification Required**\n\n"
            "This account has 2FA enabled.\n"
            "Please send your password:\n\n"
            "To cancel, send /cancel"
        )
        
    except PhoneCodeInvalid:
        await update.message.reply_text(
            "❌ **Invalid OTP code!**\n\n"
            "Please check the code and try again.\n"
            "Send the correct OTP:"
        )
        # Keep in OTP step
        state["step"] = "otp"
        
    except PhoneCodeExpired:
        await update.message.reply_text(
            "❌ **OTP code expired!**\n\n"
            "The code has expired. Please start over with /login"
        )
        # Clean up
        if user_id in login_states:
            await app.disconnect()
            del login_states[user_id]
        
    except Exception as e:
        logger.error(f"❌ OTP verification error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ **Verification failed:** {str(e)[:100]}\n\n"
            "Please start over with /login"
        )
        # Clean up
        if user_id in login_states:
            await app.disconnect()
            del login_states[user_id]

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    """Verify 2FA password"""
    user_id = update.effective_user.id
    
    await update.message.reply_text("🔐 Verifying password...")
    
    app = state.get("app")
    if not app:
        await update.message.reply_text("❌ Session expired. Please start over!")
        if user_id in login_states:
            del login_states[user_id]
        return
    
    try:
        # Check password
        await app.check_password(state["data"]["password"])
        
        # Sign in with password
        signed_in = await app.sign_in(
            phone_number=state["data"]["phone_number"],
            phone_code_hash=state["data"]["phone_code_hash"],
            phone_code=state["data"]["otp_code"]
        )
        
        await complete_session_setup(update, context, state, signed_in)
        
    except Exception as e:
        logger.error(f"❌ Password verification error: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ **Invalid password!**\n\n"
            "Please send the correct password:\n\n"
            "To cancel, send /cancel"
        )
        # Stay in password step
        state["step"] = "password"

async def complete_session_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict, signed_in):
    """Complete session setup and save to database"""
    user_id = update.effective_user.id
    app = state["app"]
    
    try:
        # Get session string
        session_string = await app.export_session_string()
        
        # Get user info
        me = await app.get_me()
        
        # Save to database
        await save_account_to_db(update, context, state, session_string, me)
        
        # Success message
        await update.message.reply_text(
            f"✅ **Account Added Successfully!**\n\n"
            f"🏷️ **Account Name:** {state['data']['account_name']}\n"
            f"📱 **Phone:** {state['data']['phone_number']}\n"
            f"👤 **Username:** @{me.username if me.username else 'No username'}\n"
            f"🆔 **User ID:** {me.id}\n\n"
            f"✨ **You can now use this account with other commands!**\n"
            f"Use `/set` to manage your accounts."
        )
        
    except Exception as e:
        logger.error(f"❌ Session setup error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ **Error saving account:** {str(e)[:100]}\n\n"
            "Please try again with /login"
        )
    finally:
        # Clean up
        if app:
            await app.disconnect()
        if user_id in login_states:
            del login_states[user_id]

async def save_account_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict, session_string: str, me):
    """Save account to MongoDB"""
    from database.mongodb import get_accounts_collection, get_users_collection
    
    accounts_collection = await get_accounts_collection()
    users_collection = await get_users_collection()
    
    # Create account document
    account_data = {
        "user_id": update.effective_user.id,
        "phone_number": state["data"]["phone_number"],
        "api_id": state["data"]["api_id"],
        "api_hash": state["data"]["api_hash"],
        "session_string": session_string,
        "account_name": state["data"]["account_name"],
        "first_name": me.first_name or "",
        "last_name": me.last_name or "",
        "username": me.username or "",
        "telegram_id": me.id,
        "is_active": True,
        "is_frozen": False,
        "is_deleted": False,
        "two_step_enabled": "password" in state["data"],
        "last_seen": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert account
    result = await accounts_collection.insert_one(account_data)
    
    # Update user document
    await users_collection.update_one(
        {"user_id": update.effective_user.id},
        {
            "$set": {
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name,
                "updated_at": datetime.utcnow()
            },
            "$addToSet": {"accounts": result.inserted_id},
            "$setOnInsert": {
                "is_admin": False,
                "is_owner": update.effective_user.id == context.bot.id,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    # Log to main channel if configured
    try:
        from config import Config
        from utils.helpers import log_to_channel
        
        config = Config()
        if config.MAIN_LOG_CHANNEL:
            await log_to_channel(
                context.bot,
                config.MAIN_LOG_CHANNEL,
                f"✅ **New Account Added**\n\n"
                f"👤 **User:** {update.effective_user.id}\n"
                f"📱 **Account:** {state['data']['account_name']}\n"
                f"📞 **Phone:** {state['data']['phone_number']}\n"
                f"👥 **Telegram:** @{me.username if me.username else 'No username'}"
            )
    except Exception as e:
        logger.error(f"Error logging to channel: {e}")

async def handle_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle login callback queries"""
    query = update.callback_query
    await query.answer()
    
    # Handle different callback actions
    data = query.data
    
    if data == "login_cancel":
        user_id = query.from_user.id
        if user_id in login_states:
            app = login_states[user_id].get("app")
            if app:
                try:
                    await app.disconnect()
                except:
                    pass
            del login_states[user_id]
        
        await query.edit_message_text("❌ Login cancelled!")
