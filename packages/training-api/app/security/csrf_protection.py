import hmac
import hashlib
import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer

from app.core.config import settings


class CSRFProtection:
    """CSRF protection using double-submit cookie pattern."""
    
    def __init__(
        self,
        secret_key: str = settings.JWT_SECRET,
        token_name: str = "csrf-token",
        header_name: str = "X-CSRF-Token",
        cookie_name: str = "_csrf",
        max_age: int = 3600
    ):
        self.secret_key = secret_key.encode()
        self.token_name = token_name
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.max_age = max_age
    
    def generate_token(self) -> Tuple[str, str]:
        """Generate CSRF token and cookie value."""
        # Generate random token
        token = secrets.token_urlsafe(32)
        
        # Create timestamp
        timestamp = int(datetime.utcnow().timestamp())
        
        # Create cookie value with timestamp
        cookie_data = f"{token}:{timestamp}"
        signature = self._sign(cookie_data)
        cookie_value = f"{cookie_data}:{signature}"
        
        return token, cookie_value
    
    def _sign(self, data: str) -> str:
        """Sign data with HMAC."""
        return hmac.new(
            self.secret_key,
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def validate_token(self, token: str, cookie_value: str) -> bool:
        """Validate CSRF token against cookie."""
        try:
            # Parse cookie value
            parts = cookie_value.split(":")
            if len(parts) != 3:
                return False
            
            cookie_token, timestamp_str, signature = parts
            
            # Verify signature
            expected_signature = self._sign(f"{cookie_token}:{timestamp_str}")
            if not hmac.compare_digest(signature, expected_signature):
                return False
            
            # Check timestamp
            timestamp = int(timestamp_str)
            current_time = int(datetime.utcnow().timestamp())
            if current_time - timestamp > self.max_age:
                return False
            
            # Compare tokens
            return hmac.compare_digest(token, cookie_token)
        
        except (ValueError, AttributeError):
            return False
    
    async def set_csrf_cookie(self, response: Response) -> str:
        """Set CSRF cookie and return token."""
        token, cookie_value = self.generate_token()
        
        response.set_cookie(
            key=self.cookie_name,
            value=cookie_value,
            max_age=self.max_age,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="strict"
        )
        
        return token
    
    async def validate_request(self, request: Request) -> bool:
        """Validate CSRF token in request."""
        # Skip validation for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        
        # Get token from header
        token = request.headers.get(self.header_name)
        if not token:
            # Try to get from form data
            if hasattr(request, "form"):
                form = await request.form()
                token = form.get(self.token_name)
        
        if not token:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing"
            )
        
        # Get cookie value
        cookie_value = request.cookies.get(self.cookie_name)
        if not cookie_value:
            raise HTTPException(
                status_code=403,
                detail="CSRF cookie missing"
            )
        
        # Validate
        if not self.validate_token(token, cookie_value):
            raise HTTPException(
                status_code=403,
                detail="Invalid CSRF token"
            )
        
        return True


class OriginVerification:
    """Additional protection by verifying request origin."""
    
    def __init__(self, allowed_origins: list = None):
        self.allowed_origins = allowed_origins or [settings.FRONTEND_URL]
    
    async def verify_origin(self, request: Request) -> bool:
        """Verify request origin/referer."""
        # Skip for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        
        # Check Origin header
        origin = request.headers.get("Origin")
        if origin and origin in self.allowed_origins:
            return True
        
        # Fallback to Referer
        referer = request.headers.get("Referer")
        if referer:
            # Extract origin from referer
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            if referer_origin in self.allowed_origins:
                return True
        
        raise HTTPException(
            status_code=403,
            detail="Invalid origin"
        )


class SameSiteProtection:
    """Enhanced CSRF protection using SameSite cookies."""
    
    @staticmethod
    def set_auth_cookie(
        response: Response,
        name: str,
        value: str,
        max_age: Optional[int] = None
    ):
        """Set authentication cookie with SameSite protection."""
        response.set_cookie(
            key=name,
            value=value,
            max_age=max_age,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax"  # Allows top-level navigation
        )
    
    @staticmethod
    def set_sensitive_cookie(
        response: Response,
        name: str,
        value: str,
        max_age: Optional[int] = None
    ):
        """Set sensitive cookie with strict SameSite."""
        response.set_cookie(
            key=name,
            value=value,
            max_age=max_age,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="strict"  # Maximum protection
        )


# Global CSRF protection instance
csrf_protection = CSRFProtection()
origin_verification = OriginVerification()


# Middleware for automatic CSRF protection
async def csrf_middleware(request: Request, call_next):
    """Middleware to automatically handle CSRF protection."""
    # Skip for API endpoints that use different auth
    if request.url.path.startswith("/api/v1/auth/"):
        return await call_next(request)
    
    # Validate CSRF for state-changing requests
    if request.method not in ["GET", "HEAD", "OPTIONS"]:
        await csrf_protection.validate_request(request)
        await origin_verification.verify_origin(request)
    
    response = await call_next(request)
    
    # Set CSRF cookie for authenticated users
    if hasattr(request.state, "user") and request.state.user:
        if request.method == "GET" and not request.cookies.get(csrf_protection.cookie_name):
            token = await csrf_protection.set_csrf_cookie(response)
            # Also return token in header for SPA
            response.headers[csrf_protection.header_name] = token
    
    return response