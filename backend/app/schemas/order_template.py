from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class OrderTemplateProductItem(BaseModel):
    """Product item in order template"""
    gas_product_id: int
    quantity: int = Field(gt=0)
    unit_price: Optional[float] = None
    discount_percentage: Optional[float] = Field(ge=0, le=100, default=0)
    is_exchange: bool = False
    empty_received: Optional[int] = 0


class OrderTemplateBase(BaseModel):
    """Base schema for order template"""
    template_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    products: List[OrderTemplateProductItem]
    delivery_notes: Optional[str] = None
    priority: str = Field(default="normal", pattern="^(normal|urgent|scheduled)$")
    payment_method: str = Field(default="cash", pattern="^(cash|transfer|credit)$")
    
    # Recurring options
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = Field(None, pattern="^(daily|weekly|monthly|custom)$")
    recurrence_interval: Optional[int] = Field(None, ge=1, le=365)
    recurrence_days: Optional[List[int]] = None  # For weekly pattern: 1-7 (Mon-Sun)
    
    @field_validator('products')
    @classmethod
    def validate_products_not_empty(cls, v):
        if not v:
            raise ValueError('Template must have at least one product')
        return v
    
    @model_validator(mode='after')
    def validate_recurrence_pattern(self):
        if self.is_recurring and not self.recurrence_pattern:
            raise ValueError('Recurrence pattern is required for recurring templates')
        if not self.is_recurring and self.recurrence_pattern:
            raise ValueError('Cannot set recurrence pattern for non-recurring templates')
        return self


class OrderTemplateCreate(OrderTemplateBase):
    """Schema for creating order template"""
    customer_id: int
    template_code: Optional[str] = None


class OrderTemplateUpdate(BaseModel):
    """Schema for updating order template"""
    template_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    products: Optional[List[OrderTemplateProductItem]] = None
    delivery_notes: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(normal|urgent|scheduled)$")
    payment_method: Optional[str] = Field(None, pattern="^(cash|transfer|credit)$")
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = Field(None, pattern="^(daily|weekly|monthly|custom)$")
    recurrence_interval: Optional[int] = Field(None, ge=1, le=365)
    recurrence_days: Optional[List[int]] = None
    is_active: Optional[bool] = None


class OrderTemplateInDB(OrderTemplateBase):
    """Schema for order template in database"""
    id: int
    template_code: str
    customer_id: int
    times_used: int = 0
    last_used_at: Optional[datetime] = None
    next_scheduled_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    model_config = {"from_attributes": True}


class OrderTemplate(OrderTemplateInDB):
    """Schema for order template response"""
    customer_name: Optional[str] = None
    customer_code: Optional[str] = None
    product_details: Optional[List[Dict[str, Any]]] = None  # Enriched product info


class OrderTemplateList(BaseModel):
    """Schema for order template list response"""
    templates: List[OrderTemplate]
    total: int
    skip: int
    limit: int


class CreateOrderFromTemplate(BaseModel):
    """Schema for creating order from template"""
    template_id: int
    scheduled_date: Optional[datetime] = None
    delivery_notes: Optional[str] = None
    override_products: Optional[List[OrderTemplateProductItem]] = None
    override_priority: Optional[str] = None
    override_payment_method: Optional[str] = None