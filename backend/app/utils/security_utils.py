"""
Security utility functions for common security operations.
"""

import hashlib
import re
import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status

from app.core.cache import cache
from app.core.logging import get_logger
from app.core.security import DataEncryption
from app.core.security_config import security_config

logger = get_logger(__name__)


class SecurityAudit:
    """Security audit and logging utilities."""

    @staticmethod
    async def log_security_event(
        event_type: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO",
    ):
        """Log a security event for audit trail."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {},
        }

        # Store in daily log
        key = f"security:audit:{datetime.utcnow().strftime('%Y % m % d')}"

        try:
            current_log = await cache.get(key)
            if current_log:
                log_list = eval(current_log)
            else:
                log_list = []

            log_list.append(event)

            # Keep for configured retention period
            retention_days = security_config.event_config.retention_days
            await cache.set(key, str(log_list), expire=86400 * retention_days)

            # Log to standard logger as well
            logger.info(
                f"Security event: {event_type}", extra={"security_event": True, **event}
            )

            # Check if alert is needed
            await SecurityAudit._check_alert_threshold(event_type)

        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}", exc_info=True)

    @staticmethod
    async def _check_alert_threshold(event_type: str):
        """Check if security alerts should be triggered."""
        config = security_config.event_config

        # Count recent events
        count_key = f"security:event_count:{event_type}"
        count = await cache.get(count_key)
        count = int(count) + 1 if count else 1

        await cache.set(count_key, str(count), expire=3600)  # Count per hour

        # Check thresholds
        alert_needed = False
        if event_type == "failed_login" and count >= config.alert_failed_logins:
            alert_needed = True
        elif (
            event_type == "permission_denied"
            and count >= config.alert_permission_denied
        ):
            alert_needed = True
        elif (
            event_type == "suspicious_activity"
            and count >= config.alert_suspicious_requests
        ):
            alert_needed = True

        if alert_needed:
            # TODO: Send alert (email, SMS, webhook)
            logger.warning(
                f"Security alert threshold exceeded: {event_type}",
                extra={"event_count": count},
            )


class InputSanitizer:
    """Advanced input sanitization utilities."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal."""
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove special characters
        filename = re.sub(r"[^a - zA - Z0 - 9._-]", "_", filename)

        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = (
                name[: max_length - len(ext) - 1] + "." + ext
                if ext
                else name[:max_length]
            )

        return filename

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Basic HTML sanitization."""
        if not text:
            return text

        # HTML entity encoding
        replacements = {
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
            "&": "&amp;",
            "/": "&#x2F;",
            "`": "&#x60;",
            "=": "&#x3D;",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    @staticmethod
    def sanitize_sql_identifier(identifier: str) -> str:
        """Sanitize SQL identifiers (table names, column names)."""
        # Only allow alphanumeric and underscore
        return re.sub(r"[^a - zA - Z0 - 9_]", "", identifier)

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a - zA - Z0 - 9._%+-]+@[a - zA - Z0 - 9.-]+\.[a - zA - Z]{2, }$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_taiwan_phone(phone: str) -> bool:
        """Validate Taiwan phone number format."""
        from app.core.config import settings

        return settings.validate_taiwan_phone(phone)


class SecureTokenGenerator:
    """Secure token generation utilities."""

    @staticmethod
    def generate_token(length: int = 32, alphabet: str = None) -> str:
        """Generate a secure random token."""
        if alphabet is None:
            alphabet = string.ascii_letters + string.digits

        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_numeric_code(length: int = 6) -> str:
        """Generate a numeric code (for SMS, etc.)."""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def generate_password(
        length: int = 16, include_symbols: bool = True, exclude_ambiguous: bool = True
    ) -> str:
        """Generate a secure password."""
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:, .<>?"

        # Exclude ambiguous characters
        if exclude_ambiguous:
            lowercase = lowercase.replace("l", "").replace("o", "")
            uppercase = uppercase.replace("I", "").replace("O", "")
            digits = digits.replace("0", "").replace("1", "")
            symbols = symbols.replace("|", "").replace("l", "")

        # Build character set
        charset = lowercase + uppercase + digits
        if include_symbols:
            charset += symbols

        # Ensure password has at least one of each required type
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
        ]

        if include_symbols:
            password.append(secrets.choice(symbols))

        # Fill the rest
        for _ in range(len(password), length):
            password.append(secrets.choice(charset))

        # Shuffle
        secrets.SystemRandom().shuffle(password)

        return "".join(password)


class PIIMasking:
    """PII data masking utilities."""

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address for display."""
        if not email or "@" not in email:
            return email

        local, domain = email.split("@", 1)

        if len(local) <= 3:
            masked_local = local[0] + "*" * (len(local) - 1)
        else:
            masked_local = local[:2] + "*" * (len(local) - 4) + local[-2:]

        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number for display."""
        if not phone:
            return phone

        # Remove non - digits
        digits = re.sub(r"\D", "", phone)

        if len(digits) < 4:
            return "*" * len(digits)

        # Show first 3 and last 2 digits
        return digits[:3] + "*" * (len(digits) - 5) + digits[-2:]

    @staticmethod
    def mask_address(address: str) -> str:
        """Mask address for display."""
        if not address:
            return address

        # Keep first part and mask the rest
        parts = address.split(" ")
        if len(parts) <= 2:
            return address[:5] + "*" * (len(address) - 5)

        # Keep first two parts, mask the rest
        visible = " ".join(parts[:2])
        return visible + " " + "*" * 10

    @staticmethod
    def mask_tax_id(tax_id: str) -> str:
        """Mask Taiwan tax ID (統一編號)."""
        if not tax_id:
            return tax_id

        # Remove non - digits
        digits = re.sub(r"\D", "", tax_id)

        if len(digits) < 4:
            return "*" * len(digits)

        # Show first 2 and last 2 digits
        return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]


class SecureDataHandler:
    """Secure data handling utilities."""

    @staticmethod
    def encrypt_pii_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PII fields in a dictionary."""
        config = security_config.encryption_config

        if not config.encrypt_pii:
            return data

        encrypted_data = data.copy()

        for field in config.pii_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = DataEncryption.encrypt(
                    str(encrypted_data[field])
                )

        return encrypted_data

    @staticmethod
    def decrypt_pii_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt PII fields in a dictionary."""
        config = security_config.encryption_config

        if not config.encrypt_pii:
            return data

        decrypted_data = data.copy()

        for field in config.pii_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = DataEncryption.decrypt(
                        decrypted_data[field]
                    )
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {str(e)}")
                    decrypted_data[field] = None

        return decrypted_data

    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data with optional salt."""
        if salt:
            data = f"{salt}{data}"

        return hashlib.sha256(data.encode()).hexdigest()


class RequestValidator:
    """Request validation utilities."""

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Get real client IP from request."""
        # Check forwarded headers
        forwarded_for = request.headers.get("X - Forwarded - For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(", ")[0].strip()

        real_ip = request.headers.get("X - Real - IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    @staticmethod
    def validate_content_type(request: Request, allowed_types: List[str]):
        """Validate request content type."""
        content_type = request.headers.get("content - type", "").lower()

        # Remove charset and other parameters
        content_type = content_type.split(";")[0].strip()

        if content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"不支援的內容類型: {content_type}",
            )

    @staticmethod
    async def validate_request_size(request: Request, max_size: int = 10 * 1024 * 1024):
        """Validate request body size."""
        content_length = request.headers.get("content - length")

        if content_length and int(content_length) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"請求內容過大，最大允許 {max_size // 1024 // 1024} MB",
            )


class SecureHeaders:
    """Secure header utilities."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers from configuration."""
        return security_config.security_headers

    @staticmethod
    def add_cache_headers(response, cache_time: int = 0, private: bool = True):
        """Add cache control headers."""
        if cache_time > 0:
            cache_control = (
                f"private, max - age={cache_time}"
                if private
                else f"public, max - age={cache_time}"
            )
        else:
            cache_control = "no - store, no - cache, must - revalidate, private"

        response.headers["Cache - Control"] = cache_control
        response.headers["Pragma"] = "no - cache" if cache_time == 0 else "cache"

        if cache_time == 0:
            response.headers["Expires"] = "0"


# Export utilities
__all__ = [
    "SecurityAudit",
    "InputSanitizer",
    "SecureTokenGenerator",
    "PIIMasking",
    "SecureDataHandler",
    "RequestValidator",
    "SecureHeaders",
]
