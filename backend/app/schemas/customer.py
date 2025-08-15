"""
Simplified customer schemas
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date
from enum import Enum


class CustomerType(str, Enum):
    RESIDENTIAL = "residential"
    RESTAURANT = "restaurant"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"


class CustomerBase(BaseModel):
    """Base customer model"""
    code: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    address: str
    area: Optional[str]
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    pricing_tier: str = "standard"
    credit_limit: float = 0.0
    preferred_delivery_time: Optional[str]
    notes: Optional[str]


class CustomerCreate(CustomerBase):
    """Create customer model"""
    pass


class CustomerUpdate(BaseModel):
    """Update customer model"""
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    area: Optional[str]
    customer_type: Optional[CustomerType]
    pricing_tier: Optional[str]
    credit_limit: Optional[float]
    current_balance: Optional[float]
    preferred_delivery_time: Optional[str]
    notes: Optional[str]
    is_active: Optional[bool]


class CustomerResponse(CustomerBase):
    """Customer response model"""
    id: int
    current_balance: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class DeliveryResponse(BaseModel):
    """Delivery response for customer history"""
    id: int
    order_id: int
    delivery_date: date
    status: str
    driver_id: Optional[int]
    scheduled_time: Optional[str]
    actual_delivery_time: Optional[datetime]
    delivery_notes: Optional[str]
    
    class Config:
        orm_mode = True


class CustomerDeliveryHistory(BaseModel):
    """Customer delivery history response"""
    customer: CustomerResponse
    deliveries: List[DeliveryResponse]
    total_count: int
    summary: dict