from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

# Simple models without pydantic for now
# We'll use plain dictionaries for MongoDB

class Account:
    @staticmethod
    def create_dict(
        user_id: int,
        phone_number: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        account_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create account dictionary for MongoDB"""
        return {
            "user_id": user_id,
            "phone_number": phone_number,
            "api_id": api_id,
            "api_hash": api_hash,
            "session_string": session_string,
            "account_name": account_name,
            "first_name": kwargs.get("first_name"),
            "last_name": kwargs.get("last_name"),
            "username": kwargs.get("username"),
            "bio": kwargs.get("bio"),
            "profile_photo": kwargs.get("profile_photo"),
            "is_active": kwargs.get("is_active", True),
            "is_frozen": kwargs.get("is_frozen", False),
            "is_deleted": kwargs.get("is_deleted", False),
            "two_step_enabled": kwargs.get("two_step_enabled", False),
            "last_seen": kwargs.get("last_seen"),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow())
        }

class User:
    @staticmethod
    def create_dict(
        user_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Create user dictionary for MongoDB"""
        return {
            "user_id": user_id,
            "username": kwargs.get("username"),
            "first_name": kwargs.get("first_name"),
            "last_name": kwargs.get("last_name"),
            "is_admin": kwargs.get("is_admin", False),
            "is_owner": kwargs.get("is_owner", False),
            "log_channel": kwargs.get("log_channel"),
            "accounts": kwargs.get("accounts", []),
            "max_accounts": kwargs.get("max_accounts", 50),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow())
        }

class AdminLog:
    @staticmethod
    def create_dict(
        admin_id: int,
        action: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create admin log dictionary for MongoDB"""
        return {
            "admin_id": admin_id,
            "action": action,
            "target_user_id": kwargs.get("target_user_id"),
            "target_account_id": kwargs.get("target_account_id"),
            "details": kwargs.get("details", {}),
            "created_at": kwargs.get("created_at", datetime.utcnow())
        }

class ReportJob:
    @staticmethod
    def create_dict(
        admin_id: int,
        target_type: str,
        target_link: str,
        reason: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create report job dictionary for MongoDB"""
        return {
            "admin_id": admin_id,
            "target_type": target_type,
            "target_link": target_link,
            "reason": reason,
            "description": kwargs.get("description", ""),
            "reports_per_account": kwargs.get("reports_per_account", 1),
            "status": kwargs.get("status", "pending"),
            "accounts_used": kwargs.get("accounts_used", []),
            "total_reports": kwargs.get("total_reports", 0),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow())
        }

class BotConfig:
    @staticmethod
    def create_dict(**kwargs) -> Dict[str, Any]:
        """Create bot config dictionary for MongoDB"""
        return {
            "string_channel": kwargs.get("string_channel"),
            "report_log_channel": kwargs.get("report_log_channel"),
            "send_log_channel": kwargs.get("send_log_channel"),
            "otp_log_channel": kwargs.get("otp_log_channel"),
            "join_log_channel": kwargs.get("join_log_channel"),
            "leave_log_channel": kwargs.get("leave_log_channel"),
            "admins": kwargs.get("admins", []),
            "updated_at": kwargs.get("updated_at", datetime.utcnow())
        }
