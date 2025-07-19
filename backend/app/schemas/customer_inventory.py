from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.gas_product import GasProduct


class CustomerInventoryBase(BaseModel):
    """Base schema for customer inventory"""
    quantity_owned: int = 0
    quantity_rented: int = 0
    quantity_total: int = 0
    flow_meter_count: int = 0
    last_meter_reading: float = 0
    deposit_paid: float = 0
    is_active: bool = True


class CustomerInventoryCreate(CustomerInventoryBase):
    """Schema for creating customer inventory"""
    customer_id: int
    gas_product_id: int


class CustomerInventoryUpdate(BaseModel):
    """Schema for updating customer inventory"""
    quantity_owned: Optional[int] = None
    quantity_rented: Optional[int] = None
    flow_meter_count: Optional[int] = None
    last_meter_reading: Optional[float] = None
    deposit_paid: Optional[float] = None
    is_active: Optional[bool] = None


class CustomerInventory(CustomerInventoryBase):
    """Schema for customer inventory response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    customer_id: int
    gas_product_id: int
    last_updated: datetime
    needs_refill: bool
    gas_product: GasProduct


class CustomerInventoryList(BaseModel):
    """Schema for paginated customer inventory list"""
    items: List[CustomerInventory]
    total: int
    skip: int
    limit: int