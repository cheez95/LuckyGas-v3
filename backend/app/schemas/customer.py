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
    customer_code: str
    short_name: str
    phone: Optional[str] = None
    invoice_title: Optional[str] = None
    address: str
    area: Optional[str] = None
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    cylinders_50kg: int = 0
    cylinders_20kg: int = 0
    cylinders_16kg: int = 0
    cylinders_10kg: int = 0


class CustomerCreate(CustomerBase):
    """Create customer model"""
    pass


class CustomerUpdate(BaseModel):
    """Update customer model"""
    short_name: Optional[str] = None
    phone: Optional[str] = None
    invoice_title: Optional[str] = None
    address: Optional[str] = None
    area: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    cylinders_50kg: Optional[int] = None
    cylinders_20kg: Optional[int] = None
    cylinders_16kg: Optional[int] = None
    cylinders_10kg: Optional[int] = None
    is_subscription: Optional[bool] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    """Customer response model"""
    id: int
    customer_code: str
    short_name: str
    phone: Optional[str] = None
    invoice_title: Optional[str] = None
    address: str
    area: Optional[str] = None
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    cylinders_50kg: Optional[int] = 0
    cylinders_20kg: Optional[int] = 0
    cylinders_16kg: Optional[int] = 0
    cylinders_10kg: Optional[int] = 0
    is_subscription: Optional[bool] = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        from_attributes = True


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