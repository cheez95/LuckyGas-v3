#!/usr/bin/env python3
"""Fix security headers with spaces in them."""

import re
from pathlib import Path

def fix_security_headers():
    """Fix security headers that have spaces in them."""
    
    # Security headers that should be fixed
    header_replacements = [
        ("X - XSS - Protection", "X-XSS-Protection"),
        ("X - Content - Type - Options", "X-Content-Type-Options"),
        ("X - Frame - Options", "X-Frame-Options"),
        ("Referrer - Policy", "Referrer-Policy"),
        ("Permissions - Policy", "Permissions-Policy"),
        ("Strict - Transport - Security", "Strict-Transport-Security"),
        ("Content - Security - Policy", "Content-Security-Policy"),
        ("Server", "Server"),  # This one is okay
        # Also fix CSP directive values
        ("default - src", "default-src"),
        ("script - src", "script-src"),
        ("style - src", "style-src"),
        ("font - src", "font-src"),
        ("img - src", "img-src"),
        ("connect - src", "connect-src"),
        ("frame - ancestors", "frame-ancestors"),
        ("'sel'", "'self'"),  # Fix 'sel' -> 'self'
        ("'unsafe - inline'", "'unsafe-inline'"),
        ("'unsafe - eval'", "'unsafe-eval'"),
        ("max - age", "max-age"),
        ("strict - origin - when - cross - origin", "strict-origin-when-cross-origin"),
        # CORS headers
        ("Content - Type", "Content-Type"),
        ("X - Request - ID", "X-Request-ID"),
        ("X - CSRF - Token", "X-CSRF-Token"),
        ("X - Requested - With", "X-Requested-With"),
        ("Accept - Language", "Accept-Language"),
        ("Accept - Encoding", "Accept-Encoding"),
        ("Access - Control - Request - Headers", "Access-Control-Request-Headers"),
        ("Access - Control - Request - Method", "Access-Control-Request-Method"),
        ("X - Process - Time", "X-Process-Time"),
        ("X - RateLimit - Limit", "X-RateLimit-Limit"),
        ("X - RateLimit - Remaining", "X-RateLimit-Remaining"),
        ("X - RateLimit - Reset", "X-RateLimit-Reset"),
        ("X - Total - Count", "X-Total-Count"),
        ("X - Blocked", "X-Blocked"),
        # API paths
        ("/api / v1 / docs", "/api/v1/docs"),
        ("/api / v1 / redoc", "/api/v1/redoc"),
        ("/api / v1 / openapi.json", "/api/v1/openapi.json"),
        ("/api / v1 / auth", "/api/v1/auth"),
        ("/api / v1 / customers", "/api/v1/customers"),
        ("/api / v1 / orders", "/api/v1/orders"),
        ("/api / v1 / order - templates", "/api/v1/order-templates"),
        ("/api / v1 / routes", "/api/v1/routes"),
        ("/api / v1 / predictions", "/api/v1/predictions"),
        ("/api / v1 / delivery - history", "/api/v1/delivery-history"),
        ("/api / v1 / products", "/api/v1/products"),
        ("/api / v1 / drivers", "/api/v1/drivers"),
        ("/api / v1 / communications", "/api/v1/communications"),
        ("/api / v1 / websocket", "/api/v1/websocket"),
        ("/api / v1 / invoices", "/api/v1/invoices"),
        ("/api / v1 / payments", "/api/v1/payments"),
        ("/api / v1 / financial - reports", "/api/v1/financial-reports"),
        ("/api / v1 / banking", "/api/v1/banking"),
        ("/api / v1 / analytics", "/api/v1/analytics"),
        ("/api / v1 / maps", "/api/v1/maps"),
        ("/api / v1", "/api/v1"),
        ("/api / health", "/api/health"),
        ("/api / v1 / health", "/api/v1/health"),
        # Other middleware headers
        ("X - Forwarded - For", "X-Forwarded-For"),
        ("user - agent", "user-agent"),
        ("content - length", "content-length"),
        # Fix other issues
        ("nosnif", "nosniff"),  # Fix typo in nosniff
        ("data:text / html", "data:text/html"),
        # Regex patterns with spaces
        (r"[A - Z]", r"[A-Z]"),
        (r"[a - z]", r"[a-z]"),
        (r"[a - zA - Z0 - 9._%+-]", r"[a-zA-Z0-9._%+-]"),
        (r"[a - zA - Z0 - 9.-]", r"[a-zA-Z0-9.-]"),
        (r"[a - zA - Z]", r"[a-zA-Z]"),
        # Fix spacing in patterns
        (r"% 2e", r"%2e"),
        (r"% 252e", r"%252e"),
        # Other fixes
        ("- orphan", "-orphan"),
        ("AES - 256 - GCM", "AES-256-GCM"),
        ("%Y % m % d", "%Y%m%d"),
        ("LuckyGas - API", "LuckyGas-API")
    ]
    
    # Files to fix
    files_to_fix = [
        "/Users/lgee258/Desktop/LuckyGas-v3/backend/app/middleware/security.py",
        "/Users/lgee258/Desktop/LuckyGas-v3/backend/app/core/security_config.py",
        "/Users/lgee258/Desktop/LuckyGas-v3/backend/app/main.py",
    ]
    
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            original_content = content
            
            for old_value, new_value in header_replacements:
                content = content.replace(old_value, new_value)
            
            if content != original_content:
                path.write_text(content)
                print(f"Fixed: {file_path}")
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    fix_security_headers()