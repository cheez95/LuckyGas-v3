from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate
from app.schemas.delivery_history import (
    DeliveryHistory,
    DeliveryHistoryCreate,
    DeliveryHistoryList,
    DeliveryHistoryStats,
    DeliveryHistoryUpdate,
)
from app.schemas.order import Order, OrderCreate, OrderUpdate
from app.schemas.route import (
    Route,
    RouteCreate,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    RouteStop,
    RouteStopCreate,
    RouteStopUpdate,
    RouteUpdate,
    RouteWithDetails,
)
from app.schemas.user import Token, TokenData, User, UserCreate, UserUpdate

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
