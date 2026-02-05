import logging
import asyncio
import re
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import (
    check_admin, log_to_channel,
    get_user_accounts, split_list
)
from database.mongodb import get_accounts_collection
from config import Config
from pyrogram import Client
from pyrogram.errors import (
    FloodWait, UsernameInvalid, InviteHashInvalid,
    UserAlreadyParticipant, ChannelPrivate
)

config = Config()
logger = logging.getLogger(__name__)

# States for join/leave operations
join_states: Dict[int, Dict] = {}
leave_states: Dict[int, Dict] = {}
active_join_tasks: Dict[int, asyncio.Task] = {}
active_leave_tasks: Dict[int, asyncio.Task] = {}

async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /join command"""
    user_id = update.effective_user.id
    
    if not await check_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    join_states[user_id] = {
        "action": "join",
        "step": "get_target"
    }
    
    await update.message.reply_text(
        "👥 **Join Groups/Channels**\n\n"
        "Send the group/channel link or username:\n"
        "• For single group: @username or https://t.me/username\n"
        "• For chat folder: t.me/addlist/abc123\n"
        "• Multiple links separated by new line\n\n"
        "To cancel, send /cancel",
        parse_mode="Markdown"
    )

async def handle_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leave command"""
    user_id = update.effective_user.id
    
    if not await check_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    leave_states[user_id] = {
        "action": "leave",
        "step": "get_target"
    }
    
    await update.message.reply_text(
        "🚪 **Leave Groups/Channels**\n\n"
        "Send the group/channel link or username:\n"
        "• For single group: @username or https://t.me/username\n"
        "• For chat folder: t.me/addlist/abc123\n"
        "• Multiple links separated by new line\n\n"
        "To cancel, send /cancel",
        parse_mode="Markdown"
    )

async def handle_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle join callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not await check_admin(user_id):
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    if data == "join_start":
        await start_join_process(query, context)
    elif data == "join_stop":
        await stop_join_process(query, context)
    elif data == "join_back":
        await handle_join(update, context)

async def handle_leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leave callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not await check_admin(user_id):
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    if data == "leave_start":
        await start_leave_process(query, context)
    elif data == "leave_stop":
        await stop_leave_process(query, context)
    elif data == "leave_back":
        await handle_leave(update, context)

async def handle_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle join message input"""
    user_id = update.effective_user.id
    
    if user_id not in join_states:
        return
    
    state = join_states[user_id]
    step = state["step"]
    text = update.message.text.strip()
    
    try:
        if step == "get_target":
            # Parse multiple links
            links = [link.strip() for link in text.split('\n') if link.strip()]
            
            if not links:
                await update.message.reply_text("❌ Please send valid links!")
                return
            
            state["targets"] = links
            state["step"] = "select_accounts"
            
            # Show account selection options
            keyboard = [
                [InlineKeyboardButton("✅ All Active Accounts", callback_data="join_all_accounts")],
                [InlineKeyboardButton("🔢 Select Accounts", callback_data="join_select_accounts")],
                [InlineKeyboardButton("📱 My Accounts Only", callback_data="join_my_accounts")],
                [InlineKeyboardButton("❌ Cancel", callback_data="join_cancel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            links_text = "\n".join([f"• {link}" for link in links[:5]])
            if len(links) > 5:
                links_text += f"\n• ... and {len(links)-5} more"
            
            await update.message.reply_text(
                f"✅ **Targets Set**\n\n"
                f"{links_text}\n\n"
                f"Total: {len(links)} targets\n\n"
                f"Now select which accounts to use:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Join message error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in join_states:
            del join_states[user_id]

async def handle_leave_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leave message input"""
    user_id = update.effective_user.id
    
    if user_id not in leave_states:
        return
    
    state = leave_states[user_id]
    step = state["step"]
    text = update.message.text.strip()
    
    try:
        if step == "get_target":
            # Parse multiple links
            links = [link.strip() for link in text.split('\n') if link.strip()]
            
            if not links:
                await update.message.reply_text("❌ Please send valid links!")
                return
            
            state["targets"] = links
            state["step"] = "select_accounts"
            
            # Show account selection options
            keyboard = [
                [InlineKeyboardButton("✅ All Active Accounts", callback_data="leave_all_accounts")],
                [InlineKeyboardButton("🔢 Select Accounts", callback_data="leave_select_accounts")],
                [InlineKeyboardButton("📱 My Accounts Only", callback_data="leave_my_accounts")],
                [InlineKeyboardButton("❌ Cancel", callback_data="leave_cancel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            links_text = "\n".join([f"• {link}" for link in links[:5]])
            if len(links) > 5:
                links_text += f"\n• ... and {len(links)-5} more"
            
            await update.message.reply_text(
                f"✅ **Targets Set**\n\n"
                f"{links_text}\n\n"
                f"Total: {len(links)} targets\n\n"
                f"Now select which accounts to use:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Leave message error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in leave_states:
            del leave_states[user_id]

async def start_join_process(query, context):
    """Start joining process"""
    user_id = query.from_user.id
    
    if user_id not in join_states:
        await query.edit_message_text("❌ No join targets set!")
        return
    
    state = join_states[user_id]
    targets = state.get("targets", [])
    
    # Get accounts (for now, use all active accounts)
    accounts_collection = await get_accounts_collection()
    cursor = accounts_collection.find({"is_active": True, "is_deleted": False})
    accounts = await cursor.to_list(length=None)
    
    if not accounts:
        await query.edit_message_text("❌ No active accounts found!")
        return
    
    # Start join task
    task = asyncio.create_task(
        join_targets_task(context, accounts, targets, user_id)
    )
    active_join_tasks[user_id] = task
    
    await query.edit_message_text(
        f"🚀 **Starting Join Process**\n\n"
        f"👥 Accounts: {len(accounts)}\n"
        f"🎯 Targets: {len(targets)}\n"
        f"📊 Total operations: {len(accounts) * len(targets)}\n\n"
        f"⏳ This may take a while...\n"
        f"Use /stop to stop the process.",
        parse_mode="Markdown"
    )

async def start_leave_process(query, context):
    """Start leaving process"""
    user_id = query.from_user.id
    
    if user_id not in leave_states:
        await query.edit_message_text("❌ No leave targets set!")
        return
    
    state = leave_states[user_id]
    targets = state.get("targets", [])
    
    # Get accounts (for now, use all active accounts)
    accounts_collection = await get_accounts_collection()
    cursor = accounts_collection.find({"is_active": True, "is_deleted": False})
    accounts = await cursor.to_list(length=None)
    
    if not accounts:
        await query.edit_message_text("❌ No active accounts found!")
        return
    
    # Start leave task
    task = asyncio.create_task(
        leave_targets_task(context, accounts, targets, user_id)
    )
    active_leave_tasks[user_id] = task
    
    await query.edit_message_text(
        f"🚀 **Starting Leave Process**\n\n"
        f"👥 Accounts: {len(accounts)}\n"
        f"🎯 Targets: {len(targets)}\n"
        f"📊 Total operations: {len(accounts) * len(targets)}\n\n"
        f"⏳ This may take a while...\n"
        f"Use /stop to stop the process.",
        parse_mode="Markdown"
    )

async def join_targets_task(context, accounts, targets, user_id):
    """Task to join multiple targets from multiple accounts"""
    successful_joins = 0
    failed_joins = 0
    total_operations = len(accounts) * len(targets)
    completed_operations = 0
    
    start_time = datetime.now()
    
    # Log start
    if config.JOIN_LOG_CHANNEL:
        await log_to_channel(
            context.bot,
            config.JOIN_LOG_CHANNEL,
            f"🚀 **Join Process Started**\n\n"
            f"👤 Admin: {user_id}\n"
            f"👥 Accounts: {len(accounts)}\n"
            f"🎯 Targets: {len(targets)}\n"
            f"📊 Total: {total_operations}\n"
            f"⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    for account in accounts:
        # Check if task was stopped
        if user_id not in active_join_tasks:
            break
        
        account_success = 0
        account_failed = 0
        
        for target in targets:
            try:
                # Check if task was stopped
                if user_id not in active_join_tasks:
                    break
                
                result = await join_single_target(account, target)
                
                if result:
                    account_success += 1
                    successful_joins += 1
                    
                    # Log successful join
                    if config.JOIN_LOG_CHANNEL:
                        await log_to_channel(
                            context.bot,
                            config.JOIN_LOG_CHANNEL,
                            f"✅ **Join Successful**\n\n"
                            f"👤 Account: {account.get('account_name', 'N/A')}\n"
                            f"📱 Phone: {account.get('phone_number', 'N/A')}\n"
                            f"🎯 Target: {target}\n"
                            f"📊 Progress: {account_success+account_failed}/{len(targets)}"
                        )
                else:
                    account_failed += 1
                    failed_joins += 1
                
                completed_operations += 1
                
                # Delay between joins
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Join error for {account.get('phone_number')} -> {target}: {e}")
                account_failed += 1
                failed_joins += 1
                completed_operations += 1
                await asyncio.sleep(5)
        
        # Delay between accounts
        await asyncio.sleep(3)
    
    # Clean up
    if user_id in active_join_tasks:
        del active_join_tasks[user_id]
    
    if user_id in join_states:
        del join_states[user_id]
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Send completion summary
    message = (
        f"✅ **Join Process Complete**\n\n"
        f"📊 **Statistics:**\n"
        f"✅ Successful: {successful_joins}\n"
        f"❌ Failed: {failed_joins}\n"
        f"📈 Total attempts: {completed_operations}\n"
        f"⏱️ Duration: {duration:.2f} seconds\n\n"
        f"🎯 **Targets:** {len(targets)}\n"
        f"👥 **Accounts:** {len(accounts)}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="Markdown"
        )
    except:
        pass
    
    # Log completion
    if config.JOIN_LOG_CHANNEL:
        await log_to_channel(
            context.bot,
            config.JOIN_LOG_CHANNEL,
            f"🏁 **Join Process Complete**\n\n"
            f"👤 Admin: {user_id}\n"
            f"✅ Successful: {successful_joins}\n"
            f"❌ Failed: {failed_joins}\n"
            f"⏱️ Duration: {duration:.2f}s\n"
            f"🏁 Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

async def leave_targets_task(context, accounts, targets, user_id):
    """Task to leave multiple targets from multiple accounts"""
    successful_leaves = 0
    failed_leaves = 0
    total_operations = len(accounts) * len(targets)
    completed_operations = 0
    
    start_time = datetime.now()
    
    # Log start
    if config.LEAVE_LOG_CHANNEL:
        await log_to_channel(
            context.bot,
            config.LEAVE_LOG_CHANNEL,
            f"🚀 **Leave Process Started**\n\n"
            f"👤 Admin: {user_id}\n"
            f"👥 Accounts: {len(accounts)}\n"
            f"🎯 Targets: {len(targets)}\n"
            f"📊 Total: {total_operations}\n"
            f"⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    for account in accounts:
        # Check if task was stopped
        if user_id not in active_leave_tasks:
            break
        
        account_success = 0
        account_failed = 0
        
        for target in targets:
            try:
                # Check if task was stopped
                if user_id not in active_leave_tasks:
                    break
                
                result = await leave_single_target(account, target)
                
                if result:
                    account_success += 1
                    successful_leaves += 1
                    
                    # Log successful leave
                    if config.LEAVE_LOG_CHANNEL:
                        await log_to_channel(
                            context.bot,
                            config.LEAVE_LOG_CHANNEL,
                            f"✅ **Leave Successful**\n\n"
                            f"👤 Account: {account.get('account_name', 'N/A')}\n"
                            f"📱 Phone: {account.get('phone_number', 'N/A')}\n"
                            f"🎯 Target: {target}\n"
                            f"📊 Progress: {account_success+account_failed}/{len(targets)}"
                        )
                else:
                    account_failed += 1
                    failed_leaves += 1
                
                completed_operations += 1
                
                # Delay between leaves
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Leave error for {account.get('phone_number')} -> {target}: {e}")
                account_failed += 1
                failed_leaves += 1
                completed_operations += 1
                await asyncio.sleep(5)
        
        # Delay between accounts
        await asyncio.sleep(3)
    
    # Clean up
    if user_id in active_leave_tasks:
        del active_leave_tasks[user_id]
    
    if user_id in leave_states:
        del leave_states[user_id]
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Send completion summary
    message = (
        f"✅ **Leave Process Complete**\n\n"
        f"📊 **Statistics:**\n"
        f"✅ Successful: {successful_leaves}\n"
        f"❌ Failed: {failed_leaves}\n"
        f"📈 Total attempts: {completed_operations}\n"
        f"⏱️ Duration: {duration:.2f} seconds\n\n"
        f"🎯 **Targets:** {len(targets)}\n"
        f"👥 **Accounts:** {len(accounts)}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="Markdown"
        )
    except:
        pass
    
    # Log completion
    if config.LEAVE_LOG_CHANNEL:
        await log_to_channel(
            context.bot,
            config.LEAVE_LOG_CHANNEL,
            f"🏁 **Leave Process Complete**\n\n"
            f"👤 Admin: {user_id}\n"
            f"✅ Successful: {successful_leaves}\n"
            f"❌ Failed: {failed_leaves}\n"
            f"⏱️ Duration: {duration:.2f}s\n"
            f"🏁 Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

async def join_single_target(account, target):
    """Join a single target from an account"""
    try:
        # Create Pyrogram client
        app = Client(
            f"join_{account['phone_number']}",
            api_id=account['api_id'],
            api_hash=account['api_hash'],
            session_string=account['session_string']
        )
        
        await app.connect()
        
        # Check if it's a chat folder link
        if "addlist" in target:
            # Handle chat folder join
            await join_chat_folder(app, target)
        else:
            # Handle regular group/channel join
            await join_group_channel(app, target)
        
        await app.disconnect()
        return True
        
    except FloodWait as e:
        logger.warning(f"Flood wait for {account['phone_number']}: {e.value}s")
        await asyncio.sleep(e.value)
        return False
    except (UsernameInvalid, InviteHashInvalid):
        logger.warning(f"Invalid target for {account['phone_number']}: {target}")
        return False
    except UserAlreadyParticipant:
        logger.info(f"Already in group: {account['phone_number']} -> {target}")
        return True
    except ChannelPrivate:
        logger.warning(f"Private channel: {account['phone_number']} -> {target}")
        return False
    except Exception as e:
        logger.error(f"Join failed for {account['phone_number']}: {e}")
        return False

async def leave_single_target(account, target):
    """Leave a single target from an account"""
    try:
        # Create Pyrogram client
        app = Client(
            f"leave_{account['phone_number']}",
            api_id=account['api_id'],
            api_hash=account['api_hash'],
            session_string=account['session_string']
        )
        
        await app.connect()
        
        # Check if it's a chat folder link
        if "addlist" in target:
            # Handle chat folder leave
            await leave_chat_folder(app, target)
        else:
            # Handle regular group/channel leave
            await leave_group_channel(app, target)
        
        await app.disconnect()
        return True
        
    except FloodWait as e:
        logger.warning(f"Flood wait for {account['phone_number']}: {e.value}s")
        await asyncio.sleep(e.value)
        return False
    except Exception as e:
        logger.error(f"Leave failed for {account['phone_number']}: {e}")
        return False

async def join_group_channel(app, target):
    """Join a group or channel"""
    # Clean target
    if target.startswith("https://t.me/"):
        target = target.replace("https://t.me/", "")
    
    if target.startswith("@"):
        target = target[1:]
    
    # Join the chat
    chat = await app.join_chat(target)
    return chat

async def join_chat_folder(app, folder_link):
    """Join all chats in a chat folder"""
    # Extract hash from link
    hash_match = re.search(r"addlist/([a-zA-Z0-9_-]+)", folder_link)
    if not hash_match:
        raise ValueError("Invalid chat folder link")
    
    folder_hash = hash_match.group(1)
    
    # Get chat folder
    try:
        folder = await app.get_chat_folder(folder_hash)
        
        # Join all chats in folder
        for chat in folder.chats:
            try:
                await app.join_chat(chat.id)
                await asyncio.sleep(1)  # Delay between joins
            except Exception as e:
                logger.error(f"Failed to join chat {chat.id}: {e}")
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process chat folder: {e}")
        return False

async def leave_group_channel(app, target):
    """Leave a group or channel"""
    # Clean target
    if target.startswith("https://t.me/"):
        target = target.replace("https://t.me/", "")
    
    if target.startswith("@"):
        target = target[1:]
    
    # Get chat
    chat = await app.get_chat(target)
    
    # Leave chat
    await app.leave_chat(chat.id)
    return True

async def leave_chat_folder(app, folder_link):
    """Leave all chats in a chat folder and delete folder"""
    # Extract hash from link
    hash_match = re.search(r"addlist/([a-zA-Z0-9_-]+)", folder_link)
    if not hash_match:
        raise ValueError("Invalid chat folder link")
    
    folder_hash = hash_match.group(1)
    
    try:
        # Get chat folder
        folder = await app.get_chat_folder(folder_hash)
        
        # Leave all chats in folder
        for chat in folder.chats:
            try:
                await app.leave_chat(chat.id)
                await asyncio.sleep(1)  # Delay between leaves
            except Exception as e:
                logger.error(f"Failed to leave chat {chat.id}: {e}")
                continue
        
        # Delete chat folder
        await app.delete_chat_folder(folder_hash)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process chat folder: {e}")
        return False

async def stop_join_process(query, context):
    """Stop join process"""
    user_id = query.from_user.id
    
    if user_id in active_join_tasks:
        active_join_tasks[user_id].cancel()
        del active_join_tasks[user_id]
    
    if user_id in join_states:
        del join_states[user_id]
    
    await query.edit_message_text("🛑 Join process stopped!")

async def stop_leave_process(query, context):
    """Stop leave process"""
    user_id = query.from_user.id
    
    if user_id in active_leave_tasks:
        active_leave_tasks[user_id].cancel()
        del active_leave_tasks[user_id]
    
    if user_id in leave_states:
        del leave_states[user_id]
    
    await query.edit_message_text("🛑 Leave process stopped!")
