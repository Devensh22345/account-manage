import logging
import asyncio
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
from pyrogram.errors import FloodWait

config = Config()
logger = logging.getLogger(__name__)

# OTP states
otp_states: Dict[int, Dict] = {}
active_otp_tasks: Dict[int, asyncio.Task] = {}

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /otp command"""
    user_id = update.effective_user.id
    
    if not await check_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📱 Get OTP from Account", callback_data="otp_single")],
        [InlineKeyboardButton("📋 Get All OTPs", callback_data="otp_all")],
        [InlineKeyboardButton("🔄 Refresh OTPs", callback_data="otp_refresh")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📲 **OTP Manager**\n\n"
        "Select an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_otp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not await check_admin(user_id):
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    if data == "otp_single":
        await select_account_for_otp(query, context)
    elif data == "otp_all":
        await get_all_otps(query, context)
    elif data == "otp_refresh":
        await refresh_otps(query, context)
    elif data.startswith("otp_account_"):
        await get_account_otp(query, context, data)
    elif data == "otp_back":
        await handle_otp(update, context)

async def select_account_for_otp(query, context):
    """Select account to get OTP from"""
    user_id = query.from_user.id
    
    # Get all accounts
    accounts_collection = await get_accounts_collection()
    cursor = accounts_collection.find({"is_active": True, "is_deleted": False})
    accounts = await cursor.to_list(length=None)
    
    if not accounts:
        await query.edit_message_text("❌ No active accounts found!")
        return
    
    # Create keyboard with accounts (paginated)
    page = int(context.user_data.get("otp_page", 0))
    accounts_per_page = 8
    
    total_pages = (len(accounts) + accounts_per_page - 1) // accounts_per_page
    start_idx = page * accounts_per_page
    end_idx = min(start_idx + accounts_per_page, len(accounts))
    
    keyboard = []
    
    # Account buttons (2 per row)
    accounts_page = accounts[start_idx:end_idx]
    for i in range(0, len(accounts_page), 2):
        row = []
        for j in range(2):
            if i + j < len(accounts_page):
                account = accounts_page[i + j]
                btn_text = f"{start_idx + i + j + 1}. {account.get('account_name', 'Account')}"
                row.append(
                    InlineKeyboardButton(
                        btn_text,
                        callback_data=f"otp_account_{account['_id']}"
                    )
                )
        if row:
            keyboard.append(row)
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"otp_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="otp_page_current"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"otp_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="otp_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📱 **Select Account for OTP**\n\n"
        f"Total active accounts: {len(accounts)}\n"
        f"Page {page+1} of {total_pages}\n\n"
        f"Select an account:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def get_account_otp(query, context, data):
    """Get OTP from specific account"""
    user_id = query.from_user.id
    
    # Extract account ID
    account_id = data.replace("otp_account_", "")
    
    accounts_collection = await get_accounts_collection()
    account = await accounts_collection.find_one({"_id": account_id})
    
    if not account:
        await query.edit_message_text("❌ Account not found!")
        return
    
    await query.edit_message_text(f"🔍 Checking OTP for {account.get('account_name')}...")
    
    # Get OTP
    otp_info = await get_single_account_otp(account)
    
    if otp_info:
        message = (
            f"📲 **OTP Information**\n\n"
            f"🏷️ Account: {account.get('account_name', 'N/A')}\n"
            f"📱 Phone: {account.get('phone_number', 'N/A')}\n\n"
            f"🔢 **Recent OTPs:**\n"
        )
        
        for i, otp in enumerate(otp_info[:5], 1):
            message += f"{i}. {otp.get('code', 'N/A')} - {otp.get('time', 'N/A')}\n"
        
        if len(otp_info) > 5:
            message += f"... and {len(otp_info)-5} more\n"
        
        # Add forward button if OTP available
        keyboard = []
        if otp_info and "code" in otp_info[0]:
            keyboard.append([
                InlineKeyboardButton("📩 Forward Latest OTP", callback_data=f"otp_forward_{account_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="otp_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Log to OTP channel
        if config.OTP_LOG_CHANNEL and otp_info:
            await log_to_channel(
                context.bot,
                config.OTP_LOG_CHANNEL,
                f"📲 **OTP Retrieved**\n\n"
                f"👤 Admin: {user_id}\n"
                f"🏷️ Account: {account.get('account_name', 'N/A')}\n"
                f"📱 Phone: {account.get('phone_number', 'N/A')}\n"
                f"🔢 Latest OTP: {otp_info[0].get('code', 'N/A')}"
            )
    else:
        await query.edit_message_text(
            f"❌ No OTP found for {account.get('account_name')}!\n"
            f"The account might not have received any OTPs recently."
        )

async def get_all_otps(query, context):
    """Get OTPs from all accounts"""
    user_id = query.from_user.id
    
    await query.edit_message_text("📋 Fetching OTPs from all accounts...")
    
    # Get all accounts
    accounts_collection = await get_accounts_collection()
    cursor = accounts_collection.find({"is_active": True, "is_deleted": False})
    accounts = await cursor.to_list(length=None)
    
    if not accounts:
        await query.edit_message_text("❌ No active accounts found!")
        return
    
    # Start task to get all OTPs
    task = asyncio.create_task(
        get_all_otps_task(context, accounts, user_id)
    )
    active_otp_tasks[user_id] = task
    
    await query.edit_message_text(
        f"🚀 **Fetching OTPs from {len(accounts)} accounts**\n\n"
        f"⏳ This may take a while...\n"
        f"Results will be sent here.",
        parse_mode="Markdown"
    )

async def get_all_otps_task(context, accounts, user_id):
    """Task to get OTPs from all accounts"""
    otp_results = []
    successful = 0
    failed = 0
    
    for account in accounts:
        try:
            # Check if task was stopped
            if user_id not in active_otp_tasks:
                break
            
            otp_info = await get_single_account_otp(account)
            
            if otp_info:
                otp_results.append({
                    "account": account,
                    "otps": otp_info
                })
                successful += 1
            else:
                failed += 1
            
            # Delay between accounts
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"OTP fetch error for {account.get('phone_number')}: {e}")
            failed += 1
            await asyncio.sleep(5)
    
    # Clean up
    if user_id in active_otp_tasks:
        del active_otp_tasks[user_id]
    
    # Send results
    if not otp_results:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ No OTPs found in any account!"
        )
        return
    
    # Group results and send
    for i in range(0, len(otp_results), 10):
        batch = otp_results[i:i+10]
        
        message = f"📋 **OTP Results** ({i+1}-{i+len(batch)} of {len(otp_results)})\n\n"
        
        for j, result in enumerate(batch, start=i+1):
            account = result["account"]
            otps = result["otps"]
            
            latest_otp = otps[0].get("code", "None") if otps else "None"
            
            message += (
                f"{j}. **{account.get('account_name', 'Account')}**\n"
                f"   📱: {account.get('phone_number', 'N/A')}\n"
                f"   🔢 Latest OTP: {latest_otp}\n"
                f"   📅 OTPs found: {len(otps)}\n\n"
            )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
        except:
            pass
        
        await asyncio.sleep(1)
    
    # Send summary
    summary = (
        f"✅ **OTP Fetch Complete**\n\n"
        f"📊 Statistics:\n"
        f"✅ Successful: {successful}\n"
        f"❌ Failed: {failed}\n"
        f"📈 Total accounts: {len(accounts)}\n"
        f"🔢 Accounts with OTPs: {len(otp_results)}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=summary,
            parse_mode="Markdown"
        )
    except:
        pass

async def refresh_otps(query, context):
    """Refresh and get latest OTPs"""
    user_id = query.from_user.id
    
    await query.edit_message_text("🔄 Refreshing OTPs...")
    
    # This would typically involve:
    # 1. Requesting new OTPs from services
    # 2. Checking for new messages
    # 3. Updating OTP cache
    
    # For now, just get fresh OTPs
    await get_all_otps(query, context)

async def get_single_account_otp(account):
    """Get OTP from a single account"""
    try:
        # Create Pyrogram client
        app = Client(
            f"otp_{account['phone_number']}",
            api_id=account['api_id'],
            api_hash=account['api_hash'],
            session_string=account['session_string']
        )
        
        await app.connect()
        
        # Get recent messages (last 50)
        otp_messages = []
        
        # Check different sources for OTPs
        sources = [
            ("Telegram", "telegram"),
            ("Service", "service_notifications"),
        ]
        
        for source_name, source in sources:
            try:
                # Get messages from source
                async for message in app.get_chat_history(source, limit=20):
                    if message.text:
                        # Look for OTP patterns
                        otp = extract_otp_from_text(message.text)
                        if otp:
                            otp_messages.append({
                                "code": otp,
                                "time": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                                "source": source_name,
                                "text": message.text[:50] + "..."
                            })
            except:
                continue
        
        await app.disconnect()
        
        # Sort by time (newest first)
        otp_messages.sort(key=lambda x: x["time"], reverse=True)
        
        return otp_messages[:10]  # Return top 10 OTPs
        
    except FloodWait as e:
        logger.warning(f"Flood wait for {account['phone_number']}: {e.value}s")
        await asyncio.sleep(e.value)
        return []
    except Exception as e:
        logger.error(f"OTP fetch failed for {account['phone_number']}: {e}")
        return []

def extract_otp_from_text(text: str) -> Optional[str]:
    """Extract OTP from text message"""
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
