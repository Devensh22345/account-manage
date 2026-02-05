import motor.motor_asyncio
from config import Config
from typing import Optional

class Database:
    def __init__(self):
        self.config = Config()
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        
    async def connect(self):
        """Connect to MongoDB"""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(self.config.MONGO_URI)
        self.db = self.client[self.config.DB_NAME]
        
        # Create indexes
        await self.create_indexes()
        print(f"Connected to MongoDB: {self.config.DB_NAME}")
        
    async def create_indexes(self):
        """Create database indexes for better performance"""
        # Users collection indexes
        await self.db.users.create_index("user_id", unique=True)
        await self.db.users.create_index("is_admin")
        
        # Accounts collection indexes
        await self.db.accounts.create_index("user_id")
        await self.db.accounts.create_index("phone_number")
        await self.db.accounts.create_index([("user_id", 1), ("is_active", 1)])
        await self.db.accounts.create_index("is_active")
        await self.db.accounts.create_index("is_frozen")
        
        # Admin logs collection indexes
        await self.db.admin_logs.create_index("admin_id")
        await self.db.admin_logs.create_index("created_at")
        
        # Report jobs collection indexes
        await self.db.report_jobs.create_index("admin_id")
        await self.db.report_jobs.create_index("status")
        
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

# Global database instance
db_instance = Database()

async def get_database():
    """Get database instance"""
    if not db_instance.client:
        await db_instance.connect()
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
