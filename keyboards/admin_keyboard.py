from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

def get_admin_main_menu():
    """Get admin main menu keyboard"""
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
    
    # Add log channel management in two rows
    keyboard.extend([
        [
            InlineKeyboardButton("📝 Report Log", callback_data="admin_log_report"),
            InlineKeyboardButton("📝 Send Log", callback_data="admin_log_send")
        ],
        [
            InlineKeyboardButton("📝 OTP Log", callback_data="admin_log_otp"),
            InlineKeyboardButton("📝 Join Log", callback_data="admin_log_join"),
            InlineKeyboardButton("📝 Leave Log", callback_data="admin_log_leave")
        ]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_account_list_keyboard(accounts: List[Dict[str, Any]], page: int, total_pages: int):
    """Get keyboard for account list with pagination"""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="admin_page_current"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("👁️ View", callback_data="admin_view"),
        InlineKeyboardButton("✏️ Edit", callback_data="admin_edit"),
        InlineKeyboardButton("🗑️ Remove", callback_data="admin_remove")
    ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(keyboard)

def get_remove_options_keyboard():
    """Get keyboard for remove options"""
    keyboard = [
        [InlineKeyboardButton("👤 Remove User's Accounts", callback_data="admin_remove_user")],
        [InlineKeyboardButton("🗑️ Remove All Accounts", callback_data="admin_remove_all")],
        [InlineKeyboardButton("🔢 Remove by Numbers", callback_data="admin_remove_numbers")],
        [InlineKeyboardButton("❌ Remove Inactive", callback_data="admin_remove_inactive")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_account_settings_keyboard():
    """Get keyboard for account settings"""
    keyboard = [
        [InlineKeyboardButton("👤 Single Account", callback_data="admin_single_account")],
        [InlineKeyboardButton("👥 All Accounts", callback_data="admin_all_accounts_set")],
        [InlineKeyboardButton("🔢 Multiple Accounts", callback_data="admin_multiple_accounts")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_settings_options_keyboard():
    """Get keyboard for settings options"""
    keyboard = [
        [InlineKeyboardButton("🏷️ Change Name", callback_data="setting_name")],
        [InlineKeyboardButton("🔗 Change Username", callback_data="setting_username")],
        [InlineKeyboardButton("📝 Change Bio", callback_data="setting_bio")],
        [InlineKeyboardButton("🖼️ Change Profile Photo", callback_data="setting_pfp")],
        [InlineKeyboardButton("🔐 Two-Step Password", callback_data="setting_2fa")],
        [InlineKeyboardButton("👁️ Privacy Settings", callback_data="setting_privacy")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_management_keyboard(is_owner: bool):
    """Get keyboard for admin management"""
    keyboard = []
    
    if is_owner:
        keyboard.extend([
            [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")],
            [InlineKeyboardButton("➖ Remove Admin", callback_data="admin_remove_admin")],
            [InlineKeyboardButton("📋 List Admins", callback_data="admin_list")]
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(keyboard)
