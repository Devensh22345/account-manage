"""
Database package for Telegram Account Manager Bot
"""

from .mongodb import (
    get_database,
    get_accounts_collection,
    get_users_collection,
    get_admin_logs_collection,
    get_report_jobs_collection,
    get_config_collection,
    Database,
    init_database
)
from .models import (
    Account,
    User,
    AdminLog,
    ReportJob,
    BotConfig
)

__all__ = [
    'get_database',
    'get_accounts_collection',
    'get_users_collection',
    'get_admin_logs_collection',
    'get_report_jobs_collection',
    'get_config_collection',
    'Database',
    'init_database',
    'Account',
    'User',
    'AdminLog',
    'ReportJob',
    'BotConfig'
]

# Database connection instance
db_instance = None
