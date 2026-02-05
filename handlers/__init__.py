"""
Handlers package for Telegram Account Manager Bot
"""

from .admin import (
    handle_admin,
    handle_admin_callback,
    handle_admin_message,
    admin_states
)
from .user import (
    handle_settings,
    handle_user_callback,
    handle_user_message,
    user_states
)
from .login import (
    handle_login,
    handle_login_callback,
    handle_login_message,
    login_states
)
from .send import (
    handle_send,
    handle_send_callback,
    handle_send_message,
    send_states,
    active_send_tasks
)
from .join_leave import (
    handle_join,
    handle_leave,
    handle_join_callback,
    handle_leave_callback,
    handle_join_message,
    handle_leave_message,
    join_states,
    leave_states,
    active_join_tasks,
    active_leave_tasks
)
from .report import (
    handle_report,
    handle_stop,
    handle_report_callback,
    handle_report_message,
    report_states,
    active_report_tasks
)
from .otp import (
    handle_otp,
    handle_otp_callback,
    otp_states,
    active_otp_tasks
)

__all__ = [
    # Admin handlers
    'handle_admin',
    'handle_admin_callback',
    'handle_admin_message',
    'admin_states',
    
    # User handlers
    'handle_settings',
    'handle_user_callback',
    'handle_user_message',
    'user_states',
    
    # Login handlers
    'handle_login',
    'handle_login_callback',
    'handle_login_message',
    'login_states',
    
    # Send handlers
    'handle_send',
    'handle_send_callback',
    'handle_send_message',
    'send_states',
    'active_send_tasks',
    
    # Join/Leave handlers
    'handle_join',
    'handle_leave',
    'handle_join_callback',
    'handle_leave_callback',
    'handle_join_message',
    'handle_leave_message',
    'join_states',
    'leave_states',
    'active_join_tasks',
    'active_leave_tasks',
    
    # Report handlers
    'handle_report',
    'handle_stop',
    'handle_report_callback',
    'handle_report_message',
    'report_states',
    'active_report_tasks',
    
    # OTP handlers
    'handle_otp',
    'handle_otp_callback',
    'otp_states',
    'active_otp_tasks',
]

# Export all handler functions for easy access
HANDLERS = {
    'admin': {
        'command': handle_admin,
        'callback': handle_admin_callback,
        'message': handle_admin_message
    },
    'user': {
        'command': handle_settings,
        'callback': handle_user_callback,
        'message': handle_user_message
    },
    'login': {
        'command': handle_login,
        'callback': handle_login_callback,
        'message': handle_login_message
    },
    'send': {
        'command': handle_send,
        'callback': handle_send_callback,
        'message': handle_send_message
    },
    'join': {
        'command': handle_join,
        'callback': handle_join_callback,
        'message': handle_join_message
    },
    'leave': {
        'command': handle_leave,
        'callback': handle_leave_callback,
        'message': handle_leave_message
    },
    'report': {
        'command': handle_report,
        'callback': handle_report_callback,
        'message': handle_report_message
    },
    'stop': {
        'command': handle_stop
    },
    'otp': {
        'command': handle_otp,
        'callback': handle_otp_callback
    }
}

# Export all states for easy management
STATES = {
    'admin': admin_states,
    'user': user_states,
    'login': login_states,
    'send': send_states,
    'join': join_states,
    'leave': leave_states,
    'report': report_states,
    'otp': otp_states
}

# Export active tasks
ACTIVE_TASKS = {
    'send': active_send_tasks,
    'join': active_join_tasks,
    'leave': active_leave_tasks,
    'report': active_report_tasks,
    'otp': active_otp_tasks
}

def clear_user_states(user_id: int):
    """Clear all states for a user"""
    for state_name, state_dict in STATES.items():
        if user_id in state_dict:
            del state_dict[user_id]
    
    # Cancel active tasks
    for task_name, task_dict in ACTIVE_TASKS.items():
        if user_id in task_dict:
            task_dict[user_id].cancel()
            del task_dict[user_id]
