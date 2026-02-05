import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.user_limits: Dict[int, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.account_limits: Dict[str, List[float]] = defaultdict(list)
        self.ip_limits: Dict[str, List[float]] = defaultdict(list)
        
    async def check_user_limit(
        self, 
        user_id: int, 
        action: str, 
        limit: int, 
        period: int = 60
    ) -> bool:
        """Check if user has exceeded rate limit for an action"""
        now = time.time()
        
        # Clean old timestamps
        timestamps = self.user_limits[user_id][action]
        timestamps = [ts for ts in timestamps if now - ts < period]
        self.user_limits[user_id][action] = timestamps
        
        # Check limit
        if len(timestamps) >= limit:
            return False
        
        # Add new timestamp
        timestamps.append(now)
        return True
    
    async def get_wait_time(
        self, 
        user_id: int, 
        action: str, 
        limit: int, 
        period: int = 60
    ) -> float:
        """Get remaining wait time for user"""
        now = time.time()
        timestamps = self.user_limits[user_id][action]
        
        if len(timestamps) < limit:
            return 0
        
        # Get oldest timestamp
        oldest = min(timestamps)
        wait_time = (oldest + period) - now
        
        return max(0, wait_time)
    
    async def reset_limits(self, user_id: Optional[int] = None):
        """Reset rate limits for user or all users"""
        if user_id:
            if user_id in self.user_limits:
                del self.user_limits[user_id]
        else:
            self.user_limits.clear()
            self.account_limits.clear()
            self.ip_limits.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "total_users": len(self.user_limits),
            "total_accounts": len(self.account_limits),
            "total_ips": len(self.ip_limits),
            "timestamp": datetime.utcnow().isoformat()
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

# Rate limit configurations
RATE_LIMITS = {
    "login": {"limit": 3, "period": 300},  # 3 attempts per 5 minutes
    "send_message": {"limit": 10, "period": 60},  # 10 messages per minute
    "join_chat": {"limit": 5, "period": 60},  # 5 joins per minute
    "report": {"limit": 3, "period": 300},  # 3 reports per 5 minutes
    "api_call": {"limit": 30, "period": 60},  # 30 API calls per minute
}

async def check_rate_limit(
    user_id: int, 
    action: str, 
    account_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> tuple[bool, Optional[float]]:
    """
    Check rate limit for user, account, and IP
    
    Returns:
        Tuple of (allowed, wait_time)
    """
    # Get limits for action
    limits = RATE_LIMITS.get(action, {"limit": 5, "period": 60})
    
    # Check user limit
    user_allowed = await rate_limiter.check_user_limit(
        user_id, action, limits["limit"], limits["period"]
    )
    
    if not user_allowed:
        wait_time = await rate_limiter.get_wait_time(
            user_id, action, limits["limit"], limits["period"]
        )
        return False, wait_time
    
    return True, None

async def get_wait_time(
    user_id: int, 
    action: str, 
    account_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> float:
    """Get wait time for rate limit"""
    limits = RATE_LIMITS.get(action, {"limit": 5, "period": 60})
    return await rate_limiter.get_wait_time(user_id, action, limits["limit"], limits["period"])

async def reset_limits(user_id: Optional[int] = None):
    """Reset rate limits"""
    await rate_limiter.reset_limits(user_id)

async def get_stats() -> Dict[str, Any]:
    """Get rate limiter statistics"""
    return await rate_limiter.get_stats()
