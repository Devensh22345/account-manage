import asyncio
import psutil
import os
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BotMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "percent": disk.percent
                },
                "uptime": str(datetime.now() - self.start_time)
            }
        except Exception as e:
            logger.error(f"❌ Error getting system stats: {e}")
            return {"error": str(e)}
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        try:
            from database.mongodb import get_accounts_collection
            
            accounts_collection = await get_accounts_collection()
            
            total = await accounts_collection.count_documents({})
            active = await accounts_collection.count_documents({"is_active": True})
            
            return {
                "total_accounts": total,
                "active_accounts": active,
                "inactive_accounts": total - active,
                "uptime": str(datetime.now() - self.start_time)
            }
        except Exception as e:
            logger.error(f"❌ Error getting bot stats: {e}")
            return {"error": str(e)}

async def get_system_stats() -> Dict[str, Any]:
    """Get system statistics"""
    monitor = BotMonitor()
    return await monitor.get_system_stats()

async def get_bot_stats() -> Dict[str, Any]:
    """Get bot statistics"""
    monitor = BotMonitor()
    return await monitor.get_bot_stats()
