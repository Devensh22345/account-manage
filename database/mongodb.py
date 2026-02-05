import motor.motor_asyncio
from config import Config
from typing import Optional
import logging
from datetime import datetime  # ADD THIS IMPORT

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.config = Config()
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            logger.info(f"🔌 Connecting to MongoDB: {self.config.MONGO_URI}")
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.config.MONGO_URI)
            self.db = self.client[self.config.DB_NAME]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self.create_indexes()
            
            logger.info(f"✅ Connected to MongoDB: {self.config.DB_NAME}")
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
        
    async def create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Users collection indexes
            await self.db.users.create_index("user_id", unique=True)
            
            # Accounts collection indexes
            await self.db.accounts.create_index("user_id")
            await self.db.accounts.create_index("phone_number")
            await self.db.accounts.create_index([("user_id", 1), ("is_active", 1)])
            await self.db.accounts.create_index("is_active")
            await self.db.accounts.create_index("updated_at")
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")
            
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("✅ MongoDB connection closed")

# Global database instance
db_instance = Database()

async def get_database():
    """Get database instance"""
    if not db_instance.client:
        success = await db_instance.connect()
        if not success:
            raise ConnectionError("Failed to connect to MongoDB")
    return db_instance.db

async def get_accounts_collection():
    """Get accounts collection"""
    db = await get_database()
    return db.accounts

async def get_users_collection():
    """Get users collection"""
    db = await get_database()
    return db.users

async def get_admin_logs_collection():
    """Get admin logs collection"""
    db = await get_database()
    return db.admin_logs

async def get_report_jobs_collection():
    """Get report jobs collection"""
    db = await get_database()
    return db.report_jobs

async def get_config_collection():
    """Get bot config collection"""
    db = await get_database()
    return db.bot_config

async def init_database():
    """Initialize database with default data"""
    try:
        db = await get_database()
        config_collection = await get_config_collection()
        
        # Check if config exists
        config = await config_collection.find_one({})
        if not config:
            # Create default config
            default_config = {
                "admins": [],
                "string_channel": None,
                "report_log_channel": None,
                "send_log_channel": None,
                "otp_log_channel": None,
                "join_log_channel": None,
                "leave_log_channel": None,
                "updated_at": datetime.utcnow()
            }
            await config_collection.insert_one(default_config)
            logger.info("✅ Default configuration created")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False
