from typing import Dict, List, Optional
from fastapi import Request, Response
import hashlib
import base64
import secrets

from app.core.config import settings


class ContentSecurityPolicy:
    """Content Security Policy (CSP) implementation for XSS protection."""
    
    def __init__(self):
        self.nonce_length = 32
        self.report_uri = f"{settings.API_URL}/api/v1/security/csp-report"
        
        # Base CSP directives
        self.base_policy = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'nonce-{nonce}'"],
            "style-src": ["'self'", "'nonce-{nonce}'", "https://fonts.googleapis.com"],
            "img-src": ["'self'", "data:", "https:", "blob:"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "connect-src": ["'self'", settings.API_URL, "wss:", "https:"],
            "media-src": ["'self'", "blob:", settings.CLOUDFRONT_URL],
            "object-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
            "block-all-mixed-content": [],
            "report-uri": [self.report_uri]
        }
        
        # Environment-specific policies
        self.env_policies = {
            "development": {
                "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
                "style-src": ["'self'", "'unsafe-inline'"],
            },
            "staging": {
                "script-src": ["'self'", "'nonce-{nonce}'", "'strict-dynamic'"],
            },
            "production": {
                "script-src": ["'self'", "'nonce-{nonce}'", "'strict-dynamic'"],
                "require-trusted-types-for": ["'script'"],
            }
        }
    
    def generate_nonce(self) -> str:
        """Generate a cryptographically secure nonce."""
        return base64.b64encode(
            secrets.token_bytes(self.nonce_length)
        ).decode('utf-8').rstrip('=')
    
    def build_policy(self, nonce: str, environment: str = "production") -> str:
        """Build CSP header value."""
        policy = self.base_policy.copy()
        
        # Apply environment-specific overrides
        if environment in self.env_policies:
            for directive, values in self.env_policies[environment].items():
                policy[directive] = values
        
        # Build policy string
        policy_parts = []
        for directive, values in policy.items():
            if not values:
                policy_parts.append(directive)
            else:
                # Replace nonce placeholder
                processed_values = [
                    v.format(nonce=nonce) if '{nonce}' in v else v
                    for v in values
                ]
                policy_parts.append(f"{directive} {' '.join(processed_values)}")
        
        return "; ".join(policy_parts)
    
    def calculate_hash(self, content: str, algorithm: str = "sha256") -> str:
        """Calculate hash for inline scripts/styles."""
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(content.encode('utf-8'))
        hash_digest = base64.b64encode(hash_obj.digest()).decode('utf-8')
        return f"'{algorithm}-{hash_digest}'"
    
    async def set_csp_header(
        self,
        response: Response,
        nonce: Optional[str] = None,
        report_only: bool = False
    ):
        """Set CSP header on response."""
        if nonce is None:
            nonce = self.generate_nonce()
        
        policy = self.build_policy(nonce, settings.ENVIRONMENT)
        
        header_name = "Content-Security-Policy"
        if report_only:
            header_name = "Content-Security-Policy-Report-Only"
        
        response.headers[header_name] = policy
        
        # Store nonce for template rendering
        response.headers["X-CSP-Nonce"] = nonce
        
        return nonce


class SecurityHeaders:
    """Additional security headers for defense in depth."""
    
    def __init__(self):
        self.headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # XSS protection for older browsers
            "X-XSS-Protection": "1; mode=block",
            
            # Clickjacking protection
            "X-Frame-Options": "DENY",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy (formerly Feature Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # HSTS (in production only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload" if settings.ENVIRONMENT == "production" else None,
            
            # DNS prefetch control
            "X-DNS-Prefetch-Control": "off",
            
            # Download options for IE
            "X-Download-Options": "noopen",
            
            # Permitted cross-domain policies
            "X-Permitted-Cross-Domain-Policies": "none"
        }
    
    async def set_security_headers(self, response: Response):
        """Set all security headers on response."""
        for header, value in self.headers.items():
            if value is not None:
                response.headers[header] = value


class SubresourceIntegrity:
    """Generate and verify Subresource Integrity (SRI) hashes."""
    
    @staticmethod
    def generate_sri_hash(content: bytes, algorithms: List[str] = ["sha384"]) -> str:
        """Generate SRI hash for resource."""
        hashes = []
        
        for algo in algorithms:
            hash_obj = hashlib.new(algo)
            hash_obj.update(content)
            hash_digest = base64.b64encode(hash_obj.digest()).decode('utf-8')
            hashes.append(f"{algo}-{hash_digest}")
        
        return " ".join(hashes)
    
    @staticmethod
    def generate_script_tag(
        src: str,
        sri_hash: str,
        nonce: Optional[str] = None,
        defer: bool = False,
        async_load: bool = False
    ) -> str:
        """Generate secure script tag with SRI."""
        attrs = [
            f'src="{src}"',
            f'integrity="{sri_hash}"',
            'crossorigin="anonymous"'
        ]
        
        if nonce:
            attrs.append(f'nonce="{nonce}"')
        if defer:
            attrs.append('defer')
        if async_load:
            attrs.append('async')
        
        return f'<script {" ".join(attrs)}></script>'
    
    @staticmethod
    def generate_link_tag(
        href: str,
        sri_hash: str,
        rel: str = "stylesheet",
        media: Optional[str] = None
    ) -> str:
        """Generate secure link tag with SRI."""
        attrs = [
            f'rel="{rel}"',
            f'href="{href}"',
            f'integrity="{sri_hash}"',
            'crossorigin="anonymous"'
        ]
        
        if media:
            attrs.append(f'media="{media}"')
        
        return f'<link {" ".join(attrs)}>'


# Global instances
csp = ContentSecurityPolicy()
security_headers = SecurityHeaders()
sri = SubresourceIntegrity()


# Middleware for automatic security headers
async def security_headers_middleware(request: Request, call_next):
    """Middleware to automatically add security headers."""
    response = await call_next(request)
    
    # Skip for specific paths (e.g., health checks)
    skip_paths = ["/health", "/metrics"]
    if request.url.path in skip_paths:
        return response
    
    # Set security headers
    await security_headers.set_security_headers(response)
    
    # Set CSP for HTML responses
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        nonce = await csp.set_csp_header(response, report_only=False)
        # Store nonce in request state for template rendering
        request.state.csp_nonce = nonce
    
    return response


# CSP violation report handler
async def handle_csp_report(request: Request) -> Dict:
    """Handle CSP violation reports."""
    try:
        report = await request.json()
        
        # Log the violation
        violation = report.get("csp-report", {})
        
        # Extract important fields
        violated_directive = violation.get("violated-directive", "unknown")
        blocked_uri = violation.get("blocked-uri", "unknown")
        document_uri = violation.get("document-uri", "unknown")
        
        # Log for monitoring
        print(f"CSP Violation: {violated_directive} blocked {blocked_uri} on {document_uri}")
        
        # In production, send to monitoring service
        if settings.ENVIRONMENT == "production":
            # Send to Sentry, DataDog, etc.
            pass
        
        return {"status": "reported"}
    
    except Exception as e:
        print(f"Error processing CSP report: {e}")
        return {"status": "error"}