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
    extract_otp_from_text,
    format_time_delta,
    sanitize_text
)

from .session_manager import (
    SessionManager,
    session_manager,
    save_session,
    load_session,
    delete_session,
    validate_session,
    cleanup_old_sessions,
    get_session_stats
)

# Import rate_limiter with error handling
try:
    from .rate_limiter import (
        RateLimiter,
        rate_limiter,
        check_rate_limit,
        RATE_LIMITS,
        get_wait_time,
        reset_limits,
        get_stats as get_rate_limiter_stats
    )
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    # Create dummy functions
    class DummyRateLimiter:
        async def check_user_limit(self, *args, **kwargs): return True
        async def get_wait_time(self, *args, **kwargs): return 0
    
    rate_limiter = DummyRateLimiter()
    RATE_LIMITS = {}
    
    async def check_rate_limit(*args, **kwargs): return True, None
    async def get_wait_time(*args, **kwargs): return 0
    async def reset_limits(*args, **kwargs): pass
    async def get_rate_limiter_stats(): return {}

# Import validators with error handling
try:
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
    VALIDATORS_AVAILABLE = True
except ImportError:
    VALIDATORS_AVAILABLE = False
    # Create dummy functions
    def validate_phone(*args, **kwargs): return True, None
    def validate_api_id(*args, **kwargs): return True, None
    def validate_api_hash(*args, **kwargs): return True, None
    def validate_otp(*args, **kwargs): return True, None
    def validate_username(*args, **kwargs): return True, None
    def validate_channel_link(*args, **kwargs): return True, None
    def validate_message_content(*args, **kwargs): return True, None
    def validate_account_name(*args, **kwargs): return True, None
    def validate_email(*args, **kwargs): return True, None
    def validate_date_range(*args, **kwargs): return True, None
    def validate_numeric_range(*args, **kwargs): return True, None
    def validate_file_extension(*args, **kwargs): return True, None
    def sanitize_input(text, *args, **kwargs): return text

# Import monitor with error handling
try:
    from .monitor import (
        BotMonitor,
        get_system_stats,
        get_bot_stats
    )
    MONITOR_AVAILABLE = True
    bot_monitor = BotMonitor()
except ImportError:
    MONITOR_AVAILABLE = False
    bot_monitor = None
    
    class DummyBotMonitor:
        async def get_system_stats(self): return {}
        async def get_bot_stats(self): return {}
    
    bot_monitor = DummyBotMonitor()
    
    async def get_system_stats(): return {}
    async def get_bot_stats(): return {}

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
    'extract_otp_from_text',
    'format_time_delta',
    'sanitize_text',
    
    # Session Manager
    'SessionManager',
    'session_manager',
    'save_session',
    'load_session',
    'delete_session',
    'validate_session',
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
    'bot_monitor',
    'get_system_stats',
    'get_bot_stats',
]

async def initialize_utils():
    """Initialize all utility modules"""
    # Setup logging
    setup_logging()
    
    # Initialize rate limiter if available
    if RATE_LIMITER_AVAILABLE:
        await reset_limits()
    
    # Clean up old sessions
    await cleanup_old_sessions()
    
    print("✅ Utilities initialized successfully")

async def shutdown_utils():
    """Shutdown all utility modules"""
    # Save any pending data
    await cleanup_old_sessions()
    
    print("✅ Utilities shutdown complete")
