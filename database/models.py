from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class Account(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: int
    phone_number: str
    api_id: int
    api_hash: str
    session_string: str
    account_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    is_active: bool = True
    is_frozen: bool = False
    is_deleted: bool = False
    two_step_enabled: bool = False
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class User(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    is_owner: bool = False
    log_channel: Optional[int] = None
    accounts: List[PyObjectId] = []
    max_accounts: int = 50
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class AdminLog(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    admin_id: int
    action: str
    target_user_id: Optional[int] = None
    target_account_id: Optional[PyObjectId] = None
    details: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ReportJob(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    admin_id: int
    target_type: str  # 'user', 'group', 'channel', 'bot', 'post'
    target_link: str
    reason: str
    description: str
    reports_per_account: int = 1
    status: str = 'pending'  # 'pending', 'running', 'completed', 'stopped'
    accounts_used: List[PyObjectId] = []
    total_reports: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class BotConfig(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    string_channel: Optional[int] = None
    report_log_channel: Optional[int] = None
    send_log_channel: Optional[int] = None
    otp_log_channel: Optional[int] = None
    join_log_channel: Optional[int] = None
    leave_log_channel: Optional[int] = None
    admins: List[int] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
