from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import time
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1 import auth, customers, orders, routes, routes_crud, predictions, websocket, delivery_history, products, google_api_dashboard
from app.api.v1.socketio_handler import sio, socket_app
from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.core.logging import setup_logging, get_logger
from app.middleware.logging import LoggingMiddleware, CorrelationIdMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limiting import RateLimitMiddleware
from app.core.db_metrics import DatabaseMetricsCollector
from app.core.env_validation import validate_environment
from app.services.websocket_service import websocket_manager

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
    
    # Start database metrics collector
    db_metrics_collector = DatabaseMetricsCollector(engine)
    import asyncio
    metrics_task = asyncio.create_task(db_metrics_collector.start())
    logger.info("Database metrics collector started")
    
    # Initialize WebSocket manager
    await websocket_manager.initialize()
    logger.info("WebSocket manager initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Lucky Gas backend service")
    
    # Close WebSocket connections
    await websocket_manager.close()
    logger.info("WebSocket connections closed")
    
    # Stop metrics collector
    db_metrics_collector.stop()
    metrics_task.cancel()
    
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
    openapi_url="/api/v1/openapi.json"
)

# Mount Socket.IO app
app.mount("/socket.io", socket_app)

# Configure CORS with enhanced settings
cors_origins = settings.get_all_cors_origins()

# Add environment-specific CORS origins
if settings.is_development():
    # Additional development origins
    cors_origins.extend([
        "http://localhost:*",
        "http://127.0.0.1:*"
    ])

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
        "Access-Control-Request-Method"
    ],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Total-Count"
    ],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiting middleware
rate_limit_config = settings.get_rate_limit()
app.add_middleware(
    RateLimitMiddleware,
    default_limit=rate_limit_config["calls"],
    window_seconds=rate_limit_config["period"]
)

# Add logging middleware (should be early in the chain)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

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
            "body": str(exc.body) if exc.body else None
        }
    )
    # Convert validation errors to serializable format
    errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": error.get("loc", []),
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", ""))
        }
        errors.append(serializable_error)
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "資料驗證失敗",
            "errors": errors
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(
        f"HTTP error: {exc.status_code}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "type": "http_error"
        }
    )

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
# Include both route routers - optimization and CRUD
app.include_router(routes_crud.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(routes.router, prefix="/api/v1/routes", tags=["route_optimization"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(delivery_history.router, prefix="/api/v1/delivery-history", tags=["delivery_history"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(google_api_dashboard.router, prefix="/api/v1/google-api", tags=["google_api_dashboard"])
app.include_router(websocket.router, prefix="/api/v1/websocket", tags=["websocket"])


@app.get("/")
async def root():
    return {"message": "Lucky Gas Delivery Management System API", "status": "運行中"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "系統正常運行"}


@app.get("/api/v1/health")
async def api_v1_health_check():
    """Health check endpoint for API v1."""
    return {"status": "healthy", "message": "系統正常運行", "version": "1.0.0"}

# Add Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)