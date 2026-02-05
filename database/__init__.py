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
    Database
)
from .models import (
    Account,
    User,
    AdminLog,
    ReportJob,
    BotConfig,
    PyObjectId
)

__all__ = [
    'get_database',
    'get_accounts_collection',
    'get_users_collection',
    'get_admin_logs_collection',
    'get_report_jobs_collection',
    'get_config_collection',
    'Database',
    'Account',
    'User',
    'AdminLog',
    'ReportJob',
    'BotConfig',
    'PyObjectId'
]

# Database connection instance
db_instance = None

async def init_database():
    """Initialize database connection"""
    global db_instance
    from .mongodb import db_instance as db
    db_instance = db
    await db_instance.connect()
    return db_instance

async def close_database():
    """Close database connection"""
    global db_instance
    if db_instance:
        await db_instance.close()
