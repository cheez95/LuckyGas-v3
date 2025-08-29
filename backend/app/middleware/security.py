"""
Comprehensive security middleware for production hardening.

This module implements multiple security layers:
- Request validation and sanitization
- SQL injection prevention
- XSS protection
- Security headers
- Request size limits
- Suspicious activity detection
"""

import hashlib
import json
import re
import secrets
from datetime import datetime

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import cache
from app.core.config import settings
from app.core.logging import get_logger
from starlette.requests import Request
from starlette.responses import Response

logger = get_logger(__name__)


class SecurityHeaders:
    """Security headers configuration based on OWASP recommendations."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers based on environment."""
        headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (formerly Feature Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            # Remove server header
            "Server": "LuckyGas-API",
        }

        if settings.is_production():
            # Strict Transport Security (HSTS) - only in production with HTTPS
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

            # Content Security Policy - stricter in production
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' wss: https://api.luckygas.tw https://*.googleapis.com; "
                "frame-ancestors 'none';"
            )
        else:
            # More lenient CSP for development
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* 127.0.0.1:*; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https: http: blob:; "
                "connect-src 'self' ws: wss: http: https:;"
            )

        return headers


class SecurityValidation:
    """Input validation and sanitization utilities."""

    # Patterns for SQL injection detection
    SQL_INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|\#|\/\*|\*\/)",  # SQL comments
        r"(\bor\b\s*\d+\s*=\s*\d+)",  # OR 1=1
        r"(\band\b\s*\d+\s*=\s*\d+)",  # AND 1=1
        r"(;|'|\")",  # Common injection characters
        r"(xp_|sp_)",  # SQL Server stored procedures
        r"(benchmark|sleep|waitfor)",  # Time - based attacks
    ]

    # Patterns for XSS detection
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"vbscript:",
        r"data:text/html",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\/",
        r"%2e %2e/",
        r"%252e %252e/",
        r"\.\./\.\./",
        r"\.\.\\\.\.\\",
    ]

    @classmethod
    def is_sql_injection_attempt(cls, value: str) -> bool:
        """Check if input contains potential SQL injection."""
        if not value:
            return False

        value_lower = value.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False

    @classmethod
    def is_xss_attempt(cls, value: str) -> bool:
        """Check if input contains potential XSS."""
        if not value:
            return False

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @classmethod
    def is_path_traversal_attempt(cls, value: str) -> bool:
        """Check if input contains path traversal attempts."""
        if not value:
            return False

        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_input(cls, value: str) -> str:
        """Sanitize input by removing dangerous characters."""
        if not value:
            return value

        # Remove null bytes
        value = value.replace("\x00", "")

        # HTML encode dangerous characters
        replacements = {
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
            "/": "&#x2F;",
        }

        for char, replacement in replacements.items():
            value = value.replace(char, replacement)

        return value


class SuspiciousActivityDetector:
    """Detect and track suspicious activities."""

    def __init__(self):
        self.suspicious_patterns = {
            "rapid_404": {"threshold": 10, "window": 60},  # 10 404s in 60 seconds
            "auth_failures": {
                "threshold": 5,
                "window": 300,
            },  # 5 failed logins in 5 minutes
            "scanning": {
                "threshold": 20,
                "window": 60,
            },  # 20 different endpoints in 60 seconds
            "large_requests": {
                "threshold": 5,
                "window": 60,
            },  # 5 large requests in 60 seconds
        }

    async def track_activity(
        self, client_id: str, activity_type: str, details: Dict = None
    ):
        """Track potentially suspicious activity."""
        key = f"security:activity:{activity_type}:{client_id}"

        try:
            # Get current activity count
            current = await cache.get(key)
            count = int(current) if current else 0
            count += 1

            # Update count with expiration
            pattern = self.suspicious_patterns.get(activity_type, {"window": 60})
            await cache.set(key, str(count), expire=pattern["window"])

            # Check if threshold exceeded
            if count >= pattern["threshold"]:
                await self._handle_suspicious_activity(
                    client_id, activity_type, count, details
                )

        except Exception as e:
            logger.error(f"Activity tracking error: {str(e)}", exc_info=True)

    async def _handle_suspicious_activity(
        self, client_id: str, activity_type: str, count: int, details: Dict = None
    ):
        """Handle detected suspicious activity."""
        logger.warning(
            "Suspicious activity detected",
            extra={
                "client_id": client_id,
                "activity_type": activity_type,
                "count": count,
                "details": details,
            },
        )

        # Temporarily block the client
        block_key = f"security:blocked:{client_id}"
        block_duration = 3600  # 1 hour

        if activity_type in ["auth_failures", "scanning"]:
            await cache.set(block_key, "1", expire=block_duration)

            # Log security event
            await self._log_security_event(client_id, activity_type, count, details)

    async def _log_security_event(
        self, client_id: str, event_type: str, count: int, details: Dict = None
    ):
        """Log security events for audit trail."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client_id,
            "event_type": event_type,
            "count": count,
            "details": details,
        }

        # Store in cache for immediate access (should be persisted to database)
        key = f"security:events:{datetime.utcnow().strftime('%Y%m%d')}"
        events = await cache.get(key)

        if events:
            events_list = json.loads(events)
        else:
            events_list = []

        events_list.append(event)
        await cache.set(
            key, json.dumps(events_list), expire=86400 * 7
        )  # Keep for 7 days

    async def is_blocked(self, client_id: str) -> bool:
        """Check if client is blocked."""
        block_key = f"security:blocked:{client_id}"
        result = await cache.get(block_key)
        return result == "1"


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware implementing multiple protection layers.
    """

    # Maximum request size (10MB)
    MAX_REQUEST_SIZE = 10 * 1024 * 1024

    # Maximum URL length
    MAX_URL_LENGTH = 2048

    # Maximum header size
    MAX_HEADER_SIZE = 8192

    def __init__(self, app):
        super().__init__(app)
        self.detector = SuspiciousActivityDetector()
        self.validator = SecurityValidation()

    async def dispatch(self, request: Request, call_next):
        """Process request with security checks."""
        start_time = datetime.utcnow()

        # Get client identifier
        client_id = self._get_client_id(request)

        try:
            # Check if client is blocked
            if await self.detector.is_blocked(client_id):
                return self._blocked_response()

            # Validate request
            validation_result = await self._validate_request(request, client_id)
            if validation_result:
                return validation_result

            # Add security headers to request state for logging
            request.state.security_validated = True
            request.state.client_id = client_id

            # Process request
            response = await call_next(request)

            # Track 404s for scanning detection
            if response.status_code == 404:
                await self.detector.track_activity(
                    client_id, "rapid_404", {"path": str(request.url.path)}
                )

            # Add security headers to response
            for header, value in SecurityHeaders.get_security_headers().items():
                response.headers[header] = value

            # Log request for audit trail (only in production)
            if settings.is_production():
                await self._audit_log_request(request, response, start_time)

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}", exc_info=True)
            return JSONResponse(status_code=500, content={"detail": "內部伺服器錯誤"})

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for tracking."""
        # Try to get real IP from headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(", ")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        # Hash for privacy
        return hashlib.sha256(client_ip.encode()).hexdigest()[:16]

    async def _validate_request(
        self, request: Request, client_id: str
    ) -> Optional[Response]:
        """Validate incoming request for security threats."""

        # Check URL length
        if len(str(request.url)) > self.MAX_URL_LENGTH:
            await self.detector.track_activity(
                client_id, "scanning", {"reason": "long_url"}
            )
            return JSONResponse(status_code=414, content={"detail": "請求 URL 過長"})

        # Check headers size
        total_header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if total_header_size > self.MAX_HEADER_SIZE:
            await self.detector.track_activity(
                client_id, "large_requests", {"reason": "large_headers"}
            )
            return JSONResponse(status_code=431, content={"detail": "請求標頭過大"})

        # Check for path traversal in URL
        if self.validator.is_path_traversal_attempt(str(request.url)):
            await self.detector.track_activity(
                client_id, "scanning", {"reason": "path_traversal"}
            )
            logger.warning(f"Path traversal attempt from {client_id}: {request.url}")
            return JSONResponse(status_code=400, content={"detail": "無效的請求路徑"})

        # Validate query parameters
        for param_name, param_value in request.query_params.items():
            if isinstance(param_value, str):
                # Check for SQL injection
                if self.validator.is_sql_injection_attempt(param_value):
                    await self.detector.track_activity(
                        client_id,
                        "scanning",
                        {"reason": "sql_injection", "param": param_name},
                    )
                    logger.warning(
                        f"SQL injection attempt from {client_id}: {param_name}={param_value}"
                    )
                    return JSONResponse(
                        status_code=400, content={"detail": "無效的請求參數"}
                    )

                # Check for XSS
                if self.validator.is_xss_attempt(param_value):
                    await self.detector.track_activity(
                        client_id, "scanning", {"reason": "xss", "param": param_name}
                    )
                    logger.warning(
                        f"XSS attempt from {client_id}: {param_name}={param_value}"
                    )
                    return JSONResponse(
                        status_code=400, content={"detail": "無效的請求參數"}
                    )

        # Check Content - Length for POST / PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
                await self.detector.track_activity(
                    client_id, "large_requests", {"size": content_length}
                )
                return JSONResponse(status_code=413, content={"detail": "請求內容過大"})

        return None

    def _blocked_response(self) -> JSONResponse:
        """Response for blocked clients."""
        return JSONResponse(
            status_code=403,
            content={"detail": "存取被拒絕", "error": "access_denied"},
            headers={"X-Blocked": "1"},
        )

    async def _audit_log_request(
        self, request: Request, response: Response, start_time: datetime
    ):
        """Log requests for audit trail."""
        # Only log non - GET requests and failed requests
        if request.method != "GET" or response.status_code >= 400:
            duration = (datetime.utcnow() - start_time).total_seconds()

            log_entry = {
                "timestamp": start_time.isoformat(),
                "client_id": request.state.client_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration": duration,
                "user_agent": request.headers.get("user-agent", ""),
            }

            # Add user ID if authenticated
            if hasattr(request.state, "user_id"):
                log_entry["user_id"] = request.state.user_id

            # Store in audit log (implement proper persistence)
            audit_key = f"audit:requests:{datetime.utcnow().strftime('%Y%m%d')}"
            try:
                logs = await cache.get(audit_key)
                if logs:
                    logs_list = json.loads(logs)
                else:
                    logs_list = []

                logs_list.append(log_entry)
                await cache.set(
                    audit_key, json.dumps(logs_list), expire=86400 * 30
                )  # Keep 30 days
            except Exception as e:
                logger.error(f"Audit logging error: {str(e)}")


class CSRFProtection:
    """CSRF protection for state - changing operations."""

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a CSRF token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def validate_csrf_token(request: Request, token: str) -> bool:
        """Validate CSRF token."""
        # Get session ID or user ID
        session_id = getattr(request.state, "session_id", None)
        user_id = getattr(request.state, "user_id", None)

        if not session_id and not user_id:
            return False

        # Get stored token
        key = f"csrf:{user_id or session_id}"
        stored_token = await cache.get(key)

        return stored_token == token


# Export middleware class
__all__ = [
    "SecurityMiddleware",
    "SecurityHeaders",
    "SecurityValidation",
    "CSRFProtection",
]
