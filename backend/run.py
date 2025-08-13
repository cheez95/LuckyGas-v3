#!/usr/bin/env python3
"""
Production server runner for Lucky Gas Backend.
Properly handles PORT environment variable for Cloud Run deployment.
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable (Cloud Run sets this to 8080)
    port = int(os.environ.get("PORT", 8080))
    
    # Get other configuration from environment
    host = os.environ.get("HOST", "0.0.0.0")
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    
    # Important: reload=False for production!
    reload = os.environ.get("ENVIRONMENT", "production").lower() == "development"
    
    print(f"[STARTUP] Starting Lucky Gas Backend server...", file=sys.stderr)
    print(f"[STARTUP] Host: {host}", file=sys.stderr)
    print(f"[STARTUP] Port: {port}", file=sys.stderr)
    print(f"[STARTUP] Log Level: {log_level}", file=sys.stderr)
    print(f"[STARTUP] Reload: {reload}", file=sys.stderr)
    print(f"[STARTUP] PORT env var: {os.environ.get('PORT', 'NOT SET')}", file=sys.stderr)
    
    # Start uvicorn with the correct configuration
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,  # False in production
        access_log=True,
        use_colors=False  # Disable colors for Cloud Run logs
    )