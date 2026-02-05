import aiofiles
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import Config
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, SessionRevoked

config = Config()

class SessionManager:
    def __init__(self):
        self.sessions_dir = config.SESSION_DIR
        self.session_cache: Dict[str, Dict] = {}
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    async def save_session(self, session_string: str, account_data: Dict[str, Any]) -> str:
        """Save session string to file"""
        filename = f"{account_data['user_id']}_{account_data['phone_number']}"
        filepath = os.path.join(self.sessions_dir, f"{filename}.session")
        
        # Save session data
        session_data = {
            "session_string": session_string,
            "account_data": account_data,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(session_data, indent=2))
        
        # Cache the session
        self.session_cache[filename] = session_data
        
        return filepath
    
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
            logger.error(f"Error loading session {filename}: {e}")
            return None
    
    async def delete_session(self, filename: str) -> bool:
        """Delete session file"""
        filepath = os.path.join(self.sessions_dir, f"{filename}.session")
        
        # Remove from cache
        if filename in self.session_cache:
            del self.session_cache[filename]
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        
        return False
    
    async def validate_session(self, session_data: Dict[str, Any]) -> bool:
        """Validate if session is still active"""
        try:
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
            
        except (AuthKeyUnregistered, SessionRevoked):
            return False
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False
    
    async def refresh_session(self, account_data: Dict[str, Any]) -> Optional[str]:
        """Refresh session by logging in again"""
        try:
            app = Client(
                f"refresh_{account_data['phone_number']}",
                api_id=account_data["api_id"],
                api_hash=account_data["api_hash"],
                phone_number=account_data["phone_number"]
            )
            
            await app.connect()
            
            # Check if we need to send code
            sent_code = await app.send_code(account_data["phone_number"])
            
            # Note: This requires OTP input
            # In a real implementation, you'd store the OTP request
            # and handle it via the bot
            
            await app.disconnect()
            return None
            
        except Exception as e:
            logger.error(f"Session refresh error: {e}")
            return None
    
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
                        logger.info(f"Removed old session: {filename}")
                        
                        # Remove from cache
                        name_without_ext = filename.replace(".session", "")
                        if name_without_ext in self.session_cache:
                            del self.session_cache[name_without_ext]
                            
                except Exception as e:
                    logger.error(f"Error cleaning up session {filename}: {e}")
    
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
                
                # Try to validate session
                try:
                    session_data = await self.load_session(filename.replace(".session", ""))
                    if session_data and await self.validate_session(session_data):
                        valid_sessions += 1
                except:
                    pass
        
        return {
            "total_sessions": total_sessions,
            "valid_sessions": valid_sessions,
            "invalid_sessions": total_sessions - valid_sessions,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_size": len(self.session_cache)
        }
