"""
Utilities package for Telegram Account Manager Bot
"""

from .helpers import (
    setup_logging,
    log_to_channel,
    create_pyrogram_session,
    validate_phone_number,
    get_user_accounts,
    check_admin,
    check_owner,
    get_active_accounts_count,
    format_account_info,
    split_list,
    format_account_info
)
from .session_manager import (
    SessionManager,
    save_session,
    load_session,
    delete_session,
    validate_session,
    refresh_session,
    cleanup_old_sessions,
    get_session_stats
)
from .rate_limiter import (
    RateLimiter,
    rate_limiter,
    check_rate_limit,
    RATE_LIMITS,
    get_wait_time,
    reset_limits,
    get_stats as get_rate_limiter_stats
)
from .validators import (
    validate_phone_number as validate_phone,
    validate_api_id,
    validate_api_hash,
    validate_otp,
    validate_username,
    validate_channel_link,
    validate_message_content,
    validate_account_name,
    validate_email,
    validate_date_range,
    validate_numeric_range,
    validate_file_extension,
    sanitize_input
)
from .monitor import (
    BotMonitor,
    get_system_stats,
    get_bot_stats
)

__all__ = [
    # Helpers
    'setup_logging',
    'log_to_channel',
    'create_pyrogram_session',
    'validate_phone_number',
    'get_user_accounts',
    'check_admin',
    'check_owner',
    'get_active_accounts_count',
    'format_account_info',
    'split_list',
    
    # Session Manager
    'SessionManager',
    'save_session',
    'load_session',
    'delete_session',
    'validate_session',
    'refresh_session',
    'cleanup_old_sessions',
    'get_session_stats',
    
    # Rate Limiter
    'RateLimiter',
    'rate_limiter',
    'check_rate_limit',
    'RATE_LIMITS',
    'get_wait_time',
    'reset_limits',
    'get_rate_limiter_stats',
    
    # Validators
    'validate_phone',
    'validate_api_id',
    'validate_api_hash',
    'validate_otp',
    'validate_username',
    'validate_channel_link',
    'validate_message_content',
    'validate_account_name',
    'validate_email',
    'validate_date_range',
    'validate_numeric_range',
    'validate_file_extension',
    'sanitize_input',
    
    # Monitor
    'BotMonitor',
    'get_system_stats',
    'get_bot_stats',
]

# Global instances
session_manager = SessionManager()
bot_monitor = BotMonitor()

async def initialize_utils():
    """Initialize all utility modules"""
    # Setup logging
    setup_logging()
    
    # Initialize rate limiter
    await rate_limiter.reset_limits()
    
    # Clean up old sessions
    await session_manager.cleanup_old_sessions()
    
    print("✅ Utilities initialized successfully")

async def shutdown_utils():
    """Shutdown all utility modules"""
    # Save any pending data
    await session_manager.cleanup_old_sessions()
    
    print("✅ Utilities shutdown complete")

# Export utility functions grouped by category
UTILITIES = {
    'logging': {
        'setup': setup_logging,
        'log_to_channel': log_to_channel
    },
    'validation': {
        'phone': validate_phone,
        'api_id': validate_api_id,
        'api_hash': validate_api_hash,
        'otp': validate_otp,
        'username': validate_username,
        'channel_link': validate_channel_link,
        'message': validate_message_content,
        'account_name': validate_account_name,
        'email': validate_email,
        'date_range': validate_date_range,
        'numeric_range': validate_numeric_range,
        'file_extension': validate_file_extension,
        'sanitize': sanitize_input
    },
    'account': {
        'get_user_accounts': get_user_accounts,
        'get_active_accounts_count': get_active_accounts_count,
        'format_account_info': format_account_info
    },
    'auth': {
        'check_admin': check_admin,
        'check_owner': check_owner
    },
    'session': {
        'manager': session_manager,
        'save': save_session,
        'load': load_session,
        'delete': delete_session,
        'validate': validate_session,
        'refresh': refresh_session,
        'cleanup': cleanup_old_sessions,
        'stats': get_session_stats
    },
    'rate_limit': {
        'check': check_rate_limit,
        'get_wait_time': get_wait_time,
        'reset': reset_limits,
        'stats': get_rate_limiter_stats,
        'config': RATE_LIMITS
    },
    'monitor': {
        'monitor': bot_monitor,
        'system_stats': get_system_stats,
        'bot_stats': get_bot_stats
    },
    'helpers': {
        'split_list': split_list,
        'create_pyrogram_session': create_pyrogram_session,
        'validate_phone_number': validate_phone_number
    }
}
