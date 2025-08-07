"""
Permission system for Lucky Gas backend.
"""
from enum import Enum


class Permission(str, Enum):
    """System permissions."""
    
    # General permissions
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    
    # Customer permissions
    CUSTOMER_READ = "customer:read"
    CUSTOMER_WRITE = "customer:write"
    CUSTOMER_DELETE = "customer:delete"
    CUSTOMER_EXPORT = "customer:export"
    CUSTOMER_IMPORT = "customer:import"
    
    # Order permissions
    ORDER_READ = "order:read"
    ORDER_WRITE = "order:write"
    ORDER_DELETE = "order:delete"
    ORDER_EXPORT = "order:export"
    ORDER_IMPORT = "order:import"
    
    # Route permissions
    ROUTE_READ = "route:read"
    ROUTE_WRITE = "route:write"
    ROUTE_DELETE = "route:delete"
    ROUTE_OPTIMIZE = "route:optimize"
    
    # Financial permissions
    INVOICE_READ = "invoice:read"
    INVOICE_WRITE = "invoice:write"
    INVOICE_DELETE = "invoice:delete"
    PAYMENT_READ = "payment:read"
    PAYMENT_WRITE = "payment:write"
    FINANCIAL_REPORT = "financial:report"
    
    # Admin permissions
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"
    API_KEY_MANAGE = "api_key:manage"
    
    # Data management
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    
    # Communication
    SMS_SEND = "sms:send"
    NOTIFICATION_SEND = "notification:send"


# Role-based permission mapping
ROLE_PERMISSIONS = {
    "super_admin": ["*"],  # All permissions
    "manager": [
        Permission.CUSTOMER_READ,
        Permission.CUSTOMER_WRITE,
        Permission.CUSTOMER_EXPORT,
        Permission.ORDER_READ,
        Permission.ORDER_WRITE,
        Permission.ORDER_EXPORT,
        Permission.ROUTE_READ,
        Permission.ROUTE_WRITE,
        Permission.ROUTE_OPTIMIZE,
        Permission.INVOICE_READ,
        Permission.INVOICE_WRITE,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_WRITE,
        Permission.FINANCIAL_REPORT,
        Permission.DATA_EXPORT,
        Permission.SMS_SEND,
        Permission.NOTIFICATION_SEND,
    ],
    "office_staff": [
        Permission.CUSTOMER_READ,
        Permission.CUSTOMER_WRITE,
        Permission.ORDER_READ,
        Permission.ORDER_WRITE,
        Permission.ROUTE_READ,
        Permission.INVOICE_READ,
        Permission.PAYMENT_READ,
        Permission.DATA_EXPORT,
        Permission.SMS_SEND,
    ],
    "driver": [
        Permission.CUSTOMER_READ,
        Permission.ORDER_READ,
        Permission.ROUTE_READ,
    ],
    "customer": [
        Permission.ORDER_READ,  # Only their own orders
    ],
}


def has_permission(user_role: str, required_permission: str) -> bool:
    """
    Check if a role has a specific permission.
    
    Args:
        user_role: User's role
        required_permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    if user_role not in ROLE_PERMISSIONS:
        return False
    
    role_perms = ROLE_PERMISSIONS[user_role]
    
    # Super admin has all permissions
    if "*" in role_perms:
        return True
    
    return required_permission in role_perms