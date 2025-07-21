from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, field_validator, Field, model_validator
from datetime import datetime, date
import re

from app.models.order import OrderStatus, PaymentStatus
from app.schemas.order_item import OrderItem, OrderItemCreate, OrderItemSummary
from app.core.validators import TaiwanValidators, address_validator, phone_validator


class OrderBase(BaseModel):
    customer_id: int = Field(
        ...,
        alias="客戶編號",
        description="Customer ID",
        gt=0
    )
    scheduled_date: datetime = Field(
        ...,
        alias="預定配送日期",
        description="Scheduled delivery date"
    )
    delivery_time_start: Optional[str] = Field(
        None,
        alias="配送開始時間",
        description="Delivery start time (HH:MM)",
        pattern=r'^\d{2}:\d{2}$'
    )
    delivery_time_end: Optional[str] = Field(
        None,
        alias="配送結束時間",
        description="Delivery end time (HH:MM)",
        pattern=r'^\d{2}:\d{2}$'
    )
    
    # Cylinder quantities
    qty_50kg: int = Field(
        0,
        alias="50公斤數量",
        description="Quantity of 50kg cylinders",
        ge=0,
        le=100
    )
    qty_20kg: int = Field(
        0,
        alias="20公斤數量",
        description="Quantity of 20kg cylinders",
        ge=0,
        le=100
    )
    qty_16kg: int = Field(
        0,
        alias="16公斤數量",
        description="Quantity of 16kg cylinders",
        ge=0,
        le=100
    )
    qty_10kg: int = Field(
        0,
        alias="10公斤數量",
        description="Quantity of 10kg cylinders",
        ge=0,
        le=100
    )
    qty_4kg: int = Field(
        0,
        alias="4公斤數量",
        description="Quantity of 4kg cylinders",
        ge=0,
        le=100
    )
    
    # Delivery info
    delivery_address: Optional[str] = Field(
        None,
        alias="配送地址",
        description="Delivery address (overrides customer address)",
        max_length=200
    )
    delivery_notes: Optional[str] = Field(
        None,
        alias="配送備註",
        description="Special delivery instructions",
        max_length=500
    )
    is_urgent: bool = Field(
        False,
        alias="緊急訂單",
        description="Whether this is an urgent order"
    )
    
    # Payment
    payment_method: Optional[str] = Field(
        None,
        alias="付款方式",
        description="Payment method",
        max_length=50
    )
    
    @field_validator('delivery_time_start', 'delivery_time_end')
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^\d{2}:\d{2}$', v):
                raise ValueError('時間格式必須為 HH:MM')
            hour, minute = map(int, v.split(':'))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError('無效的時間值')
        return v
    
    @field_validator('delivery_address')
    def validate_delivery_address(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Basic validation - just check it's not empty after stripping
            v = v.strip()
            if len(v) < 10:
                raise ValueError('配送地址太短')
        return v
    
    @field_validator('scheduled_date')
    def validate_scheduled_date(cls, v: datetime) -> datetime:
        # Cannot schedule delivery in the past
        if v.date() < date.today():
            raise ValueError('配送日期不能是過去的日期')
        # Cannot schedule more than 30 days in advance
        if (v.date() - date.today()).days > 30:
            raise ValueError('配送日期不能超過30天後')
        return v
    
    @model_validator(mode='after')
    def validate_order(self):
        # At least one cylinder must be ordered
        total_qty = (
            self.qty_50kg + self.qty_20kg + 
            self.qty_16kg + self.qty_10kg + self.qty_4kg
        )
        if total_qty == 0:
            raise ValueError('訂單必須至少包含一個鋼瓶')
        
        # Validate delivery time window
        if self.delivery_time_start and self.delivery_time_end:
            start_hour = int(self.delivery_time_start.split(':')[0])
            end_hour = int(self.delivery_time_end.split(':')[0])
            if start_hour >= end_hour:
                raise ValueError('配送開始時間必須早於結束時間')
        
        return self
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "customer_id": 1,
                "scheduled_date": "2024-02-01T00:00:00",
                "delivery_time_start": "09:00",
                "delivery_time_end": "17:00",
                "qty_20kg": 2,
                "qty_16kg": 1,
                "delivery_address": "台北市中正區重慶南路一段122號",
                "delivery_notes": "請按門鈴，放在門口即可",
                "payment_method": "現金"
            }
        }
    )


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
    id: int = Field(..., alias="訂單編號", description="Order ID")
    order_number: str = Field(..., alias="訂單號碼", description="Order number")
    status: OrderStatus = Field(..., alias="訂單狀態", description="Order status")
    payment_status: PaymentStatus = Field(..., alias="付款狀態", description="Payment status")
    
    # Pricing
    total_amount: float = Field(..., alias="總金額", description="Total amount before discount", ge=0)
    discount_amount: float = Field(0, alias="折扣金額", description="Discount amount", ge=0)
    final_amount: float = Field(..., alias="應付金額", description="Final amount after discount", ge=0)
    
    # Timestamps
    created_at: datetime = Field(..., alias="建立時間", description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, alias="更新時間", description="Last update timestamp")
    delivered_at: Optional[datetime] = Field(None, alias="配送時間", description="Delivery completion timestamp")
    
    # Additional fields
    driver_id: Optional[int] = Field(None, alias="司機編號", description="Assigned driver ID")
    route_id: Optional[int] = Field(None, alias="路線編號", description="Assigned route ID")
    
    @field_validator('final_amount')
    def validate_final_amount(cls, v: float, values) -> float:
        # Ensure final amount is reasonable
        if v < 0:
            raise ValueError('應付金額不能為負數')
        return v
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
            OrderStatus: lambda v: v.value,
            PaymentStatus: lambda v: v.value
        }
    )


# V2 Schemas for flexible product system
class OrderBaseV2(BaseModel):
    """Base order schema using flexible products"""
    customer_id: int = Field(..., alias="客戶編號", gt=0)
    scheduled_date: datetime = Field(..., alias="預定配送日期")
    delivery_time_start: Optional[str] = Field(None, alias="配送開始時間", pattern=r'^\d{2}:\d{2}$')
    delivery_time_end: Optional[str] = Field(None, alias="配送結束時間", pattern=r'^\d{2}:\d{2}$')
    
    # Delivery info
    delivery_address: Optional[str] = Field(None, alias="配送地址", max_length=200)
    delivery_notes: Optional[str] = Field(None, alias="配送備註", max_length=500)
    is_urgent: bool = Field(False, alias="緊急訂單")
    
    # Payment
    payment_method: Optional[str] = Field(None, alias="付款方式", max_length=50)
    
    # Apply same validators
    _validate_time = field_validator('delivery_time_start', 'delivery_time_end')(OrderBase.validate_time_format)
    _validate_address = field_validator('delivery_address')(OrderBase.validate_delivery_address)
    _validate_date = field_validator('scheduled_date')(OrderBase.validate_scheduled_date)
    
    model_config = ConfigDict(populate_by_name=True)


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
    id: int = Field(..., alias="訂單編號")
    order_number: str = Field(..., alias="訂單號碼")
    status: OrderStatus = Field(..., alias="訂單狀態")
    payment_status: PaymentStatus = Field(..., alias="付款狀態")
    
    # Pricing
    total_amount: float = Field(..., alias="總金額", ge=0)
    discount_amount: float = Field(0, alias="折扣金額", ge=0)
    final_amount: float = Field(..., alias="應付金額", ge=0)
    
    # Timestamps
    created_at: datetime = Field(..., alias="建立時間")
    updated_at: Optional[datetime] = Field(None, alias="更新時間")
    delivered_at: Optional[datetime] = Field(None, alias="配送時間")
    
    # Order items
    order_items: List[OrderItem] = Field(default_factory=list, alias="訂單項目")
    
    # Customer info (optional)
    customer_name: Optional[str] = Field(None, alias="客戶名稱", max_length=100)
    customer_phone: Optional[str] = Field(None, alias="客戶電話", max_length=15)
    
    # Apply validators
    _validate_phone = field_validator('customer_phone')(lambda cls, v: TaiwanValidators.validate_phone_number(v) if v else v)
    _validate_amount = field_validator('final_amount')(Order.validate_final_amount)
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
            OrderStatus: lambda v: v.value,
            PaymentStatus: lambda v: v.value
        }
    )