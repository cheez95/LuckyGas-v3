from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime


class CustomerBase(BaseModel):
    customer_code: str
    invoice_title: Optional[str] = None
    short_name: str
    address: str
    
    # Cylinder inventory
    cylinders_50kg: int = 0
    cylinders_20kg: int = 0
    cylinders_16kg: int = 0
    cylinders_10kg: int = 0
    cylinders_4kg: int = 0
    
    # Delivery preferences
    delivery_time_start: Optional[str] = None
    delivery_time_end: Optional[str] = None
    area: Optional[str] = None
    
    # Consumption data
    avg_daily_usage: Optional[float] = None
    max_cycle_days: Optional[int] = None
    can_delay_days: Optional[int] = None
    
    # Pricing
    pricing_method: Optional[str] = None
    payment_method: Optional[str] = None
    
    # Status
    is_subscription: bool = False
    is_terminated: bool = False
    needs_same_day_delivery: bool = False
    
    # Customer type
    customer_type: Optional[str] = None
    
    @field_validator('delivery_time_start', 'delivery_time_end')
    def validate_time_format(cls, v):
        if v is not None and not (len(v) == 5 and v[2] == ':'):
            raise ValueError('時間格式必須為 HH:MM')
        return v


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    invoice_title: Optional[str] = None
    short_name: Optional[str] = None
    address: Optional[str] = None
    
    # Cylinder inventory
    cylinders_50kg: Optional[int] = None
    cylinders_20kg: Optional[int] = None
    cylinders_16kg: Optional[int] = None
    cylinders_10kg: Optional[int] = None
    cylinders_4kg: Optional[int] = None
    
    # Delivery preferences
    delivery_time_start: Optional[str] = None
    delivery_time_end: Optional[str] = None
    area: Optional[str] = None
    
    # Consumption data
    avg_daily_usage: Optional[float] = None
    max_cycle_days: Optional[int] = None
    can_delay_days: Optional[int] = None
    
    # Status
    is_subscription: Optional[bool] = None
    is_terminated: Optional[bool] = None
    needs_same_day_delivery: Optional[bool] = None


class Customer(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class CustomerList(BaseModel):
    """Schema for paginated customer list"""
    items: List[Customer]
    total: int
    skip: int
    limit: int