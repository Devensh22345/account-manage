import re
from typing import Optional, Tuple
from datetime import datetime

def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format
    
    Args:
        phone: Phone number string
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check length
    if len(digits) < 10 or len(digits) > 15:
        return False, "Phone number must be 10-15 digits"
    
    # Check for valid country code (optional)
    if not phone.startswith('+'):
        # Assume it's missing country code, we'll add +
        phone = '+' + phone
    
    return True, None

def validate_api_id(api_id: str) -> Tuple[bool, Optional[str]]:
    """Validate API ID"""
    if not api_id.isdigit():
        return False, "API ID must be numeric"
    
    if len(api_id) < 5 or len(api_id) > 10:
        return False, "API ID must be 5-10 digits"
    
    return True, None

def validate_api_hash(api_hash: str) -> Tuple[bool, Optional[str]]:
    """Validate API Hash"""
    if len(api_hash) != 32:
        return False, "API Hash must be 32 characters"
    
    if not re.match(r'^[a-f0-9]{32}$', api_hash, re.IGNORECASE):
        return False, "API Hash must be hexadecimal"
    
    return True, None

def validate_otp(otp: str) -> Tuple[bool, Optional[str]]:
    """Validate OTP code"""
    if not otp.isdigit():
        return False, "OTP must be numeric"
    
    if len(otp) < 4 or len(otp) > 8:
        return False, "OTP must be 4-8 digits"
    
    return True, None

def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """Validate Telegram username"""
    if not username:
        return True, None  # Username can be empty
    
    if len(username) < 5:
        return False, "Username must be at least 5 characters"
    
    if len(username) > 32:
        return False, "Username must be at most 32 characters"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, None

def validate_channel_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate Telegram channel/group link"""
    patterns = [
        r'^@[a-zA-Z0-9_]{5,32}$',
        r'^https://t\.me/[a-zA-Z0-9_]{5,32}$',
        r'^https://t\.me/\+[a-zA-Z0-9_]{5,32}$',
        r'^https://t\.me/joinchat/[a-zA-Z0-9_-]{5,}$',
        r'^https://t\.me/addlist/[a-zA-Z0-9_-]{5,}$',
    ]
    
    for pattern in patterns:
        if re.match(pattern, link, re.IGNORECASE):
            return True, None
    
    return False, "Invalid Telegram link format"

def validate_message_content(content: str, max_length: int = 4096) -> Tuple[bool, Optional[str]]:
    """Validate message content"""
    if not content or not content.strip():
        return False, "Message content cannot be empty"
    
    if len(content) > max_length:
        return False, f"Message too long (max {max_length} characters)"
    
    return True, None

def validate_account_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate account name"""
    if not name or not name.strip():
        return False, "Account name cannot be empty"
    
    if len(name) < 2:
        return False, "Account name must be at least 2 characters"
    
    if len(name) > 50:
        return False, "Account name must be at most 50 characters"
    
    # Check for invalid characters
    if re.search(r'[<>:"/\\|?*]', name):
        return False, "Account name contains invalid characters"
    
    return True, None

def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return True, None
    
    return False, "Invalid email format"

def validate_date_range(start_date: str, end_date: str) -> Tuple[bool, Optional[str]]:
    """Validate date range"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start > end:
            return False, "Start date cannot be after end date"
        
        if (end - start).days > 365:
            return False, "Date range cannot exceed 1 year"
        
        return True, None
        
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"

def validate_numeric_range(value: str, min_val: int = 1, max_val: int = 100) -> Tuple[bool, Optional[str]]:
    """Validate numeric range"""
    if not value.isdigit():
        return False, "Value must be a number"
    
    num = int(value)
    
    if num < min_val:
        return False, f"Value must be at least {min_val}"
    
    if num > max_val:
        return False, f"Value must be at most {max_val}"
    
    return True, None

def validate_file_extension(filename: str, allowed_extensions: list) -> Tuple[bool, Optional[str]]:
    """Validate file extension"""
    if not filename:
        return False, "Filename cannot be empty"
    
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None

def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Escape HTML special characters (for safe display)
    text = (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
    )
    
    return text
