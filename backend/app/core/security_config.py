"""
Security configuration and utilities for production hardening.

This module provides centralized security configuration based on OWASP guidelines
and industry best practices for web application security.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import secrets
import hashlib
from enum import Enum

from app.core.config import settings


class SecurityLevel(str, Enum):
    """Security levels for different environments."""
    LOW = "low"  # Development
    MEDIUM = "medium"  # Staging
    HIGH = "high"  # Production
    CRITICAL = "critical"  # High-security production


@dataclass
class PasswordPolicy:
    """Password policy configuration."""
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Password history
    history_count: int = 5  # Remember last 5 passwords
    
    # Password age
    max_age_days: int = 90  # Force password change every 90 days
    min_age_hours: int = 1  # Prevent rapid password changes
    
    # Common password blacklist
    blacklist_patterns: List[str] = None
    
    def __post_init__(self):
        if self.blacklist_patterns is None:
            self.blacklist_patterns = [
                "password", "123456", "admin", "luckygas",
                "qwerty", "abc123", "111111", "000000"
            ]
    
    def validate_password(self, password: str, username: str = None) -> tuple[bool, List[str]]:
        """
        Validate password against policy.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Length check
        if len(password) < self.min_length:
            errors.append(f"密碼至少需要 {self.min_length} 個字元")
        if len(password) > self.max_length:
            errors.append(f"密碼不能超過 {self.max_length} 個字元")
        
        # Character requirements
        if self.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("密碼需要包含至少一個大寫字母")
        if self.require_lowercase and not re.search(r"[a-z]", password):
            errors.append("密碼需要包含至少一個小寫字母")
        if self.require_digit and not re.search(r"\d", password):
            errors.append("密碼需要包含至少一個數字")
        if self.require_special and not re.search(f"[{re.escape(self.special_chars)}]", password):
            errors.append("密碼需要包含至少一個特殊字元")
        
        # Check against blacklist
        password_lower = password.lower()
        for pattern in self.blacklist_patterns:
            if pattern in password_lower:
                errors.append("密碼包含常見的不安全模式")
                break
        
        # Check if password contains username
        if username and username.lower() in password_lower:
            errors.append("密碼不能包含使用者名稱")
        
        # Entropy check (simple version)
        unique_chars = len(set(password))
        if unique_chars < min(6, len(password) // 2):
            errors.append("密碼複雜度不足")
        
        return len(errors) == 0, errors


@dataclass
class SessionConfig:
    """Session management configuration."""
    # Token settings
    access_token_expire_minutes: int = 120  # 2 hours
    refresh_token_expire_days: int = 7
    
    # Session settings
    session_timeout_minutes: int = 1440  # 24 hours
    idle_timeout_minutes: int = 30  # Logout after 30 minutes of inactivity
    
    # Concurrent session limits
    max_sessions_per_user: int = 5
    
    # Session security
    secure_cookie: bool = True  # HTTPS only in production
    http_only: bool = True  # Prevent JS access
    same_site: str = "lax"  # CSRF protection
    
    # Remember me
    remember_me_days: int = 30
    
    def get_cookie_settings(self) -> Dict[str, any]:
        """Get cookie configuration."""
        return {
            "secure": self.secure_cookie and settings.is_production(),
            "httponly": self.http_only,
            "samesite": self.same_site,
            "max_age": self.session_timeout_minutes * 60
        }


@dataclass
class AccountLockoutPolicy:
    """Account lockout configuration."""
    enabled: bool = True
    max_attempts: int = 5
    lockout_duration_minutes: int = 30
    
    # Progressive lockout
    progressive_lockout: bool = True
    lockout_multiplier: float = 2.0  # Double lockout time after each lockout
    max_lockout_hours: int = 24
    
    # IP-based lockout
    ip_lockout_enabled: bool = True
    ip_max_attempts: int = 10
    ip_lockout_duration_hours: int = 1
    
    def get_lockout_duration(self, previous_lockouts: int) -> int:
        """Calculate lockout duration based on previous lockouts."""
        if not self.progressive_lockout:
            return self.lockout_duration_minutes
        
        duration = self.lockout_duration_minutes
        for _ in range(previous_lockouts):
            duration = int(duration * self.lockout_multiplier)
        
        max_duration = self.max_lockout_hours * 60
        return min(duration, max_duration)


@dataclass
class APIKeyConfig:
    """API key configuration for B2B partners."""
    key_length: int = 32
    prefix: str = "lgas_"  # Lucky Gas API key prefix
    
    # Key rotation
    rotation_days: int = 365  # Rotate annually
    rotation_warning_days: int = 30  # Warn 30 days before expiry
    
    # Rate limiting per API key
    default_rate_limit: int = 1000  # Requests per hour
    
    # Scopes
    available_scopes: List[str] = None
    
    def __post_init__(self):
        if self.available_scopes is None:
            self.available_scopes = [
                "orders:read", "orders:write",
                "customers:read", "customers:write",
                "routes:read", "routes:write",
                "predictions:read",
                "invoices:read", "invoices:write"
            ]
    
    def generate_api_key(self) -> str:
        """Generate a new API key."""
        key = secrets.token_urlsafe(self.key_length)
        return f"{self.prefix}{key}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()


@dataclass
class TwoFactorConfig:
    """Two-factor authentication configuration."""
    enabled: bool = True
    issuer_name: str = "Lucky Gas"
    
    # TOTP settings
    totp_digits: int = 6
    totp_interval: int = 30  # seconds
    totp_window: int = 1  # Allow 1 interval before/after
    
    # Backup codes
    backup_codes_count: int = 10
    backup_code_length: int = 8
    
    # SMS settings (for Taiwan)
    sms_enabled: bool = True
    sms_code_length: int = 6
    sms_code_expiry_minutes: int = 5
    
    # Trusted devices
    trusted_device_days: int = 30
    max_trusted_devices: int = 5


@dataclass
class EncryptionConfig:
    """Data encryption configuration."""
    # Field-level encryption for PII
    encrypt_pii: bool = True
    pii_fields: List[str] = None
    
    # Encryption algorithm
    algorithm: str = "AES-256-GCM"
    
    # Key rotation
    key_rotation_days: int = 90
    
    def __post_init__(self):
        if self.pii_fields is None:
            self.pii_fields = [
                "phone", "email", "address", "tax_id",
                "bank_account", "credit_card"
            ]
    
    def should_encrypt_field(self, field_name: str) -> bool:
        """Check if field should be encrypted."""
        return self.encrypt_pii and field_name in self.pii_fields


@dataclass
class SecurityEventConfig:
    """Security event logging configuration."""
    # Events to log
    log_failed_logins: bool = True
    log_permission_denied: bool = True
    log_suspicious_activity: bool = True
    log_data_access: bool = True  # For sensitive data
    log_configuration_changes: bool = True
    
    # Retention
    retention_days: int = 90  # Keep logs for 90 days
    
    # Alert thresholds
    alert_failed_logins: int = 10  # Alert after 10 failed logins
    alert_permission_denied: int = 20  # Alert after 20 permission denials
    alert_suspicious_requests: int = 5  # Alert after 5 suspicious requests


class SecurityConfig:
    """Main security configuration class."""
    
    def __init__(self):
        self.security_level = self._determine_security_level()
        
        # Initialize configurations based on security level
        self.password_policy = self._get_password_policy()
        self.session_config = self._get_session_config()
        self.lockout_policy = self._get_lockout_policy()
        self.api_key_config = APIKeyConfig()
        self.two_factor_config = self._get_2fa_config()
        self.encryption_config = EncryptionConfig()
        self.event_config = SecurityEventConfig()
        
        # Security headers configuration
        self.security_headers = self._get_security_headers()
        
        # CORS configuration
        self.cors_config = self._get_cors_config()
        
        # Rate limiting configuration
        self.rate_limits = self._get_rate_limits()
    
    def _determine_security_level(self) -> SecurityLevel:
        """Determine security level based on environment."""
        if settings.ENVIRONMENT.value == "production":
            return SecurityLevel.HIGH
        elif settings.ENVIRONMENT.value == "staging":
            return SecurityLevel.MEDIUM
        else:
            return SecurityLevel.LOW
    
    def _get_password_policy(self) -> PasswordPolicy:
        """Get password policy based on security level."""
        if self.security_level == SecurityLevel.HIGH:
            return PasswordPolicy(
                min_length=12,
                require_uppercase=True,
                require_lowercase=True,
                require_digit=True,
                require_special=True,
                history_count=10,
                max_age_days=60
            )
        elif self.security_level == SecurityLevel.MEDIUM:
            return PasswordPolicy(
                min_length=10,
                history_count=5,
                max_age_days=90
            )
        else:  # LOW (development)
            return PasswordPolicy(
                min_length=8,
                require_special=False,
                history_count=0,
                max_age_days=0  # No expiry
            )
    
    def _get_session_config(self) -> SessionConfig:
        """Get session configuration based on security level."""
        if self.security_level == SecurityLevel.HIGH:
            return SessionConfig(
                access_token_expire_minutes=60,  # 1 hour
                idle_timeout_minutes=15,
                max_sessions_per_user=3,
                secure_cookie=True
            )
        elif self.security_level == SecurityLevel.MEDIUM:
            return SessionConfig(
                access_token_expire_minutes=120,  # 2 hours
                idle_timeout_minutes=30,
                max_sessions_per_user=5
            )
        else:  # LOW
            return SessionConfig(
                access_token_expire_minutes=480,  # 8 hours
                idle_timeout_minutes=120,
                max_sessions_per_user=10,
                secure_cookie=False
            )
    
    def _get_lockout_policy(self) -> AccountLockoutPolicy:
        """Get lockout policy based on security level."""
        if self.security_level == SecurityLevel.HIGH:
            return AccountLockoutPolicy(
                max_attempts=3,
                lockout_duration_minutes=60,
                progressive_lockout=True,
                ip_lockout_enabled=True
            )
        elif self.security_level == SecurityLevel.MEDIUM:
            return AccountLockoutPolicy(
                max_attempts=5,
                lockout_duration_minutes=30
            )
        else:  # LOW
            return AccountLockoutPolicy(
                enabled=False,
                max_attempts=10,
                lockout_duration_minutes=5
            )
    
    def _get_2fa_config(self) -> TwoFactorConfig:
        """Get 2FA configuration based on security level."""
        if self.security_level == SecurityLevel.HIGH:
            return TwoFactorConfig(
                enabled=True,
                sms_enabled=True,
                trusted_device_days=7
            )
        elif self.security_level == SecurityLevel.MEDIUM:
            return TwoFactorConfig(
                enabled=True,
                sms_enabled=False,
                trusted_device_days=30
            )
        else:  # LOW
            return TwoFactorConfig(enabled=False)
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Get security headers based on security level."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        if self.security_level >= SecurityLevel.MEDIUM:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
        if self.security_level == SecurityLevel.HIGH:
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' wss: https://api.luckygas.tw https://*.googleapis.com;"
            )
        
        return headers
    
    def _get_cors_config(self) -> Dict[str, any]:
        """Get CORS configuration based on security level."""
        if self.security_level == SecurityLevel.HIGH:
            return {
                "allow_origins": [
                    "https://app.luckygas.tw",
                    "https://www.luckygas.tw"
                ],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE"],
                "max_age": 3600
            }
        else:
            # Development/staging - more permissive
            return {
                "allow_origins": settings.get_all_cors_origins(),
                "allow_credentials": True,
                "allow_methods": ["*"],
                "max_age": 3600
            }
    
    def _get_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Get rate limiting configuration."""
        if self.security_level == SecurityLevel.HIGH:
            return {
                "default": {"requests": 100, "window": 60},
                "auth": {"requests": 5, "window": 300},
                "api": {"requests": 1000, "window": 3600},
                "search": {"requests": 30, "window": 60}
            }
        elif self.security_level == SecurityLevel.MEDIUM:
            return {
                "default": {"requests": 200, "window": 60},
                "auth": {"requests": 10, "window": 300},
                "api": {"requests": 2000, "window": 3600},
                "search": {"requests": 60, "window": 60}
            }
        else:  # LOW
            return {
                "default": {"requests": 1000, "window": 60},
                "auth": {"requests": 100, "window": 300},
                "api": {"requests": 10000, "window": 3600},
                "search": {"requests": 300, "window": 60}
            }


# Global security configuration instance
security_config = SecurityConfig()


# Utility functions
def get_password_policy() -> PasswordPolicy:
    """Get current password policy."""
    return security_config.password_policy


def get_session_config() -> SessionConfig:
    """Get current session configuration."""
    return security_config.session_config


def get_lockout_policy() -> AccountLockoutPolicy:
    """Get current lockout policy."""
    return security_config.lockout_policy


def get_api_key_config() -> APIKeyConfig:
    """Get current API key configuration."""
    return security_config.api_key_config


def get_2fa_config() -> TwoFactorConfig:
    """Get current 2FA configuration."""
    return security_config.two_factor_config


def is_high_security() -> bool:
    """Check if running in high security mode."""
    return security_config.security_level >= SecurityLevel.HIGH


# Export configuration
__all__ = [
    "SecurityConfig",
    "SecurityLevel",
    "PasswordPolicy",
    "SessionConfig",
    "AccountLockoutPolicy",
    "APIKeyConfig",
    "TwoFactorConfig",
    "EncryptionConfig",
    "SecurityEventConfig",
    "security_config",
    "get_password_policy",
    "get_session_config",
    "get_lockout_policy",
    "get_api_key_config",
    "get_2fa_config",
    "is_high_security"
]