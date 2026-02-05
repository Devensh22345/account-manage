import logging
import asyncio
import random
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import (
    check_admin, log_to_channel,
    get_user_accounts, split_list
)
from database.mongodb import get_accounts_collection, get_report_jobs_collection
from config import Config
from pyrogram import Client
from pyrogram.errors import FloodWait, PeerIdInvalid

config = Config()
logger = logging.getLogger(__name__)

# Report states
report_states: Dict[int, Dict] = {}
active_report_tasks: Dict[int, asyncio.Task] = {}
report_reasons = [
    "Child Abuse",
    "Copyright",
    "Fake Account",
    "Fraud",
    "Harassment",
    "Hate Speech",
    "Illegal Drugs",
    "Impersonation",
    "Pornography",
    "Promotes Suicide",
    "Scam",
    "Spam",
    "Terrorism",
    "Violence",
    "Other"
]

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    user_id = update.effective_user.id
    
    if not await check_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    keyboard = [
        [InlineKeyboardButton("🤖 Report Bot", callback_data="report_bot")],
        [InlineKeyboardButton("👥 Report Group", callback_data="report_group")],
        [InlineKeyboardButton("📢 Report Channel", callback_data="report_channel")],
        [InlineKeyboardButton("👤 Report User", callback_data="report_user")],
        [InlineKeyboardButton("📝 Report Post", callback_data="report_post")],
        [InlineKeyboardButton("⏹️ Stop Reporting", callback_data="report_stop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🚨 **Report Content**\n\n"
        "Select what you want to report:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command to stop reporting"""
    user_id = update.effective_user.id
    
    if not await check_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if user_id in active_report_tasks:
        active_report_tasks[user_id].cancel()
        del active_report_tasks[user_id]
        await update.message.reply_text("🛑 Reporting stopped!")
    else:
        await update.message.reply_text("ℹ️ No active reporting process found.")

async def handle_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not await check_admin(user_id):
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    if data == "report_stop":
        await handle_stop(update, context)
        return
    
    # Parse report type
    report_type = data.replace("report_", "")
    
    if report_type in ["bot", "group", "channel", "user", "post"]:
        await start_report_process(query, context, report_type)
    elif data.startswith("report_reason_"):
        await handle_report_reason(query, context, data)
    elif data.startswith("report_accounts_"):
        await handle_report_accounts(query, context, data)
    elif data == "report_back":
        await handle_report(update, context)

async def start_report_process(query, context, report_type):
    """Start report process for a specific type"""
    user_id = query.from_user.id
    
    report_states[user_id] = {
        "action": "report",
        "type": report_type,
        "step": "get_target"
    }
    
    type_names = {
        "bot": "bot",
        "group": "group",
        "channel": "channel",
        "user": "user",
        "post": "post"
    }
    
    await query.edit_message_text(
        f"🚨 **Report {type_names[report_type].title()}**\n\n"
        f"Send the {type_names[report_type]} link, username, or ID:\n"
        f"Examples:\n"
        f"• Username: @username\n"
        f"• Link: https://t.me/username\n"
        f"• Post link: https://t.me/channel/123\n"
        f"• User ID: 123456789\n\n"
        f"To cancel, send /cancel",
        parse_mode="Markdown"
    )

async def handle_report_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report process messages"""
    user_id = update.effective_user.id
    
    if user_id not in report_states:
        return
    
    state = report_states[user_id]
    step = state["step"]
    text = update.message.text.strip()
    
    try:
        if step == "get_target":
            # Validate target
            if not text:
                await update.message.reply_text("❌ Please send a valid target!")
                return
            
            state["target"] = text
            state["step"] = "get_reason"
            
            # Show reason selection
            keyboard = []
            for i, reason in enumerate(report_reasons):
                if i % 2 == 0:
                    row = [InlineKeyboardButton(reason, callback_data=f"report_reason_{i}")]
                    if i + 1 < len(report_reasons):
                        row.append(InlineKeyboardButton(report_reasons[i+1], callback_data=f"report_reason_{i+1}"))
                    keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="report_cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Target set: {text}\n\n"
                f"Select report reason:",
                reply_markup=reply_markup
            )
            
        elif step == "get_description":
            state["description"] = text
            state["step"] = "get_count"
            
            await update.message.reply_text(
                f"✅ Description saved!\n\n"
                f"Now enter number of reports per account (1-10):\n"
                f"Recommended: 1-3 to avoid detection"
            )
            
        elif step == "get_count":
            if not text.isdigit() or not (1 <= int(text) <= 10):
                await update.message.reply_text("❌ Please enter a number between 1 and 10!")
                return
            
            state["reports_per_account"] = int(text)
            state["step"] = "select_accounts"
            
            # Show account selection
            keyboard = [
                [InlineKeyboardButton("✅ All Active Accounts", callback_data="report_accounts_all")],
                [InlineKeyboardButton("🔢 Select Accounts", callback_data="report_accounts_select")],
                [InlineKeyboardButton("📱 My Accounts Only", callback_data="report_accounts_my")],
                [InlineKeyboardButton("❌ Cancel", callback_data="report_cancel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Reports per account: {text}\n\n"
                f"Select which accounts to use:",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Report message error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in report_states:
            del report_states[user_id]

async def handle_report_reason(query, context, data):
    """Handle report reason selection"""
    user_id = query.from_user.id
    
    if user_id not in report_states:
        await query.edit_message_text("❌ Report process expired!")
        return
    
    # Get reason index from callback data
    reason_idx = int(data.replace("report_reason_", ""))
    if 0 <= reason_idx < len(report_reasons):
        report_states[user_id]["reason"] = report_reasons[reason_idx]
        report_states[user_id]["step"] = "get_description"
        
        await query.edit_message_text(
            f"✅ Reason: {report_reasons[reason_idx]}\n\n"
            f"Now send a description for the report:\n"
            f"(Optional, but recommended for better results)\n\n"
            f"To skip, send 'skip'",
            parse_mode="Markdown"
        )

async def handle_report_accounts(query, context, data):
    """Handle account selection for reporting"""
    user_id = query.from_user.id
    
    if user_id not in report_states:
        await query.edit_message_text("❌ Report process expired!")
        return
    
    account_type = data.replace("report_accounts_", "")
    state = report_states[user_id]
    
    # Get accounts based on selection
    accounts_collection = await get_accounts_collection()
    
    if account_type == "all":
        cursor = accounts_collection.find({"is_active": True, "is_deleted": False})
        accounts = await cursor.to_list(length=None)
    elif account_type == "my":
        cursor = accounts_collection.find({
            "user_id": user_id,
            "is_active": True,
            "is_deleted": False
        })
        accounts = await cursor.to_list(length=None)
    else:
        await query.edit_message_text("❌ Invalid selection!")
        return
    
    if not accounts:
        await query.edit_message_text("❌ No active accounts found!")
        return
    
    state["accounts"] = accounts
    
    # Start reporting
    await start_reporting_task(query, context, state)

async def start_reporting_task(query, context, state):
    """Start the reporting task"""
    user_id = query.from_user.id
    
    # Save report job to database
    report_jobs_collection = await get_report_jobs_collection()
    
    job_data = {
        "admin_id": user_id,
        "target_type": state["type"],
        "target_link": state["target"],
        "reason": state["reason"],
        "description": state.get("description", ""),
        "reports_per_account": state["reports_per_account"],
        "status": "running",
        "accounts_used": [acc["_id"] for acc in state["accounts"]],
        "total_reports": len(state["accounts"]) * state["reports_per_account"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    job_result = await report_jobs_collection.insert_one(job_data)
    state["job_id"] = job_result.inserted_id
    
    # Start task
    task = asyncio.create_task(
        report_target_task(context, state, user_id)
    )
    active_report_tasks[user_id] = task
    
    await query.edit_message_text(
        f"🚀 **Reporting Started**\n\n"
        f"🎯 Target: {state['target']}\n"
        f"📋 Reason: {state['reason']}\n"
        f"👥 Accounts: {len(state['accounts'])}\n"
        f"📊 Reports per account: {state['reports_per_account']}\n"
        f"📈 Total reports: {len(state['accounts']) * state['reports_per_account']}\n\n"
        f"⏳ This may take a while...\n"
        f"Use /stop to stop reporting.",
        parse_mode="Markdown"
    )

async def report_target_task(context, state, user_id):
    """Task to report target from multiple accounts"""
    successful_reports = 0
    failed_reports = 0
    total_reports = len(state["accounts"]) * state["reports_per_account"]
    
    start_time = datetime.now()
    
    # Log start
    if config.REPORT_LOG_CHANNEL:
        await log_to_channel(
            context.bot,
            config.REPORT_LOG_CHANNEL,
            f"🚀 **Reporting Started**\n\n"
            f"👤 Admin: {user_id}\n"
            f"🎯 Target: {state['target']}\n"
            f"📋 Type: {state['type']}\n"
            f"📝 Reason: {state['reason']}\n"
            f"👥 Accounts: {len(state['accounts'])}\n"
            f"📊 Total reports: {total_reports}\n"
            f"⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    for account in state["accounts"]:
        # Check if task was stopped
        if user_id not in active_report_tasks:
            break
        
        account_success = 0
        
        for i in range(state["reports_per_account"]):
            try:
                # Check if task was stopped
                if user_id not in active_report_tasks:
                    break
                
                result = await report_from_account(account, state)
                
                if result:
                    account_success += 1
                    successful_reports += 1
                else:
                    failed_reports += 1
                
                # Random delay between reports (mimic human behavior)
                delay = random.uniform(3, 8)
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Report error for {account.get('phone_number')}: {e}")
                failed_reports += 1
                await asyncio.sleep(5)
        
        # Random delay between accounts
        delay = random.uniform(5, 15)
        await asyncio.sleep(delay)
    
    # Clean up
    if user_id in active_report_tasks:
        del active_report_tasks[user_id]
    
    if user_id in report_states:
        del report_states[user_id]
    
    # Update job status
    report_jobs_collection = await get_report_jobs_collection()
    await report_jobs_collection.update_one(
        {"_id": state["job_id"]},
        {
            "$set": {
                "status": "completed",
                "total_reports": successful_reports,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Send completion summary
    message = (
        f"✅ **Reporting Complete**\n\n"
        f"📊 **Statistics:**\n"
        f"✅ Successful: {successful_reports}\n"
        f"❌ Failed: {failed_reports}\n"
        f"📈 Total attempted: {total_reports}\n"
        f"⏱️ Duration: {duration:.2f} seconds\n\n"
        f"🎯 **Target:** {state['target']}\n"
        f"📋 **Reason:** {state['reason']}"
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
    if config.REPORT_LOG_CHANNEL:
        await log_to_channel(
            context.bot,
            config.REPORT_LOG_CHANNEL,
            f"🏁 **Reporting Complete**\n\n"
            f"👤 Admin: {user_id}\n"
            f"✅ Successful: {successful_reports}\n"
            f"❌ Failed: {failed_reports}\n"
            f"⏱️ Duration: {duration:.2f}s\n"
            f"🏁 Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

async def report_from_account(account, state):
    """Report from a single account"""
    try:
        # Create Pyrogram client
        app = Client(
            f"report_{account['phone_number']}",
            api_id=account['api_id'],
            api_hash=account['api_hash'],
            session_string=account['session_string']
        )
        
        await app.connect()
        
        target = state["target"]
        report_type = state["type"]
        reason = state["reason"]
        description = state.get("description", "")
        
        # Parse target
        if target.startswith("https://t.me/"):
            target = target.replace("https://t.me/", "")
        
        if report_type == "bot":
            # Report bot
            await report_bot(app, target, reason, description)
        elif report_type in ["group", "channel"]:
            # Report group/channel
            await report_group_channel(app, target, reason, description, report_type)
        elif report_type == "user":
            # Report user
            await report_user(app, target, reason, description)
        elif report_type == "post":
            # Report post
            await report_post(app, target, reason, description)
        
        await app.disconnect()
        return True
        
    except FloodWait as e:
        logger.warning(f"Flood wait for {account['phone_number']}: {e.value}s")
        await asyncio.sleep(e.value)
        return False
    except Exception as e:
        logger.error(f"Report failed for {account['phone_number']}: {e}")
        return False

async def report_bot(app, bot_username, reason, description):
    """Report a bot"""
    # First, start the bot if not already started
    try:
        await app.send_message(bot_username, "/start")
        await asyncio.sleep(random.uniform(1, 3))
    except:
        pass
    
    # Report the bot
    # Note: Telegram Bot API doesn't have direct report method
    # We need to use inline query or contact support
    
    # Alternative: Report via Telegram support
    await app.send_message(
        "spambot",
        f"/report {bot_username} {reason}"
    )
    
    await asyncio.sleep(random.uniform(2, 5))

async def report_group_channel(app, target, reason, description, chat_type):
    """Report a group or channel"""
    try:
        # Try to join first if not already member
        try:
            chat = await app.join_chat(target)
            await asyncio.sleep(random.uniform(2, 5))
        except:
            # Already member or cannot join
            pass
        
        # Get chat
        chat = await app.get_chat(target)
        
        # Report the chat
        # Note: Actual reporting requires UI interaction
        # This is a placeholder for the actual implementation
        
        # For now, we'll use spam bot
        await app.send_message(
            "spambot",
            f"/report {chat.id} {reason}"
        )
        
        await asyncio.sleep(random.uniform(2, 5))
        
    except Exception as e:
        raise e

async def report_user(app, user_identifier, reason, description):
    """Report a user"""
    try:
        # Get user
        if user_identifier.startswith("@"):
            user = await app.get_users(user_identifier)
        else:
            # Try as user ID
            user_id = int(user_identifier)
            user = await app.get_users(user_id)
        
        # Report user
        # Placeholder for actual reporting logic
        
        await app.send_message(
            "spambot",
            f"/report {user.id} {reason}"
        )
        
        await asyncio.sleep(random.uniform(2, 5))
        
    except Exception as e:
        raise e

async def report_post(app, post_link, reason, description):
    """Report a specific post"""
    try:
        # Parse post link
        # Format: https://t.me/channel/123 or https://t.me/c/channel/123
        
        # Extract channel and message ID
        parts = post_link.split("/")
        if len(parts) >= 4:
            channel = parts[3]
            message_id = int(parts[4]) if len(parts) > 4 else None
            
            if message_id:
                # Report the message
                # Placeholder for actual reporting logic
                
                await app.send_message(
                    "spambot",
                    f"/report {channel}/{message_id} {reason}"
                )
                
                await asyncio.sleep(random.uniform(2, 5))
        
    except Exception as e:
        raise e
