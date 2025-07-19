from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.gas_product import DeliveryMethod, ProductAttribute


class GasProductBase(BaseModel):
    delivery_method: DeliveryMethod
    size_kg: int
    attribute: ProductAttribute
    name_zh: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    unit_price: float
    deposit_amount: float = 0
    is_active: bool = True
    is_available: bool = True
    track_inventory: bool = True
    low_stock_threshold: int = 10
    
    @field_validator('size_kg')
    def validate_size(cls, v):
        valid_sizes = [4, 10, 16, 20, 50]
        if v not in valid_sizes:
            raise ValueError(f'Size must be one of {valid_sizes}')
        return v
    
    @field_validator('unit_price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Unit price must be non-negative')
        return v


class GasProductCreate(GasProductBase):
    """Schema for creating a new gas product"""
    pass


class GasProductUpdate(BaseModel):
    """Schema for updating a gas product"""
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
    sku: str
    display_name: str


class GasProductList(BaseModel):
    """Schema for paginated gas product list"""
    items: List[GasProduct]
    total: int
    skip: int
    limit: int


class GasProductSummary(BaseModel):
    """Summary view of gas product for dropdowns/selections"""
    id: int
    sku: str
    display_name: str
    unit_price: float
    is_available: bool