import logging
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import (
    get_user_accounts, format_account_info,
    check_admin, check_owner, log_to_channel,
    split_list, get_active_accounts_count
)
from database.mongodb import (
    get_accounts_collection, get_users_collection,
    get_config_collection, get_admin_logs_collection
)
from config import Config
from bson.objectid import ObjectId
from datetime import datetime

config = Config()
logger = logging.getLogger(__name__)

# Admin states
admin_states: Dict[int, Dict] = {}

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - Admin panel"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not await check_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use admin commands!")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Accounts", callback_data="admin_all_accounts")],
        [InlineKeyboardButton("🗑️ Remove Accounts", callback_data="admin_remove_menu")],
        [InlineKeyboardButton("🔄 Refresh Accounts", callback_data="admin_refresh")],
        [InlineKeyboardButton("📦 Set String Channel", callback_data="admin_set_string")],
        [InlineKeyboardButton("❌ Remove String Channel", callback_data="admin_remove_string")],
        [InlineKeyboardButton("👨‍💼 Admin Management", callback_data="admin_management")],
        [InlineKeyboardButton("⚙️ Account Settings", callback_data="admin_account_settings")],
        [InlineKeyboardButton("📊 Bot Statistics", callback_data="admin_stats")]
    ]
    
    # Add log channel management
    keyboard.extend([
        [InlineKeyboardButton("📝 Set Report Log", callback_data="admin_set_report_log")],
        [InlineKeyboardButton("📝 Set Send Log", callback_data="admin_set_send_log")],
        [InlineKeyboardButton("📝 Set OTP Log", callback_data="admin_set_otp_log")],
        [InlineKeyboardButton("📝 Set Join Log", callback_data="admin_set_join_log")],
        [InlineKeyboardButton("📝 Set Leave Log", callback_data="admin_set_leave_log")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 **Admin Panel**\n\n"
        "Select an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Check admin access
    if not await check_admin(user_id):
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    # Route to appropriate handler
    if data == "admin_all_accounts":
        await show_all_accounts(query, context)
    elif data == "admin_remove_menu":
        await admin_remove_menu(query, context)
    elif data == "admin_refresh":
        await admin_refresh_accounts(query, context)
    elif data == "admin_set_string":
        await set_string_channel(query, context)
    elif data == "admin_remove_string":
        await remove_string_channel(query, context)
    elif data == "admin_management":
        await admin_management_menu(query, context)
    elif data == "admin_account_settings":
        await account_settings_menu(query, context)
    elif data == "admin_stats":
        await show_bot_stats(query, context)
    elif data.startswith("admin_log_"):
        await handle_log_channel_setup(query, context, data)
    elif data.startswith("admin_action_"):
        await handle_admin_action(query, context, data)
    elif data == "admin_back":
        await handle_admin(update, context)

async def show_all_accounts(query, context):
    """Show all accounts in the system"""
    accounts_collection = await get_accounts_collection()
    users_collection = await get_users_collection()
    
    # Get pagination
    page = int(context.user_data.get("admin_account_page", 0))
    accounts_per_page = 10
    
    # Get total counts
    total_accounts = await accounts_collection.count_documents({"is_deleted": False})
    active_accounts = await accounts_collection.count_documents({
        "is_active": True,
        "is_deleted": False
    })
    
    # Get accounts for this page
    cursor = accounts_collection.find({"is_deleted": False}).skip(page * accounts_per_page).limit(accounts_per_page)
    accounts = await cursor.to_list(length=accounts_per_page)
    
    # Get user info for each account
    message = f"👥 **All Accounts**\n\n"
    message += f"📊 Total: {total_accounts} | ✅ Active: {active_accounts}\n\n"
    
    for i, account in enumerate(accounts, start=page * accounts_per_page + 1):
        # Get user info
        user = await users_collection.find_one({"user_id": account["user_id"]})
        username = user.get("username", "N/A") if user else "N/A"
        
        status = "✅" if account.get("is_active") else "❌"
        if account.get("is_frozen"):
            status = "❄️"
        
        message += f"{i}. {status} {account.get('account_name', 'N/A')}\n"
        message += f"   📞: {account.get('phone_number', 'N/A')}\n"
        message += f"   👤 User: {username} ({account['user_id']})\n\n"
    
    # Navigation buttons
    total_pages = (total_accounts + accounts_per_page - 1) // accounts_per_page
    keyboard = []
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_accounts_page_{page-1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_accounts_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("👁️ View Details", callback_data=f"admin_view_page_{page}"),
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
    ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_remove_menu(query, context):
    """Admin remove account menu"""
    user_id = query.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("👤 Remove User's Accounts", callback_data="admin_remove_user")],
        [InlineKeyboardButton("🗑️ Remove All Accounts", callback_data="admin_remove_all")],
        [InlineKeyboardButton("🔢 Remove by Numbers", callback_data="admin_remove_numbers")],
        [InlineKeyboardButton("❌ Remove Inactive", callback_data="admin_remove_inactive")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑️ **Admin Remove Accounts**\n\n"
        "Select removal option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_refresh_accounts(query, context):
    """Admin refresh all accounts"""
    user_id = query.from_user.id
    
    await query.edit_message_text("🔄 Refreshing all accounts... This may take a while.")
    
    accounts_collection = await get_accounts_collection()
    cursor = accounts_collection.find({"is_deleted": False})
    accounts = await cursor.to_list(length=None)
    
    total = len(accounts)
    active = 0
    inactive = 0
    frozen = 0
    
    from pyrogram import Client
    import asyncio
    
    # Process accounts in batches
    batch_size = 10
    for i in range(0, total, batch_size):
        batch = accounts[i:i+batch_size]
        tasks = []
        
        for account in batch:
            task = check_account_status(account)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, dict):
                if result["status"] == "active":
                    active += 1
                elif result["status"] == "frozen":
                    frozen += 1
                    inactive += 1
                else:
                    inactive += 1
                
                # Update database
                await accounts_collection.update_one(
                    {"_id": batch[j]["_id"]},
                    {
                        "$set": {
                            "is_active": result["status"] == "active",
                            "is_frozen": result["status"] == "frozen",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
    
    # Log the action
    await log_admin_action(
        user_id,
        "refresh_accounts",
        details={
            "total": total,
            "active": active,
            "inactive": inactive,
            "frozen": frozen
        }
    )
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Remove Inactive", callback_data="admin_remove_inactive")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ **Account Refresh Complete**\n\n"
        f"📊 Total Accounts: {total}\n"
        f"🟢 Active: {active}\n"
        f"🔴 Inactive: {inactive}\n"
        f"❄️ Frozen: {frozen}\n\n"
        f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def check_account_status(account):
    """Check individual account status"""
    from pyrogram import Client
    
    try:
        app = Client(
            f"check_{account['phone_number']}",
            api_id=account['api_id'],
            api_hash=account['api_hash'],
            session_string=account['session_string']
        )
        
        await app.connect()
        await app.get_me()
        await app.disconnect()
        
        return {"status": "active"}
        
    except Exception as e:
        error_str = str(e)
        if "FLOOD_WAIT" in error_str or "420" in error_str:
            return {"status": "frozen"}
        else:
            return {"status": "inactive"}

async def set_string_channel(query, context):
    """Set string storage channel"""
    user_id = query.from_user.id
    admin_states[user_id] = {"action": "set_string_channel"}
    
    await query.edit_message_text(
        "📦 **Set String Channel**\n\n"
        "Please forward a message from the channel where you want to store session strings,\n"
        "or send the channel username (with @) or channel ID.\n\n"
        "To cancel, send /cancel",
        parse_mode="Markdown"
    )

async def remove_string_channel(query, context):
    """Remove string channel"""
    config_collection = await get_config_collection()
    await config_collection.update_one(
        {},
        {"$set": {"string_channel": None}},
        upsert=True
    )
    
    # Update config
    config.STRING_CHANNEL = None
    
    await query.edit_message_text(
        "✅ String channel removed successfully!"
    )

async def admin_management_menu(query, context):
    """Admin management menu"""
    user_id = query.from_user.id
    
    # Check if user is owner
    if not await check_owner(user_id):
        await query.edit_message_text("❌ Only owner can manage admins!")
        return
    
    config_collection = await get_config_collection()
    config_data = await config_collection.find_one({})
    admins = config_data.get("admins", []) if config_data else []
    
    # Get admin user info
    users_collection = await get_users_collection()
    admin_users = []
    
    for admin_id in admins:
        user = await users_collection.find_one({"user_id": admin_id})
        if user:
            admin_users.append(f"👤 {user.get('first_name', 'Unknown')} (@{user.get('username', 'N/A')}) - {admin_id}")
        else:
            admin_users.append(f"👤 Unknown User - {admin_id}")
    
    admin_list = "\n".join(admin_users) if admin_users else "No admins yet"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")],
        [InlineKeyboardButton("➖ Remove Admin", callback_data="admin_remove")],
        [InlineKeyboardButton("📋 List Admins", callback_data="admin_list")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👨‍💼 **Admin Management**\n\n"
        f"Current Admins:\n{admin_list}\n\n"
        f"Select an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def account_settings_menu(query, context):
    """Account settings modification menu"""
    user_id = query.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("👤 Single Account", callback_data="admin_single_account")],
        [InlineKeyboardButton("👥 All Accounts", callback_data="admin_all_accounts_set")],
        [InlineKeyboardButton("🔢 Multiple Accounts", callback_data="admin_multiple_accounts")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ **Account Settings**\n\n"
        "Select accounts to modify:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_bot_stats(query, context):
    """Show bot statistics"""
    accounts_collection = await get_accounts_collection()
    users_collection = await get_users_collection()
    
    # Get counts
    total_accounts = await accounts_collection.count_documents({"is_deleted": False})
    active_accounts = await accounts_collection.count_documents({
        "is_active": True,
        "is_deleted": False
    })
    frozen_accounts = await accounts_collection.count_documents({
        "is_frozen": True,
        "is_deleted": False
    })
    total_users = await users_collection.count_documents({})
    admin_users = await users_collection.count_documents({"is_admin": True})
    
    # Get recent activity
    recent_accounts = await accounts_collection.count_documents({
        "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
    })
    
    message = (
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"👨‍💼 Admins: {admin_users}\n"
        f"📱 Total Accounts: {total_accounts}\n"
        f"🟢 Active Accounts: {active_accounts}\n"
        f"❄️ Frozen Accounts: {frozen_accounts}\n"
        f"📈 New Today: {recent_accounts}\n\n"
        f"⚙️ Bot Uptime: N/A\n"
        f"🔄 Last Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_stats_refresh")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_log_channel_setup(query, context, data):
    """Handle log channel setup"""
    user_id = query.from_user.id
    log_type = data.replace("admin_log_", "").replace("set_", "")
    
    admin_states[user_id] = {
        "action": f"set_{log_type}_log",
        "log_type": log_type
    }
    
    log_names = {
        "report": "Report Log",
        "send": "Send Log",
        "otp": "OTP Log",
        "join": "Join Log",
        "leave": "Leave Log"
    }
    
    log_name = log_names.get(log_type, log_type.title())
    
    await query.edit_message_text(
        f"📝 **Set {log_name} Channel**\n\n"
        "Please forward a message from the channel,\n"
        "or send the channel username (with @) or channel ID.\n\n"
        "To cancel, send /cancel",
        parse_mode="Markdown"
    )

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin-related messages"""
    user_id = update.effective_user.id
    
    if user_id not in admin_states:
        return
    
    state = admin_states[user_id]
    action = state.get("action")
    text = update.message.text
    
    if action == "set_string_channel":
        await process_string_channel_input(update, context, text)
    elif action.startswith("set_") and action.endswith("_log"):
        await process_log_channel_input_admin(update, context, text, state)
    elif action == "add_admin":
        await process_add_admin(update, context, text)
    elif action == "remove_admin":
        await process_remove_admin(update, context, text)
    
    # Clear state after processing
    if user_id in admin_states:
        del admin_states[user_id]

async def process_string_channel_input(update, context, text):
    """Process string channel input"""
    try:
        # Get channel info
        if update.message.forward_from_chat:
            channel_id = update.message.forward_from_chat.id
            channel_name = update.message.forward_from_chat.title
        elif text.startswith("@"):
            chat = await context.bot.get_chat(text)
            channel_id = chat.id
            channel_name = chat.title
        elif text.lstrip("-").isdigit():
            channel_id = int(text)
            chat = await context.bot.get_chat(channel_id)
            channel_name = chat.title
        else:
            await update.message.reply_text("❌ Invalid channel format!")
            return
        
        # Check bot permissions
        try:
            chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
            if chat_member.status not in ["administrator", "creator"]:
                await update.message.reply_text("❌ I need to be an admin in that channel!")
                return
        except:
            await update.message.reply_text("❌ Cannot access channel. Add me as admin first!")
            return
        
        # Save to database
        config_collection = await get_config_collection()
        await config_collection.update_one(
            {},
            {"$set": {"string_channel": channel_id}},
            upsert=True
        )
        
        # Update config
        config.STRING_CHANNEL = channel_id
        
        await update.message.reply_text(
            f"✅ String channel set successfully!\n"
            f"📢 Channel: {channel_name}\n"
            f"🆔 ID: {channel_id}"
        )
        
        # Log action
        await log_admin_action(
            update.effective_user.id,
            "set_string_channel",
            details={"channel_id": channel_id, "channel_name": channel_name}
        )
        
    except Exception as e:
        logger.error(f"Error setting string channel: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def process_log_channel_input_admin(update, context, text, state):
    """Process log channel input for admin"""
    try:
        # Get channel info
        if update.message.forward_from_chat:
            channel_id = update.message.forward_from_chat.id
            channel_name = update.message.forward_from_chat.title
        elif text.startswith("@"):
            chat = await context.bot.get_chat(text)
            channel_id = chat.id
            channel_name = chat.title
        elif text.lstrip("-").isdigit():
            channel_id = int(text)
            chat = await context.bot.get_chat(channel_id)
            channel_name = chat.title
        else:
            await update.message.reply_text("❌ Invalid channel format!")
            return
        
        # Check bot permissions
        try:
            chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
            if chat_member.status not in ["administrator", "creator"]:
                await update.message.reply_text("❌ I need to be an admin in that channel!")
                return
        except:
            await update.message.reply_text("❌ Cannot access channel. Add me as admin first!")
            return
        
        # Save to database
        config_collection = await get_config_collection()
        log_type = state.get("log_type")
        
        update_data = {f"{log_type}_log_channel": channel_id}
        await config_collection.update_one({}, {"$set": update_data}, upsert=True)
        
        # Update config
        if log_type == "report":
            config.REPORT_LOG_CHANNEL = channel_id
        elif log_type == "send":
            config.SEND_LOG_CHANNEL = channel_id
        elif log_type == "otp":
            config.OTP_LOG_CHANNEL = channel_id
        elif log_type == "join":
            config.JOIN_LOG_CHANNEL = channel_id
        elif log_type == "leave":
            config.LEAVE_LOG_CHANNEL = channel_id
        
        await update.message.reply_text(
            f"✅ {log_type.title()} log channel set successfully!\n"
            f"📢 Channel: {channel_name}\n"
            f"🆔 ID: {channel_id}"
        )
        
        # Log action
        await log_admin_action(
            update.effective_user.id,
            f"set_{log_type}_log",
            details={"channel_id": channel_id, "channel_name": channel_name}
        )
        
    except Exception as e:
        logger.error(f"Error setting log channel: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def log_admin_action(admin_id: int, action: str, details: Dict = None):
    """Log admin actions"""
    admin_logs_collection = await get_admin_logs_collection()
    
    log_entry = {
        "admin_id": admin_id,
        "action": action,
        "details": details or {},
        "created_at": datetime.utcnow()
    }
    
    await admin_logs_collection.insert_one(log_entry)
