
from pydantic import BaseModel, ConfigDict
from typing import Optional


class DeliveryHistoryItemBase(BaseModel):
    gas_product_id: int
    quantity: int
    unit_price: float
    is_flow_delivery: bool = False
    flow_quantity: Optional[float] = None
    legacy_product_code: Optional[str] = None


class DeliveryHistoryItemCreate(DeliveryHistoryItemBase):
    pass


class DeliveryHistoryItemUpdate(BaseModel):
    gas_product_id: Optional[int] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    is_flow_delivery: Optional[bool] = None
    flow_quantity: Optional[float] = None


class DeliveryHistoryItem(DeliveryHistoryItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delivery_history_id: int
    subtotal: float

    # Computed properties
    is_cylinder_product: bool


class DeliveryHistoryItemInDB(DeliveryHistoryItem):
    """Schema with full database fields"""
