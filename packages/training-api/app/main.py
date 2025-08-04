from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from prometheus_client import make_asgi_app, Counter, Histogram
import socketio
import uvicorn

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_router
from app.core.logging import setup_logging
from app.core.exceptions import TrainingException
from app.core.telemetry import setup_telemetry

# Setup logging
logger = setup_logging()

# Metrics
REQUEST_COUNT = Counter(
    "training_requests_total", 
    "Total request count", 
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "training_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"]
)

# Socket.IO setup
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Lucky Gas Training API...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Setup telemetry
    if settings.ENABLE_TELEMETRY:
        setup_telemetry()
    
    logger.info("Lucky Gas Training API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Lucky Gas Training API...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Lucky Gas Training API",
    description="Training and learning management system for Lucky Gas delivery personnel",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and track metrics."""
    start_time = time.time()
    
    # Get correlation ID from header or generate new one
    correlation_id = request.headers.get("X-Correlation-ID", f"req_{int(time.time()*1000)}")
    request.state.correlation_id = correlation_id
    
    # Log request
    logger.info(
        f"Request started",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None
        }
    )
    
    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Track metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "correlation_id": correlation_id,
                "status_code": response.status_code,
                "duration": f"{duration:.3f}s"
            }
        )
        
        # Add correlation ID to response header
        response.headers["X-Correlation-ID"] = correlation_id
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "duration": f"{duration:.3f}s"
            }
        )
        raise


@app.exception_handler(TrainingException)
async def training_exception_handler(request: Request, exc: TrainingException):
    """Handle custom training exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "correlation_id": getattr(request.state, "correlation_id", None)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={"correlation_id": correlation_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id
        }
    )


# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Lucky Gas Training API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "training-api",
        "timestamp": time.time()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "database": db_status
            }
        )
    
    return {
        "status": "ready",
        "database": db_status
    }


# Include API router
app.include_router(api_router, prefix="/api/v1")

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)


# Socket.IO events
@sio.event
async def connect(sid, environ):
    """Handle socket connection."""
    logger.info(f"Socket connected: {sid}")
    await sio.emit("connected", {"message": "Welcome to Lucky Gas Training"}, to=sid)


@sio.event
async def disconnect(sid):
    """Handle socket disconnection."""
    logger.info(f"Socket disconnected: {sid}")


@sio.event
async def join_course(sid, data):
    """Join a course room for real-time updates."""
    course_id = data.get("course_id")
    if course_id:
        sio.enter_room(sid, f"course_{course_id}")
        await sio.emit(
            "joined_course",
            {"course_id": course_id, "message": "Joined course room"},
            to=sid
        )


@sio.event
async def leave_course(sid, data):
    """Leave a course room."""
    course_id = data.get("course_id")
    if course_id:
        sio.leave_room(sid, f"course_{course_id}")
        await sio.emit(
            "left_course",
            {"course_id": course_id, "message": "Left course room"},
            to=sid
        )


@sio.event
async def progress_update(sid, data):
    """Handle progress updates from clients."""
    course_id = data.get("course_id")
    module_id = data.get("module_id")
    progress = data.get("progress")
    
    # Broadcast to others in the course room
    await sio.emit(
        "peer_progress",
        {
            "user_id": data.get("user_id"),
            "module_id": module_id,
            "progress": progress
        },
        room=f"course_{course_id}",
        skip_sid=sid
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:socket_app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_config=None  # We handle logging ourselves
    )