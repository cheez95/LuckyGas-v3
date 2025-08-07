"""API v1 endpoints"""

from fastapi import APIRouter

from . import (
    analytics,
    auth,
    customers,
    health_simple,
    orders,
    predictions,
    routes,
    websocket,
    websocket_simple,
)

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(
    predictions.router, prefix="/predictions", tags=["predictions"]
)
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(websocket.router, prefix="/websocket", tags=["websocket"])
api_router.include_router(
    websocket_simple.router, prefix="/websocket - simple", tags=["websocket - simple"]
)
api_router.include_router(
    health_simple.router, prefix="/health - simple", tags=["health"]
)
