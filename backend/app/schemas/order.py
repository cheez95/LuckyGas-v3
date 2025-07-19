from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.models.order import OrderStatus, PaymentStatus
from app.schemas.order_item import OrderItem, OrderItemCreate, OrderItemSummary


class OrderBase(BaseModel):
    customer_id: int
    scheduled_date: datetime
    delivery_time_start: Optional[str] = None
    delivery_time_end: Optional[str] = None
    
    # Cylinder quantities
    qty_50kg: int = 0
    qty_20kg: int = 0
    qty_16kg: int = 0
    qty_10kg: int = 0
    qty_4kg: int = 0
    
    # Delivery info
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_urgent: bool = False
    
    # Payment
    payment_method: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    scheduled_date: Optional[datetime] = None
    delivery_time_start: Optional[str] = None
    delivery_time_end: Optional[str] = None
    
    # Quantities
    qty_50kg: Optional[int] = None
    qty_20kg: Optional[int] = None
    qty_16kg: Optional[int] = None
    qty_10kg: Optional[int] = None
    qty_4kg: Optional[int] = None
    
    # Status
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    
    # Delivery
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_urgent: Optional[bool] = None
    
    # Assignment
    route_id: Optional[int] = None
    driver_id: Optional[int] = None


class Order(OrderBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    
    # Pricing
    total_amount: float
    discount_amount: float
    final_amount: float
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


# V2 Schemas for flexible product system
class OrderBaseV2(BaseModel):
    """Base order schema using flexible products"""
    customer_id: int
    scheduled_date: datetime
    delivery_time_start: Optional[str] = None
    delivery_time_end: Optional[str] = None
    
    # Delivery info
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_urgent: bool = False
    
    # Payment
    payment_method: Optional[str] = None


class OrderCreateV2(OrderBaseV2):
    """Create order with flexible products"""
    order_items: List[OrderItemCreate]


class OrderUpdateV2(BaseModel):
    """Update order with flexible products"""
    scheduled_date: Optional[datetime] = None
    delivery_time_start: Optional[str] = None
    delivery_time_end: Optional[str] = None
    
    # Status
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    
    # Delivery
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_urgent: Optional[bool] = None
    
    # Assignment
    route_id: Optional[int] = None
    driver_id: Optional[int] = None


class OrderV2(OrderBaseV2):
    """Order response with flexible products"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    
    # Pricing
    total_amount: float
    discount_amount: float
    final_amount: float
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Order items
    order_items: List[OrderItem] = []
    
    # Customer info (optional)
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None