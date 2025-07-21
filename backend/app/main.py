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

from app.api.v1 import auth, customers, orders, routes, predictions, websocket, delivery_history, products, google_api_dashboard
from app.api.v1.socketio_handler import sio, socket_app
from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.core.logging import setup_logging, get_logger
from app.middleware.logging import LoggingMiddleware, CorrelationIdMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.core.db_metrics import DatabaseMetricsCollector
from app.core.env_validation import validate_environment

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
    
    yield
    
    # Shutdown
    logger.info("Shutting down Lucky Gas backend service")
    
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
    lifespan=lifespan
)

# Mount Socket.IO app
app.mount("/socket.io", socket_app)

# Configure CORS with restricted settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_all_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
            "body": exc.body
        }
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "資料驗證失敗",
            "errors": exc.errors(),
            "body": exc.body
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
app.include_router(routes.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(delivery_history.router, prefix="/api/v1/delivery-history", tags=["delivery_history"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(google_api_dashboard.router, prefix="/api/v1/google-api", tags=["google_api_dashboard"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/")
async def root():
    return {"message": "Lucky Gas Delivery Management System API", "status": "運行中"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "系統正常運行"}

# Add Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)