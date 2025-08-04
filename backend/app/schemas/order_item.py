from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.gas_product import GasProduct


class OrderItemBase(BaseModel):
    gas_product_id: int
    quantity: int
    unit_price: float
    discount_percentage: float = 0
    discount_amount: float = 0
    is_exchange: bool = True
    empty_received: int = 0
    is_flow_delivery: bool = False
    meter_reading_start: Optional[float] = None
    meter_reading_end: Optional[float] = None
    actual_quantity: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("quantity")
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("數量必須大於0")
        return v

    @field_validator("unit_price")
    def validate_unit_price(cls, v):
        if v < 0:
            raise ValueError("單價不能為負數")
        return v

    @field_validator("discount_percentage")
    def validate_discount_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError("折扣百分比必須在0-100之間")
        return v


class OrderItemCreate(OrderItemBase):
    """Schema for creating order item"""

    pass


class OrderItemUpdate(BaseModel):
    """Schema for updating order item"""

    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    discount_amount: Optional[float] = None
    is_exchange: Optional[bool] = None
    empty_received: Optional[int] = None
    meter_reading_start: Optional[float] = None
    meter_reading_end: Optional[float] = None
    actual_quantity: Optional[float] = None
    notes: Optional[str] = None


class OrderItem(OrderItemBase):
    """Schema for order item response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    subtotal: float
    final_amount: float
    gas_product: Optional[GasProduct] = None

    @property
    def display_name(self) -> str:
        """Get display name from product"""
        if self.gas_product:
            return self.gas_product.display_name
        return f"產品 #{self.gas_product_id}"


class OrderItemSummary(BaseModel):
    """Summary view for order item listing"""

    id: int
    gas_product_id: int
    product_name: str
    quantity: int
    unit_price: float
    final_amount: float
    is_flow_delivery: bool
