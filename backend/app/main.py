"""
Lucky Gas Backend - Simplified Main Application
Simple, working, maintainable!
"""
import sys
import os

# Add backend directory to Python path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session

# Dynamic config import based on environment
config_module = os.getenv('CONFIG_MODULE', 'app.core.config')
if config_module == 'app.core.config_production':
    from app.core.config_production import settings
else:
    from app.core.config import settings
from app.core.database import init_db, test_connection, get_db
import app.api.v1.auth as auth
import app.api.v1.customers as customers
import app.api.v1.dashboard as dashboard
import app.api.v1.websocket as websocket
import app.api.v1.orders as orders
import app.api.v1.drivers as drivers
import app.api.v1.routes_simple as routes
import app.api.v1.maps as maps
import app.api.v1.delivery_history_sync as delivery_history
from app.api.v1.auth import create_initial_admin
from app.core.database import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Simple startup and shutdown
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Test database connection
    if test_connection():
        logger.info("✅ Database connection successful")
        
        # Initialize database tables
        try:
            init_db()
            logger.info("✅ Database tables initialized")
            
            # Create initial admin user
            with SessionLocal() as db:
                create_initial_admin(db)
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    else:
        logger.error("❌ Database connection failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="幸福氣體配送管理系統 - Simplified and Working!",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    root_path="",
    root_path_in_servers=False,
    redirect_slashes=False  # Disable automatic redirect to prevent losing auth headers
)

# Configure CORS - MUST BE FIRST BEFORE ANY ROUTES
from app.core.security_config import security_config
from fastapi.middleware.trustedhost import TrustedHostMiddleware

cors_config = security_config.cors_config
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.get("allow_origins", settings.BACKEND_CORS_ORIGINS),
    allow_credentials=cors_config.get("allow_credentials", True),
    allow_methods=cors_config.get("allow_methods", ["*"]),
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=cors_config.get("max_age", 3600)
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Allow all hosts for Cloud Run
)


# Proxy fix middleware - MUST BE BEFORE OTHER MIDDLEWARE
@app.middleware("http")
async def fix_proxy_headers(request: Request, call_next):
    """Fix proxy headers for Cloud Run deployment"""
    # Cloud Run sets X-Forwarded-Proto header
    # We need to ensure FastAPI knows it's behind HTTPS proxy
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "https")
    forwarded_host = request.headers.get("X-Forwarded-Host", request.headers.get("host", ""))
    
    # Always force HTTPS in production or when behind proxy
    if forwarded_proto == "https" or settings.ENVIRONMENT in ["production", "staging"]:
        # Override the URL scheme to HTTPS
        request.scope["scheme"] = "https"
        # Also set the server host if available
        if forwarded_host:
            request.scope["server"] = (forwarded_host.split(":")[0], 443)
    
    # Process the request
    response = await call_next(request)
    
    # Add security headers to all responses
    if settings.ENVIRONMENT in ["production", "staging"]:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Forwarded-Proto"] = "https"
    
    # Fix redirect location headers to use HTTPS
    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("location", "")
        
        # Handle relative redirects (like /api/v1/customers/)
        if location.startswith("/"):
            # Build the full HTTPS URL
            if forwarded_host:
                location = f"https://{forwarded_host}{location}"
            else:
                # Use the original host if no forwarded host
                host = request.headers.get("host", "")
                location = f"https://{host}{location}"
            response.headers["location"] = location
        # Handle absolute HTTP redirects
        elif location.startswith("http://"):
            response.headers["location"] = location.replace("http://", "https://", 1)
    
    return response

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "detail": "資料驗證失敗",  # "Data validation failed"
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "detail": "系統錯誤，請稍後再試"  # "System error, please try again later"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "運行中",  # "Running"
        "environment": settings.ENVIRONMENT
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    # Test database connection
    db_healthy = test_connection()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": settings.APP_VERSION
    }


# API v1 endpoints
@app.get("/api/v1")
async def api_info():
    """API information"""
    return {
        "version": "1.0",
        "endpoints": [
            "/api/v1/auth",
            "/api/v1/customers",
            "/api/v1/orders",
            "/api/v1/deliveries",
            "/api/v1/drivers",
            "/api/v1/delivery-history"
        ]
    }


# Include routers - SIMPLIFIED ENDPOINTS ONLY!
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)

app.include_router(
    customers.router,
    prefix="/api/v1/customers",
    tags=["customers"]
)

app.include_router(
    dashboard.router,
    prefix="/api/v1/dashboard",
    tags=["dashboard"]
)

app.include_router(
    websocket.router,
    prefix="/api/v1/websocket",
    tags=["websocket"]
)

app.include_router(
    orders.router,
    prefix="/api/v1/orders",
    tags=["orders"]
)

app.include_router(
    drivers.router,
    prefix="/api/v1/drivers",
    tags=["drivers"]
)

app.include_router(
    routes.router,
    prefix="/api/v1/routes",
    tags=["routes"]
)

app.include_router(
    maps.router,
    prefix="/api/v1/maps",
    tags=["maps"]
)

app.include_router(
    delivery_history.router,
    prefix="/api/v1/delivery-history",
    tags=["delivery_history"]
)

# Additional endpoint for /api/v1/users/drivers
@app.get("/api/v1/users/drivers")
async def get_user_drivers(db: Session = Depends(get_db)):
    """Get drivers from users table"""
    return {
        "drivers": [],
        "total": 0
    }


# Cache statistics endpoint (for monitoring)
@app.get("/api/v1/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    from app.core.cache import get_all_cache_stats
    return get_all_cache_stats()


# Database statistics endpoint (for monitoring)
@app.get("/api/v1/db/stats")
async def db_stats():
    """Get database statistics"""
    from app.core.database import get_table_stats
    
    stats = {}
    for table in ['users', 'customers', 'orders', 'deliveries']:
        try:
            stats[table] = get_table_stats(table)
        except:
            stats[table] = {"error": "Could not get stats"}
    
    return stats


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn for development
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )