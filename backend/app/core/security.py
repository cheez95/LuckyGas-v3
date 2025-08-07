import base64
import hashlib
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pyotp
import qrcode
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.cache import cache
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security_config import (
    get_2fa_config,
    get_api_key_config,
    get_lockout_policy,
    get_password_policy,
    get_session_config,
)

logger = get_logger(__name__)

# Enhanced password context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Increase rounds for better security
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise ValueError("Could not validate credentials")


def decode_refresh_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        return payload
    except JWTError:
        raise ValueError("Could not validate refresh token")


def verify_user_role(user, allowed_roles: list[str]) -> bool:
    """
    Verify if user has one of the allowed roles

    Args:
        user: User model instance
        allowed_roles: List of allowed role names

    Raises:
        HTTPException: If user role is not in allowed roles
    """
    from fastapi import HTTPException, status

    if user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")
    return True


class PasswordValidator:
    """Enhanced password validation with policy enforcement."""

    @staticmethod
    def validate_password(
        password: str, username: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """Validate password against security policy."""
        policy = get_password_policy()
        return policy.validate_password(password, username)

    @staticmethod
    async def check_password_history(user_id: int, password_hash: str) -> bool:
        """Check if password was used recently."""
        policy = get_password_policy()
        if policy.history_count == 0:
            return True

        # Get password history from cache
        history_key = f"password_history:{user_id}"
        history = await cache.get(history_key)

        if history:
            history_list = eval(history)  # Safe since we control the data
            # Check if password was used before
            for old_hash in history_list:
                if old_hash == password_hash:
                    return False

        return True

    @staticmethod
    async def update_password_history(user_id: int, password_hash: str):
        """Update password history after successful change."""
        policy = get_password_policy()
        if policy.history_count == 0:
            return

        history_key = f"password_history:{user_id}"
        history = await cache.get(history_key)

        if history:
            history_list = eval(history)
        else:
            history_list = []

        # Add new password hash
        history_list.insert(0, password_hash)

        # Keep only the required number of passwords
        history_list = history_list[: policy.history_count]

        # Store updated history
        await cache.set(
            history_key, str(history_list), expire=86400 * 365
        )  # Keep for 1 year


class AccountLockout:
    """Account lockout management for failed login attempts."""

    @staticmethod
    async def record_failed_attempt(identifier: str, is_ip: bool = False):
        """Record a failed login attempt."""
        policy = get_lockout_policy()
        if not policy.enabled:
            return

        if is_ip:
            key = f"lockout:ip:{identifier}"
            max_attempts = policy.ip_max_attempts
        else:
            key = f"lockout:user:{identifier}"
            max_attempts = policy.max_attempts

        # Get current attempt count
        attempts = await cache.get(f"{key}:attempts")
        attempts = int(attempts) + 1 if attempts else 1

        # Store attempt count
        await cache.set(
            f"{key}:attempts", str(attempts), expire=3600
        )  # Reset after 1 hour

        # Check if should lock
        if attempts >= max_attempts:
            # Get previous lockout count for progressive lockout
            lockout_count = await cache.get(f"{key}:count")
            lockout_count = int(lockout_count) + 1 if lockout_count else 1

            # Calculate lockout duration
            if is_ip:
                duration = policy.ip_lockout_duration_hours * 3600
            else:
                duration = policy.get_lockout_duration(lockout_count - 1) * 60

            # Set lockout
            await cache.set(f"{key}:locked", "1", expire=duration)
            await cache.set(
                f"{key}:count", str(lockout_count), expire=86400 * 30
            )  # Remember for 30 days

            logger.warning(
                f"Account locked: {identifier}",
                extra={
                    "identifier": identifier,
                    "is_ip": is_ip,
                    "attempts": attempts,
                    "duration_seconds": duration,
                },
            )

    @staticmethod
    async def is_locked(identifier: str, is_ip: bool = False) -> bool:
        """Check if account / IP is locked."""
        policy = get_lockout_policy()
        if not policy.enabled:
            return False

        if is_ip:
            key = f"lockout:ip:{identifier}"
        else:
            key = f"lockout:user:{identifier}"

        locked = await cache.get(f"{key}:locked")
        return locked == "1"

    @staticmethod
    async def clear_failed_attempts(identifier: str, is_ip: bool = False):
        """Clear failed attempts after successful login."""
        if is_ip:
            key = f"lockout:ip:{identifier}"
        else:
            key = f"lockout:user:{identifier}"

        await cache.delete(f"{key}:attempts")


class TwoFactorAuth:
    """Two - factor authentication management."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def generate_qr_code(username: str, secret: str) -> str:
        """Generate QR code for 2FA setup."""
        config = get_2fa_config()
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username, issuer_name=config.issuer_name
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verify TOTP token."""
        config = get_2fa_config()
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=config.totp_window)

    @staticmethod
    def generate_backup_codes(count: int = None) -> List[str]:
        """Generate backup codes for 2FA."""
        config = get_2fa_config()
        count = count or config.backup_codes_count

        codes = []
        for _ in range(count):
            code = "".join(
                secrets.choice("0123456789") for _ in range(config.backup_code_length)
            )
            codes.append(f"{code[:4]}-{code[4:]}")  # Format: XXXX - XXXX

        return codes

    @staticmethod
    async def send_sms_code(phone: str) -> str:
        """Send SMS verification code."""
        config = get_2fa_config()
        if not config.sms_enabled:
            raise ValueError("SMS 2FA is not enabled")

        # Generate code
        code = "".join(
            secrets.choice("0123456789") for _ in range(config.sms_code_length)
        )

        # Store code with expiry
        key = f"2fa:sms:{phone}"
        await cache.set(key, code, expire=config.sms_code_expiry_minutes * 60)

        # TODO: Integrate with SMS service to send code
        logger.info(f"SMS code generated for {phone}: {code}")  # Remove in production

        return code

    @staticmethod
    async def verify_sms_code(phone: str, code: str) -> bool:
        """Verify SMS code."""
        key = f"2fa:sms:{phone}"
        stored_code = await cache.get(key)

        if stored_code and stored_code == code:
            await cache.delete(key)  # One - time use
            return True

        return False


class APIKeyManager:
    """API key management for B2B partners."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key."""
        config = get_api_key_config()
        return config.generate_api_key()

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage."""
        config = get_api_key_config()
        return config.hash_api_key(api_key)

    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return associated data."""
        if not api_key:
            return None

        # Hash the key
        key_hash = APIKeyManager.hash_api_key(api_key)

        # Look up in cache (should be backed by database)
        key_data = await cache.get(f"api_key:{key_hash}")

        if key_data:
            data = eval(key_data)  # Safe since we control the data

            # Check expiry
            if data.get("expires_at"):
                expires = datetime.fromisoformat(data["expires_at"])
                if expires < datetime.utcnow():
                    return None

            return data

        return None

    @staticmethod
    async def create_api_key(
        name: str, scopes: List[str], expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new API key with specified scopes."""
        config = get_api_key_config()

        # Generate key
        api_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(api_key)

        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        elif config.rotation_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=config.rotation_days)

        # Store key data
        key_data = {
            "name": name,
            "scopes": scopes,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "rate_limit": config.default_rate_limit,
        }

        # Store in cache (should be persisted to database)
        await cache.set(f"api_key:{key_hash}", str(key_data))

        return {
            "api_key": api_key,
            "key_id": key_hash[:8],  # First 8 chars as ID
            **key_data,
        }


class DataEncryption:
    """Field - level encryption for sensitive data."""

    _fernet = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance."""
        if cls._fernet is None:
            # Use a derived key from the secret key
            key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(key)
            cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, data: str) -> str:
        """Encrypt sensitive data."""
        if not data:
            return data

        fernet = cls._get_fernet()
        encrypted = fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    @classmethod
    def decrypt(cls, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not encrypted_data:
            return encrypted_data

        try:
            fernet = cls._get_fernet()
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise ValueError("Failed to decrypt data")


class SessionManager:
    """Enhanced session management with security features."""

    @staticmethod
    async def create_session(user_id: int, remember_me: bool = False) -> Dict[str, Any]:
        """Create a new session with tokens."""
        config = get_session_config()

        # Check concurrent sessions
        sessions_key = f"sessions:user:{user_id}"
        current_sessions = await cache.get(sessions_key)

        if current_sessions:
            sessions = eval(current_sessions)
            if len(sessions) >= config.max_sessions_per_user:
                # Remove oldest session
                oldest = min(sessions, key=lambda x: x["created_at"])
                sessions.remove(oldest)
                await SessionManager.revoke_session(oldest["session_id"])
        else:
            sessions = []

        # Create session ID
        session_id = secrets.token_urlsafe(32)

        # Create tokens
        access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
        refresh_token_expires = timedelta(
            days=(
                config.remember_me_days
                if remember_me
                else config.refresh_token_expire_days
            )
        )

        access_token = create_access_token(
            data={"sub": str(user_id), "session_id": session_id},
            expires_delta=access_token_expires,
        )

        refresh_token = create_refresh_token(
            data={"sub": str(user_id), "session_id": session_id}
        )

        # Store session
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "remember_me": remember_me,
        }

        sessions.append(session_data)
        await cache.set(sessions_key, str(sessions), expire=86400 * 30)  # 30 days
        await cache.set(
            f"session:{session_id}",
            str(session_data),
            expire=config.session_timeout_minutes * 60,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
            "expires_in": config.access_token_expire_minutes * 60,
        }

    @staticmethod
    async def validate_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and update session activity."""
        config = get_session_config()

        session_data = await cache.get(f"session:{session_id}")
        if not session_data:
            return None

        session = eval(session_data)

        # Check idle timeout
        last_activity = datetime.fromisoformat(session["last_activity"])
        if datetime.utcnow() - last_activity > timedelta(
            minutes=config.idle_timeout_minutes
        ):
            await SessionManager.revoke_session(session_id)
            return None

        # Update last activity
        session["last_activity"] = datetime.utcnow().isoformat()
        await cache.set(
            f"session:{session_id}",
            str(session),
            expire=config.session_timeout_minutes * 60,
        )

        return session

    @staticmethod
    async def revoke_session(session_id: str):
        """Revoke a session."""
        await cache.delete(f"session:{session_id}")

    @staticmethod
    async def revoke_all_sessions(user_id: int):
        """Revoke all sessions for a user."""
        sessions_key = f"sessions:user:{user_id}"
        sessions = await cache.get(sessions_key)

        if sessions:
            sessions_list = eval(sessions)
            for session in sessions_list:
                await SessionManager.revoke_session(session["session_id"])

            await cache.delete(sessions_key)
