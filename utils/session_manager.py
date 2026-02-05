import aiofiles
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = sessions_dir
        self.session_cache: Dict[str, Dict] = {}
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    async def save_session(self, session_string: str, account_data: Dict[str, Any]) -> str:
        """Save session string to file"""
        filename = f"{account_data.get('user_id', 'unknown')}_{account_data.get('phone_number', 'unknown')}"
        filepath = os.path.join(self.sessions_dir, f"{filename}.session")
        
        # Save session data
        session_data = {
            "session_string": session_string,
            "account_data": account_data,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": datetime.utcnow().isoformat()
        }
        
        try:
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(session_data, indent=2))
            
            # Cache the session
            self.session_cache[filename] = session_data
            
            logger.info(f"✅ Session saved: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Error saving session: {e}")
            return ""
    
    async def load_session(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load session data from file"""
        # Check cache first
        if filename in self.session_cache:
            return self.session_cache[filename]
        
        filepath = os.path.join(self.sessions_dir, f"{filename}.session")
        
        if not os.path.exists(filepath):
            return None
        
        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            # Update cache
            self.session_cache[filename] = session_data
            
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Error loading session {filename}: {e}")
            return None
    
    async def delete_session(self, filename: str) -> bool:
        """Delete session file"""
        filepath = os.path.join(self.sessions_dir, f"{filename}.session")
        
        # Remove from cache
        if filename in self.session_cache:
            del self.session_cache[filename]
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"✅ Session deleted: {filename}")
                return True
            except Exception as e:
                logger.error(f"❌ Error deleting session {filename}: {e}")
        
        return False
    
    async def validate_session(self, session_data: Dict[str, Any]) -> bool:
        """Validate if session is still active"""
        try:
            from pyrogram import Client
            
            app = Client(
                "validation_session",
                api_id=session_data["account_data"]["api_id"],
                api_hash=session_data["account_data"]["api_hash"],
                session_string=session_data["session_string"]
            )
            
            await app.connect()
            await app.get_me()
            await app.disconnect()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Session validation error: {e}")
            return False
    
    async def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up session files older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".session"):
                filepath = os.path.join(self.sessions_dir, filename)
                
                try:
                    # Get file modification time
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if mtime < cutoff_date:
                        os.remove(filepath)
                        logger.info(f"🗑️ Removed old session: {filename}")
                        
                        # Remove from cache
                        name_without_ext = filename.replace(".session", "")
                        if name_without_ext in self.session_cache:
                            del self.session_cache[name_without_ext]
                            
                except Exception as e:
                    logger.error(f"❌ Error cleaning up session {filename}: {e}")
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        total_sessions = 0
        valid_sessions = 0
        total_size = 0
        
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".session"):
                total_sessions += 1
                filepath = os.path.join(self.sessions_dir, filename)
                total_size += os.path.getsize(filepath)
        
        return {
            "total_sessions": total_sessions,
            "valid_sessions": valid_sessions,
            "invalid_sessions": total_sessions - valid_sessions,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_size": len(self.session_cache)
        }

# Create global instance
session_manager = SessionManager()

# Export functions for backward compatibility
async def save_session(session_string: str, account_data: Dict[str, Any]) -> str:
    return await session_manager.save_session(session_string, account_data)

async def load_session(filename: str) -> Optional[Dict[str, Any]]:
    return await session_manager.load_session(filename)

async def delete_session(filename: str) -> bool:
    return await session_manager.delete_session(filename)

async def validate_session(session_data: Dict[str, Any]) -> bool:
    return await session_manager.validate_session(session_data)

async def cleanup_old_sessions(days_old: int = 30):
    return await session_manager.cleanup_old_sessions(days_old)

async def get_session_stats() -> Dict[str, Any]:
    return await session_manager.get_session_stats()
