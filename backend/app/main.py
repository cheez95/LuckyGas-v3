from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import time
import aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1 import auth, customers, orders, routes, predictions, websocket, delivery_history, products
from app.core.config import settings
from app.core.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_db_and_tables()
    
    # Initialize FastAPI-Cache2
    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="luckygas-cache")
    
    yield
    
    # Shutdown
    await redis.close()


app = FastAPI(
    title="Lucky Gas Delivery Management System",
    description="幸福氣配送管理系統 API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS with all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_all_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

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