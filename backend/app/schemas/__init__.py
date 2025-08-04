from app.schemas.user import User, UserCreate, UserUpdate, Token, TokenData
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate
from app.schemas.order import Order, OrderCreate, OrderUpdate
from app.schemas.route import (
    Route,
    RouteCreate,
    RouteUpdate,
    RouteWithDetails,
    RouteStop,
    RouteStopCreate,
    RouteStopUpdate,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
)
from app.schemas.delivery_history import (
    DeliveryHistory,
    DeliveryHistoryCreate,
    DeliveryHistoryUpdate,
    DeliveryHistoryList,
    DeliveryHistoryStats,
)

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "Token",
    "TokenData",
    "Customer",
    "CustomerCreate",
    "CustomerUpdate",
    "Order",
    "OrderCreate",
    "OrderUpdate",
    "Route",
    "RouteCreate",
    "RouteUpdate",
    "RouteWithDetails",
    "RouteStop",
    "RouteStopCreate",
    "RouteStopUpdate",
    "RouteOptimizationRequest",
    "RouteOptimizationResponse",
    "DeliveryHistory",
    "DeliveryHistoryCreate",
    "DeliveryHistoryUpdate",
    "DeliveryHistoryList",
    "DeliveryHistoryStats",
]
