"""
Keyboards package for Telegram Account Manager Bot
"""

from .admin_keyboard import (
    get_admin_main_menu,
    get_account_list_keyboard,
    get_remove_options_keyboard,
    get_account_settings_keyboard,
    get_settings_options_keyboard,
    get_admin_management_keyboard
)
from .user_keyboard import (
    get_user_main_menu,
    get_account_list_user_keyboard,
    get_remove_accounts_keyboard,
    get_refresh_result_keyboard
)

__all__ = [
    # Admin keyboards
    'get_admin_main_menu',
    'get_account_list_keyboard',
    'get_remove_options_keyboard',
    'get_account_settings_keyboard',
    'get_settings_options_keyboard',
    'get_admin_management_keyboard',
    
    # User keyboards
    'get_user_main_menu',
    'get_account_list_user_keyboard',
    'get_remove_accounts_keyboard',
    'get_refresh_result_keyboard',
]

# Export keyboard types for easy access
KEYBOARDS = {
    'admin': {
        'main': get_admin_main_menu,
        'account_list': get_account_list_keyboard,
        'remove_options': get_remove_options_keyboard,
        'account_settings': get_account_settings_keyboard,
        'settings_options': get_settings_options_keyboard,
        'admin_management': get_admin_management_keyboard
    },
    'user': {
        'main': get_user_main_menu,
        'account_list': get_account_list_user_keyboard,
        'remove_accounts': get_remove_accounts_keyboard,
        'refresh_result': get_refresh_result_keyboard
    }
}

def create_pagination_keyboard(current_page: int, total_pages: int, prefix: str):
    """Create a standardized pagination keyboard"""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    
    if current_page > 0:
        nav_buttons.append({
            "text": "⬅️ Previous",
            "callback_data": f"{prefix}_page_{current_page-1}"
        })
    
    # Page indicator
    nav_buttons.append({
        "text": f"{current_page+1}/{total_pages}",
        "callback_data": f"{prefix}_page_current"
    })
    
    if current_page < total_pages - 1:
        nav_buttons.append({
            "text": "➡️ Next",
            "callback_data": f"{prefix}_page_{current_page+1}"
        })
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return keyboard

def create_account_selection_keyboard(accounts, prefix: str, start_idx: int = 0):
    """Create keyboard for selecting accounts"""
    keyboard = []
    
    # Group accounts 2 per row
    for i in range(0, len(accounts), 2):
        row = []
        for j in range(2):
            if i + j < len(accounts):
                account = accounts[i + j]
                account_name = account.get('account_name', f'Account {start_idx + i + j + 1}')
                row.append({
                    "text": f"{start_idx + i + j + 1}. {account_name}",
                    "callback_data": f"{prefix}_account_{account['_id']}"
                })
        if row:
            keyboard.append(row)
    
    return keyboard
