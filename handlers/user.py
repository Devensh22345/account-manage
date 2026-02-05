import logging
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import (
    get_user_accounts, format_account_info,
    check_admin, log_to_channel, split_list
)
from database.mongodb import get_accounts_collection, get_users_collection
from config import Config
from bson.objectid import ObjectId

config = Config()
logger = logging.getLogger(__name__)

# User states for various operations
user_states: Dict[int, Dict] = {}

async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set command - User settings menu"""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📱 My Accounts", callback_data="user_accounts")],
        [InlineKeyboardButton("🗑️ Remove Account", callback_data="user_remove_menu")],
        [InlineKeyboardButton("🔄 Refresh Accounts", callback_data="user_refresh")],
        [InlineKeyboardButton("📝 Set Log Channel", callback_data="user_set_log")],
        [InlineKeyboardButton("❌ Remove Log Channel", callback_data="user_remove_log")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ **User Settings Menu**\n\n"
        "Select an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "user_accounts":
        await show_user_accounts(query, context)
    elif data == "user_remove_menu":
        await show_remove_menu(query, context)
    elif data == "user_refresh":
        await refresh_accounts(query, context)
    elif data == "user_set_log":
        await set_log_channel(query, context)
    elif data == "user_remove_log":
        await remove_log_channel(query, context)
    elif data.startswith("user_account_"):
        await handle_account_action(query, context, data)
    elif data.startswith("user_remove_"):
        await handle_remove_action(query, context, data)
    elif data == "user_back":
        await handle_settings(update, context)

async def show_user_accounts(query, context):
    """Show user's accounts"""
    user_id = query.from_user.id
    accounts = await get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text(
            "📭 You have no accounts added yet.\n"
            "Use /login to add your first account."
        )
        return
    
    # Create account list with pagination
    page = int(context.user_data.get("account_page", 0))
    accounts_per_page = 5
    
    total_pages = (len(accounts) + accounts_per_page - 1) // accounts_per_page
    start_idx = page * accounts_per_page
    end_idx = min(start_idx + accounts_per_page, len(accounts))
    
    message = f"📱 **Your Accounts** ({len(accounts)} total)\n\n"
    
    for i, account in enumerate(accounts[start_idx:end_idx], start=start_idx + 1):
        status = "✅" if account.get("is_active") else "❌"
        message += f"{i}. {status} {account.get('account_name', 'N/A')}\n"
        message += f"   📞: {account.get('phone_number', 'N/A')}\n"
        message += f"   👤: @{account.get('username', 'N/A')}\n\n"
    
    # Navigation buttons
    keyboard = []
    
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"user_page_{page-1}"))
    
    if page < total_pages - 1:
        if page > 0:
            keyboard.append(InlineKeyboardButton("➡️ Next", callback_data=f"user_page_{page+1}"))
        else:
            keyboard = [InlineKeyboardButton("➡️ Next", callback_data=f"user_page_{page+1}")]
    
    # Add account action buttons
    if keyboard:
        reply_markup = InlineKeyboardMarkup([keyboard] + [
            [InlineKeyboardButton("🔍 View Details", callback_data=f"user_view_{page}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="user_back")]
        ])
    else:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 View Details", callback_data=f"user_view_{page}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="user_back")]
        ])
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_remove_menu(query, context):
    """Show remove account menu"""
    user_id = query.from_user.id
    accounts = await get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text(
            "📭 You have no accounts to remove."
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Remove All Accounts", callback_data="user_remove_all")],
        [InlineKeyboardButton("🔢 Remove by Numbers", callback_data="user_remove_by_numbers")],
        [InlineKeyboardButton("📝 Select Accounts", callback_data="user_select_accounts")]
    ]
    
    # Add individual account buttons (max 10)
    for i, account in enumerate(accounts[:10], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"❌ {account.get('account_name', f'Account {i}')}",
                callback_data=f"user_remove_single_{account['_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="user_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑️ **Remove Accounts**\n\n"
        "Select accounts to remove:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def refresh_accounts(query, context):
    """Refresh and check account status"""
    user_id = query.from_user.id
    
    await query.edit_message_text("🔄 Checking account status...")
    
    accounts = await get_user_accounts(user_id)
    active_count = 0
    inactive_count = 0
    frozen_count = 0
    
    from pyrogram import Client
    import asyncio
    
    for account in accounts:
        try:
            # Create client from session string
            app = Client(
                f"check_{account['phone_number']}",
                api_id=account['api_id'],
                api_hash=account['api_hash'],
                session_string=account['session_string']
            )
            
            await app.connect()
            me = await app.get_me()
            await app.disconnect()
            
            # Update account status
            accounts_collection = await get_accounts_collection()
            await accounts_collection.update_one(
                {"_id": account["_id"]},
                {
                    "$set": {
                        "is_active": True,
                        "is_frozen": False,
                        "first_name": me.first_name,
                        "last_name": me.last_name,
                        "username": me.username,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            active_count += 1
            
        except Exception as e:
            logger.error(f"Account check failed for {account['phone_number']}: {e}")
            
            # Update as inactive
            accounts_collection = await get_accounts_collection()
            await accounts_collection.update_one(
                {"_id": account["_id"]},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            inactive_count += 1
            
            # Check if account is frozen
            if "FLOOD_WAIT" in str(e) or "420" in str(e):
                await accounts_collection.update_one(
                    {"_id": account["_id"]},
                    {"$set": {"is_frozen": True}}
                )
                frozen_count += 1
    
    # Show results
    keyboard = []
    if inactive_count > 0:
        keyboard.append([InlineKeyboardButton(
            "🗑️ Remove Inactive Accounts",
            callback_data="user_remove_inactive"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="user_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ **Account Refresh Complete**\n\n"
        f"🟢 Active: {active_count}\n"
        f"🔴 Inactive: {inactive_count}\n"
        f"❄️ Frozen: {frozen_count}\n\n"
        f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def set_log_channel(query, context):
    """Set user's log channel"""
    user_id = query.from_user.id
    user_states[user_id] = {"action": "set_log_channel"}
    
    await query.edit_message_text(
        "📝 **Set Log Channel**\n\n"
        "Please forward a message from the channel where you want to receive logs,\n"
        "or send the channel username (with @) or channel ID.\n\n"
        "To cancel, send /cancel",
        parse_mode="Markdown"
    )

async def remove_log_channel(query, context):
    """Remove user's log channel"""
    user_id = query.from_user.id
    
    users_collection = await get_users_collection()
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"log_channel": None}}
    )
    
    await query.edit_message_text(
        "✅ Log channel removed successfully!"
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user settings related messages"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    action = state.get("action")
    text = update.message.text
    
    if action == "set_log_channel":
        await process_log_channel_input(update, context, text)
        if user_id in user_states:
            del user_states[user_id]

async def process_log_channel_input(update, context, text):
    """Process log channel input"""
    user_id = update.effective_user.id
    
    try:
        # Try to parse channel ID from forwarded message
        if update.message.forward_from_chat:
            channel_id = update.message.forward_from_chat.id
            channel_name = update.message.forward_from_chat.title
        elif text.startswith("@"):
            # Get channel by username
            chat = await context.bot.get_chat(text)
            channel_id = chat.id
            channel_name = chat.title
        elif text.lstrip("-").isdigit():
            # Direct channel ID
            channel_id = int(text)
            chat = await context.bot.get_chat(channel_id)
            channel_name = chat.title
        else:
            await update.message.reply_text("❌ Invalid channel format!")
            return
        
        # Check if bot is admin in channel
        try:
            chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
            if chat_member.status not in ["administrator", "creator"]:
                await update.message.reply_text(
                    "❌ I need to be an admin in that channel to send logs!"
                )
                return
        except:
            await update.message.reply_text(
                "❌ I cannot access that channel. Make sure I'm added as admin!"
            )
            return
        
        # Save log channel
        users_collection = await get_users_collection()
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {"log_channel": channel_id},
                "$setOnInsert": {
                    "user_id": user_id,
                    "username": update.effective_user.username,
                    "first_name": update.effective_user.first_name,
                    "last_name": update.effective_user.last_name,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        await update.message.reply_text(
            f"✅ Log channel set successfully!\n"
            f"📢 Channel: {channel_name}\n"
            f"🆔 ID: {channel_id}"
        )
        
    except Exception as e:
        logger.error(f"Error setting log channel: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
