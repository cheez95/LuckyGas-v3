from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime

from app.core.validators import (
    TaiwanValidators,
    phone_validator,
    tax_id_validator,
    address_validator,
    TaiwanPhoneField,
    TaiwanTaxIdField,
    TaiwanAddressField,
)


class CustomerBase(BaseModel):
    customer_code: str = Field(
        ...,
        alias="客戶代碼",
        description="Unique customer code",
        min_length=1,
        max_length=50,
    )
    invoice_title: Optional[str] = Field(
        None,
        alias="發票抬頭",
        description="Invoice title for the customer",
        max_length=100,
    )
    short_name: str = Field(
        ...,
        alias="簡稱",
        description="Customer short name",
        min_length=1,
        max_length=50,
    )
    address: str = Field(
        ..., alias="地址", description="Delivery address", min_length=10, max_length=200
    )

    # Contact Information
    phone: Optional[str] = Field(
        None,
        alias="電話",
        description="Contact phone number",
        min_length=9,
        max_length=15,
    )
    tax_id: Optional[str] = Field(
        None, alias="統一編號", description="Company tax ID", min_length=8, max_length=8
    )

    # Cylinder inventory
    cylinders_50kg: int = Field(
        0, alias="50公斤鋼瓶數", description="Number of 50kg cylinders", ge=0
    )
    cylinders_20kg: int = Field(
        0, alias="20公斤鋼瓶數", description="Number of 20kg cylinders", ge=0
    )
    cylinders_16kg: int = Field(
        0, alias="16公斤鋼瓶數", description="Number of 16kg cylinders", ge=0
    )
    cylinders_10kg: int = Field(
        0, alias="10公斤鋼瓶數", description="Number of 10kg cylinders", ge=0
    )
    cylinders_4kg: int = Field(
        0, alias="4公斤鋼瓶數", description="Number of 4kg cylinders", ge=0
    )

    # Delivery preferences
    delivery_time_start: Optional[str] = Field(
        None,
        alias="配送開始時間",
        description="Preferred delivery start time (HH:MM)",
        pattern=r"^\d{2}:\d{2}$",
    )
    delivery_time_end: Optional[str] = Field(
        None,
        alias="配送結束時間",
        description="Preferred delivery end time (HH:MM)",
        pattern=r"^\d{2}:\d{2}$",
    )
    area: Optional[str] = Field(
        None, alias="區域", description="Delivery area", max_length=50
    )

    # Consumption data
    avg_daily_usage: Optional[float] = Field(
        None, alias="平均日用量", description="Average daily gas usage (kg)", ge=0
    )
    max_cycle_days: Optional[int] = Field(
        None,
        alias="最大週期天數",
        description="Maximum days between deliveries",
        ge=1,
        le=365,
    )
    can_delay_days: Optional[int] = Field(
        None,
        alias="可延遲天數",
        description="Number of days delivery can be delayed",
        ge=0,
        le=30,
    )

    # Pricing
    pricing_method: Optional[str] = Field(
        None, alias="計價方式", description="Pricing method", max_length=50
    )
    payment_method: Optional[str] = Field(
        None, alias="付款方式", description="Payment method", max_length=50
    )

    # Status
    is_subscription: bool = Field(
        False, alias="訂閱制", description="Whether customer has subscription"
    )
    is_terminated: bool = Field(
        False, alias="已終止", description="Whether customer is terminated"
    )
    needs_same_day_delivery: bool = Field(
        False, alias="當日配送", description="Whether customer needs same-day delivery"
    )

    # Customer type
    customer_type: Optional[str] = Field(
        None,
        alias="客戶類型",
        description="Customer type (residential/commercial)",
        max_length=50,
    )

    # Location data
    latitude: Optional[float] = Field(
        None, alias="緯度", description="Latitude coordinate", ge=-90, le=90
    )
    longitude: Optional[float] = Field(
        None, alias="經度", description="Longitude coordinate", ge=-180, le=180
    )

    @field_validator("delivery_time_start", "delivery_time_end")
    def validate_time_format(cls, v):
        if v is not None:
            import re

            if not re.match(r"^\d{2}:\d{2}$", v):
                raise ValueError("時間格式必須為 HH:MM")
            hour, minute = map(int, v.split(":"))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("無效的時間值")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            return TaiwanValidators.validate_phone_number(v)
        return v

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            return TaiwanValidators.validate_tax_id(v)
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v and isinstance(v, str):
            return TaiwanValidators.validate_address(v)
        return v

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both field names and aliases
        json_schema_extra={
            "example": {
                "customer_code": "C001",
                "invoice_title": "幸福瓦斯行",
                "short_name": "幸福瓦斯",
                "address": "台北市中正區重慶南路一段122號",
                "phone": "0912-345-678",
                "tax_id": "12345678",
                "cylinders_20kg": 10,
                "cylinders_16kg": 5,
                "delivery_time_start": "09:00",
                "delivery_time_end": "17:00",
                "area": "中正區",
                "customer_type": "商業",
            }
        },
    )


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    invoice_title: Optional[str] = Field(None, alias="發票抬頭", max_length=100)
    short_name: Optional[str] = Field(None, alias="簡稱", max_length=50)
    address: Optional[str] = Field(None, alias="地址", max_length=200)
    phone: Optional[str] = Field(None, alias="電話", max_length=15)
    tax_id: Optional[str] = Field(None, alias="統一編號", max_length=8)

    # Cylinder inventory
    cylinders_50kg: Optional[int] = Field(None, alias="50公斤鋼瓶數", ge=0)
    cylinders_20kg: Optional[int] = Field(None, alias="20公斤鋼瓶數", ge=0)
    cylinders_16kg: Optional[int] = Field(None, alias="16公斤鋼瓶數", ge=0)
    cylinders_10kg: Optional[int] = Field(None, alias="10公斤鋼瓶數", ge=0)
    cylinders_4kg: Optional[int] = Field(None, alias="4公斤鋼瓶數", ge=0)

    # Delivery preferences
    delivery_time_start: Optional[str] = Field(
        None, alias="配送開始時間", pattern=r"^\d{2}:\d{2}$"
    )
    delivery_time_end: Optional[str] = Field(
        None, alias="配送結束時間", pattern=r"^\d{2}:\d{2}$"
    )
    area: Optional[str] = Field(None, alias="區域", max_length=50)

    # Consumption data
    avg_daily_usage: Optional[float] = Field(None, alias="平均日用量", ge=0)
    max_cycle_days: Optional[int] = Field(None, alias="最大週期天數", ge=1, le=365)
    can_delay_days: Optional[int] = Field(None, alias="可延遲天數", ge=0, le=30)

    # Status
    is_subscription: Optional[bool] = Field(None, alias="訂閱制")
    is_terminated: Optional[bool] = Field(None, alias="已終止")
    needs_same_day_delivery: Optional[bool] = Field(None, alias="當日配送")

    # Location
    latitude: Optional[float] = Field(None, alias="緯度", ge=-90, le=90)
    longitude: Optional[float] = Field(None, alias="經度", ge=-180, le=180)

    # Apply validators
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            return TaiwanValidators.validate_phone_number(v)
        return v

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            return TaiwanValidators.validate_tax_id(v)
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v and isinstance(v, str):
            return TaiwanValidators.validate_address(v)
        return v

    @field_validator("delivery_time_start", "delivery_time_end")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not re.match(r"^\d{2}:\d{2}$", v):
                raise ValueError("時間格式必須為 HH:MM")
            hour, minute = map(int, v.split(":"))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("無效的時間值")
        return v

    model_config = ConfigDict(populate_by_name=True)


class Customer(CustomerBase):
    id: int = Field(..., alias="編號", description="Customer ID")
    created_at: datetime = Field(
        ..., alias="建立時間", description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        None, alias="更新時間", description="Last update timestamp"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")},
    )


class CustomerList(BaseModel):
    """Schema for paginated customer list"""

    items: List[Customer]
    total: int
    skip: int
    limit: int
