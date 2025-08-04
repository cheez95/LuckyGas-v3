import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    analytics,
    api_keys,
    auth,
    banking,
    communications,
    customers,
    delivery_history,
    driver,
    financial_reports,
    health,
    invoices,
    maps_proxy,
    monitoring,
    notifications,
    order_templates,
    orders,
    payments,
    predictions,
    products,
    routes,
    sms,
    websocket,
)
from app.api.v1.admin import migration

# Socket.IO handler removed during compaction
from app.core.config import settings
from app.core.database import create_db_and_tables, engine

# from app.core.db_metrics import DatabaseMetricsCollector  # Removed during compaction
from app.core.env_validation import validate_environment
from app.core.logging import get_logger, setup_logging
from app.middleware.enhanced_rate_limiting import (
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
    limiter,
)
from app.middleware.logging import CorrelationIdMiddleware, LoggingMiddleware
from app.middleware.metrics import MetricsMiddleware

# from app.core.api_security import APISecurityMiddleware, api_validator, rate_limiter  # TODO: Fix missing dependencies
from app.middleware.performance import PerformanceMiddleware
from app.middleware.security import SecurityMiddleware
from app.services.websocket_service import websocket_manager

# from prometheus_fastapi_instrumentator import Instrumentator  # Removed during compaction


# Setup structured logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Lucky Gas backend service")

    # Validate environment variables
    # Note: Environment validation is done by Pydantic Settings during initialization
    # validate_environment()
    logger.info("Environment loaded from settings")

    # Create database tables
    await create_db_and_tables()
    logger.info("Database tables created/verified")

    # Initialize custom cache service
    from app.core.cache import cache

    await cache.connect()
    logger.info("Custom cache service initialized")

    # Initialize performance monitoring
    from app.middleware.performance import PerformanceMiddleware

    app.state.performance_middleware = PerformanceMiddleware(redis_client=cache.redis)
    logger.info("Performance monitoring initialized")

    # Database metrics collector removed during compaction
    # db_metrics_collector = DatabaseMetricsCollector(engine)
    # import asyncio
    # metrics_task = asyncio.create_task(db_metrics_collector.start())
    # logger.info("Database metrics collector started")

    # Initialize WebSocket manager
    await websocket_manager.initialize()
    logger.info("WebSocket manager initialized")

    # API monitoring removed during compaction
    # from app.core.api_monitoring import init_api_monitoring, api_monitor
    # init_api_monitoring()
    # await api_monitor.start_monitoring(interval=300)  # 5 minute interval
    # logger.info("API monitoring initialized")

    # Initialize enhanced feature flag service
    # TODO: Fix enum mismatch between feature_flag.py and audit.py AuditAction enums
    # from app.services.feature_flags_enhanced import get_feature_flag_service
    # feature_service = await get_feature_flag_service()
    # logger.info("Enhanced feature flag service initialized with persistence")

    # Initialize enhanced sync service
    # TODO: Fix initialization issues
    # from app.services.sync_service_enhanced import get_sync_service
    # sync_service = await get_sync_service()
    # logger.info("Enhanced sync service initialized with persistence")

    # Initialize enhanced monitoring
    # TODO: Fix monitoring service initialization
    # from app.core.enhanced_monitoring import monitoring_service
    # await monitoring_service.initialize(app)
    # logger.info("Enhanced monitoring service initialized")

    yield

    # Shutdown
    logger.info("Shutting down Lucky Gas backend service")

    # Close WebSocket connections
    await websocket_manager.close()
    logger.info("WebSocket connections closed")

    # Metrics collector removed during compaction
    # db_metrics_collector.stop()
    # metrics_task.cancel()

    # Enhanced sync service removed during compaction
    # from app.services.sync_service import get_sync_service
    # sync_service = await get_sync_service()
    # await sync_service.close()
    # logger.info("Enhanced sync service closed")

    # Enhanced feature flag service removed during compaction
    # from app.services.feature_flags import get_feature_flag_service
    # feature_service = await get_feature_flag_service()
    # await feature_service.close()
    # logger.info("Enhanced feature flag service closed")

    # Close custom cache connection
    from app.core.cache import cache

    await cache.disconnect()
    logger.info("Cleanup completed")


app = FastAPI(
    title="Lucky Gas Delivery Management System",
    description="幸福氣配送管理系統 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# Socket.IO app mounting removed during compaction
# Use WebSocket endpoint instead

# Configure CORS with enhanced settings
cors_origins = settings.get_all_cors_origins()

# Add environment-specific CORS origins
if settings.is_development():
    # Additional development origins
    cors_origins.extend(["http://localhost:*", "http://127.0.0.1:*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-CSRF-Token",
        "X-Requested-With",
        "Accept",
        "Accept-Language",
        "Accept-Encoding",
        "Access-Control-Request-Headers",
        "Access-Control-Request-Method",
    ],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Total-Count",
    ],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add security middleware (should be first)
app.add_middleware(SecurityMiddleware)

# Add API security middleware for key validation and rate limiting
# app.add_middleware(APISecurityMiddleware, validator=api_validator, rate_limiter=rate_limiter)  # TODO: Fix missing dependencies

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add slowapi rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add logging middleware (should be early in the chain)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Add performance monitoring middleware
# TODO: Fix performance middleware initialization
# @app.middleware("http")
# async def performance_middleware(request: Request, call_next):
#     if hasattr(app.state, 'performance_middleware'):
#         return await app.state.performance_middleware(request, call_next)
#     return await call_next(request)

# Add HTTPS redirect middleware for production
if settings.ENVIRONMENT.value == "production":
    app.add_middleware(HTTPSRedirectMiddleware)


# Add timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(f"{process_time:.3f}")
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Request validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
            "body": str(exc.body) if exc.body else None,
        },
    )
    # Convert validation errors to serializable format
    errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": error.get("loc", []),
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        errors.append(serializable_error)

    return JSONResponse(
        status_code=422, content={"detail": "資料驗證失敗", "errors": errors}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(
        f"HTTP error: {exc.status_code}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "http_error"},
    )


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(
    order_templates.router, prefix="/api/v1/order-templates", tags=["order_templates"]
)
# Consolidated routes router
app.include_router(routes.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(
    predictions.router, prefix="/api/v1/predictions", tags=["predictions"]
)
app.include_router(
    delivery_history.router,
    prefix="/api/v1/delivery-history",
    tags=["delivery_history"],
)
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
# Removed google_api_dashboard during compaction
app.include_router(driver.router, prefix="/api/v1/drivers", tags=["drivers"])
app.include_router(
    communications.router, prefix="/api/v1/communications", tags=["communications"]
)
app.include_router(websocket.router, prefix="/api/v1/websocket", tags=["websocket"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(
    financial_reports.router,
    prefix="/api/v1/financial-reports",
    tags=["financial_reports"],
)
app.include_router(banking.router, prefix="/api/v1/banking", tags=["banking"])
# Removed banking_monitor during compaction
app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])
# Removed webhooks during compaction
app.include_router(sms.router, prefix="/api/v1", tags=["sms"])
# Removed sms_webhooks during compaction
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])
app.include_router(migration.router, prefix="/api/v1", tags=["admin", "migration"])
# Removed sync_operations during compaction
# Removed feature_flags during compaction
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["api_keys"])
app.include_router(maps_proxy.router, prefix="/api/v1/maps", tags=["maps_proxy"])

# Test utilities removed during compaction
# import os
# if os.getenv("ENVIRONMENT") in ["test", "development"]:
#     from app.api.v1.test_utils import router as test_utils_router
#     app.include_router(test_utils_router, prefix="/api/v1/test", tags=["test"])


@app.get("/")
async def root():
    return {"message": "Lucky Gas Delivery Management System API", "status": "運行中"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "系統正常運行"}


@app.get("/api/health")
async def api_health_check():
    """Health check endpoint for API."""
    return {"status": "healthy", "message": "系統正常運行", "timestamp": time.time()}


@app.get("/api/v1/health")
async def api_v1_health_check():
    """Health check endpoint for API v1."""
    return {"status": "healthy", "message": "系統正常運行", "version": "1.0.0"}


# Prometheus metrics removed during compaction
# instrumentator = Instrumentator()
# instrumentator.instrument(app).expose(app)
