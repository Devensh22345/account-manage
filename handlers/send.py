import logging
import asyncio
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import (
    get_user_accounts, check_admin,
    log_to_channel, split_list
)
from database.mongodb import get_accounts_collection
from config import Config
from pyrogram import Client
from pyrogram.errors import FloodWait, PeerIdInvalid, UsernameInvalid

config = Config()
logger = logging.getLogger(__name__)

# Send states
send_states: Dict[int, Dict] = {}
active_send_tasks: Dict[int, asyncio.Task] = {}

async def handle_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /send command"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not await check_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    keyboard = [
        [InlineKeyboardButton("🤖 Send to Bot", callback_data="send_bot")],
        [InlineKeyboardButton("👤 Send to User", callback_data="send_user")],
        [InlineKeyboardButton("👥 Send to Group", callback_data="send_group")],
        [InlineKeyboardButton("⏹️ Stop Sending", callback_data="send_stop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📤 **Send Messages**\n\n"
        "Select destination type:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle send callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not await check_admin(user_id):
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    if data == "send_bot":
        await send_bot_menu(query, context)
    elif data == "send_user":
        await send_user_menu(query, context)
    elif data == "send_group":
        await send_group_menu(query, context)
    elif data == "send_stop":
        await stop_sending(query, context)
    elif data.startswith("send_type_"):
        await handle_send_type(query, context, data)
    elif data == "send_back":
        await handle_send(update, context)

async def send_bot_menu(query, context):
    """Menu for sending to bot"""
    keyboard = [
        [InlineKeyboardButton("📝 Single Message", callback_data="send_bot_single")],
        [InlineKeyboardButton("📨 Multiple Messages", callback_data="send_bot_multiple")],
        [InlineKeyboardButton("⬅️ Back", callback_data="send_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🤖 **Send to Bot**\n\n"
        "Select message type:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_user_menu(query, context):
    """Menu for sending to user"""
    keyboard = [
        [InlineKeyboardButton("📝 Single Message", callback_data="send_user_single")],
        [InlineKeyboardButton("📨 Multiple Messages", callback_data="send_user_multiple")],
        [InlineKeyboardButton("⬅️ Back", callback_data="send_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 **Send to User**\n\n"
        "Select message type:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_group_menu(query, context):
    """Menu for sending to group"""
    keyboard = [
        [InlineKeyboardButton("📝 Single Message", callback_data="send_group_single")],
        [InlineKeyboardButton("📨 Multiple Messages", callback_data="send_group_multiple")],
        [InlineKeyboardButton("⬅️ Back", callback_data="send_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👥 **Send to Group**\n\n"
        "Select message type:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_send_type(query, context, data):
    """Handle send type selection"""
    user_id = query.from_user.id
    
    # Parse data: send_[bot/user/group]_[single/multiple]
    parts = data.split("_")
    if len(parts) >= 3:
        target_type = parts[1]  # bot, user, or group
        message_type = parts[2]  # single or multiple
        
        send_states[user_id] = {
            "action": "send_message",
            "target_type": target_type,
            "message_type": message_type,
            "step": "get_target"
        }
        
        target_names = {
            "bot": "bot",
            "user": "user",
            "group": "group/channel"
        }
        
        await query.edit_message_text(
            f"📤 **Send to {target_names[target_type].title()}**\n\n"
            f"Please send the {target_names[target_type]} username or link:\n"
            f"Example: @username or https://t.me/username\n\n"
            f"To cancel, send /cancel",
            parse_mode="Markdown"
        )

async def handle_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle send message process"""
    user_id = update.effective_user.id
    
    if user_id not in send_states:
        return
    
    state = send_states[user_id]
    step = state["step"]
    text = update.message.text
    
    try:
        if step == "get_target":
            # Store target
            state["target"] = text
            state["step"] = "get_message"
            
            target_type = state["target_type"]
            target_names = {
                "bot": "bot",
                "user": "user",
                "group": "group"
            }
            
            await update.message.reply_text(
                f"✅ {target_names[target_type].title()} set to: {text}\n\n"
                f"Now send the message you want to send.\n"
                f"You can send text, photo, or any other media.\n\n"
                f"To cancel, send /cancel"
            )
            
        elif step == "get_message":
            # Store message
            if update.message.text:
                state["message"] = update.message.text
                state["message_type"] = "text"
            elif update.message.photo:
                state["message"] = update.message.photo[-1].file_id
                state["message_type"] = "photo"
                if update.message.caption:
                    state["caption"] = update.message.caption
            elif update.message.video:
                state["message"] = update.message.video.file_id
                state["message_type"] = "video"
                if update.message.caption:
                    state["caption"] = update.message.caption
            elif update.message.document:
                state["message"] = update.message.document.file_id
                state["message_type"] = "document"
                if update.message.caption:
                    state["caption"] = update.message.caption
            else:
                await update.message.reply_text("❌ Unsupported message type!")
                del send_states[user_id]
                return
            
            state["step"] = "get_accounts"
            
            # Ask for account selection
            keyboard = [
                [InlineKeyboardButton("✅ All Active Accounts", callback_data="send_all_accounts")],
                [InlineKeyboardButton("🔢 Select Accounts", callback_data="send_select_accounts")],
                [InlineKeyboardButton("📱 My Accounts Only", callback_data="send_my_accounts")],
                [InlineKeyboardButton("❌ Cancel", callback_data="send_cancel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ Message saved!\n\n"
                "Now select which accounts to use:",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Send message error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in send_states:
            del send_states[user_id]

async def start_sending(update, context, account_ids):
    """Start sending messages"""
    user_id = update.effective_user.id
    
    if user_id not in send_states:
        return
    
    state = send_states[user_id]
    
    # Get accounts
    accounts_collection = await get_accounts_collection()
    accounts = []
    
    for account_id in account_ids:
        account = await accounts_collection.find_one({"_id": account_id})
        if account and account.get("is_active"):
            accounts.append(account)
    
    if not accounts:
        await update.message.reply_text("❌ No active accounts found!")
        return
    
    # Start sending task
    task = asyncio.create_task(
        send_messages_task(context, accounts, state, user_id)
    )
    active_send_tasks[user_id] = task
    
    await update.message.reply_text(
        f"🚀 Started sending to {len(accounts)} accounts!\n\n"
        f"Target: {state.get('target', 'N/A')}\n"
        f"Message type: {state.get('message_type', 'text')}\n\n"
        f"Use /stop to stop sending."
    )

async def send_messages_task(context, accounts, state, user_id):
    """Task to send messages from multiple accounts"""
    successful = 0
    failed = 0
    total = len(accounts)
    
    start_time = datetime.now()
    
    for i, account in enumerate(accounts, 1):
        try:
            # Check if task was stopped
            if user_id not in active_send_tasks:
                break
            
            # Send message
            result = await send_single_message(account, state)
            
            if result:
                successful += 1
                
                # Log success
                if config.SEND_LOG_CHANNEL:
                    await log_to_channel(
                        context.bot,
                        config.SEND_LOG_CHANNEL,
                        f"✅ Message Sent\n\n"
                        f"👤 Account: {account.get('account_name', 'N/A')}\n"
                        f"📱 Phone: {account.get('phone_number', 'N/A')}\n"
                        f"🎯 Target: {state.get('target', 'N/A')}\n"
                        f"📊 Progress: {i}/{total}"
                    )
            else:
                failed += 1
            
            # Delay between accounts to avoid flood
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Send error for account {account.get('phone_number')}: {e}")
            failed += 1
            await asyncio.sleep(5)  # Longer delay on error
    
    # Clean up
    if user_id in active_send_tasks:
        del active_send_tasks[user_id]
    
    if user_id in send_states:
        del send_states[user_id]
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Send completion message
    message = (
        f"📤 **Sending Complete**\n\n"
        f"✅ Successful: {successful}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {total}\n"
        f"⏱️ Duration: {duration:.2f} seconds\n\n"
        f"Target: {state.get('target', 'N/A')}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="Markdown"
        )
    except:
        pass  # User might have blocked bot

async def send_single_message(account, state):
    """Send message from a single account"""
    try:
        # Create Pyrogram client
        app = Client(
            f"send_{account['phone_number']}",
            api_id=account['api_id'],
            api_hash=account['api_hash'],
            session_string=account['session_string']
        )
        
        await app.connect()
        
        target = state["target"]
        message_type = state["message_type"]
        
        # Parse target
        if target.startswith("https://t.me/"):
            target = target.replace("https://t.me/", "")
        
        # Send based on message type
        if message_type == "text":
            await app.send_message(target, state["message"])
        elif message_type == "photo":
            await app.send_photo(
                target,
                state["message"],
                caption=state.get("caption")
            )
        elif message_type == "video":
            await app.send_video(
                target,
                state["message"],
                caption=state.get("caption")
            )
        elif message_type == "document":
            await app.send_document(
                target,
                state["message"],
                caption=state.get("caption")
            )
        
        await app.disconnect()
        return True
        
    except FloodWait as e:
        logger.warning(f"Flood wait for {account['phone_number']}: {e.value}s")
        await asyncio.sleep(e.value)
        return False
    except (PeerIdInvalid, UsernameInvalid):
        logger.warning(f"Invalid target for {account['phone_number']}: {target}")
        return False
    except Exception as e:
        logger.error(f"Send failed for {account['phone_number']}: {e}")
        return False

async def stop_sending(query, context):
    """Stop sending process"""
    user_id = query.from_user.id
    
    if user_id in active_send_tasks:
        active_send_tasks[user_id].cancel()
        del active_send_tasks[user_id]
    
    if user_id in send_states:
        del send_states[user_id]
    
    await query.edit_message_text("🛑 Sending stopped successfully!")
