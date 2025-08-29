
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.models.gas_product import DeliveryMethod, ProductAttribute


class GasProductBase(BaseModel):
    """Base schema for gas products"""

    delivery_method: DeliveryMethod
    size_kg: int
    attribute: ProductAttribute
    sku: Optional[str] = None
    name_zh: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    unit_price: float
    deposit_amount: float = 0
    is_active: bool = True
    is_available: bool = True
    track_inventory: bool = True
    low_stock_threshold: int = 10


class GasProductCreate(GasProductBase):
    """Schema for creating gas products"""


class GasProductUpdate(BaseModel):
    """Schema for updating gas products"""

    name_zh: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[float] = None
    deposit_amount: Optional[float] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    track_inventory: Optional[bool] = None
    low_stock_threshold: Optional[int] = None


class GasProduct(GasProductBase):
    """Schema for gas product response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class GasProductList(BaseModel):
    """Schema for paginated gas product list"""

    items: List[GasProduct]
    total: int
    skip: int
    limit: int
