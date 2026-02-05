from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

def get_user_main_menu():
    """Get user main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📱 My Accounts", callback_data="user_accounts")],
        [InlineKeyboardButton("🗑️ Remove Account", callback_data="user_remove_menu")],
        [InlineKeyboardButton("🔄 Refresh Accounts", callback_data="user_refresh")],
        [InlineKeyboardButton("📝 Set Log Channel", callback_data="user_set_log")],
        [InlineKeyboardButton("❌ Remove Log Channel", callback_data="user_remove_log")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_account_list_user_keyboard(accounts: List[Dict[str, Any]], page: int, total_pages: int):
    """Get keyboard for user's account list"""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"user_page_{page-1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"user_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Account action buttons (limited to first 5 accounts per page)
    accounts_on_page = accounts[page*5:page*5+5]
    for i, account in enumerate(accounts_on_page, start=page*5+1):
        keyboard.append([
            InlineKeyboardButton(
                f"👁️ {i}. {account.get('account_name', 'Account')}",
                callback_data=f"user_view_{account['_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="user_back")])
    
    return InlineKeyboardMarkup(keyboard)

def get_remove_accounts_keyboard(accounts: List[Dict[str, Any]]):
    """Get keyboard for removing accounts"""
    keyboard = []
    
    # Bulk options
    keyboard.extend([
        [InlineKeyboardButton("🗑️ Remove All My Accounts", callback_data="user_remove_all")],
        [InlineKeyboardButton("🔢 Remove by Numbers (e.g., 1,3,5)", callback_data="user_remove_numbers")],
        [InlineKeyboardButton("❌ Remove Inactive Accounts", callback_data="user_remove_inactive")]
    ])
    
    # Individual account buttons (max 10)
    for i, account in enumerate(accounts[:10], 1):
        account_name = account.get('account_name', f'Account {i}')
        keyboard.append([
            InlineKeyboardButton(
                f"❌ {i}. {account_name}",
                callback_data=f"user_remove_single_{account['_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="user_back")])
    
    return InlineKeyboardMarkup(keyboard)

def get_refresh_result_keyboard(has_inactive: bool):
    """Get keyboard after refresh"""
    keyboard = []
    
    if has_inactive:
        keyboard.append([
            InlineKeyboardButton("🗑️ Remove Inactive Accounts", callback_data="user_remove_inactive")
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="user_back")])
    
    return InlineKeyboardMarkup(keyboard)
