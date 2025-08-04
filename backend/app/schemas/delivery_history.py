from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.delivery_history_item import DeliveryHistoryItem


class DeliveryHistoryBase(BaseModel):
    """Base schema for delivery history"""

    transaction_date: date
    transaction_time: Optional[str] = None
    salesperson: Optional[str] = None
    customer_code: str

    # Cylinder quantities
    qty_50kg: int = 0
    qty_ying20: int = 0
    qty_ying16: int = 0
    qty_20kg: int = 0
    qty_16kg: int = 0
    qty_10kg: int = 0
    qty_4kg: int = 0
    qty_haoyun16: int = 0
    qty_pingantong10: int = 0
    qty_xingfuwan4: int = 0
    qty_haoyun20: int = 0

    # Flow quantities
    flow_50kg: float = 0
    flow_20kg: float = 0
    flow_16kg: float = 0
    flow_haoyun20kg: float = 0
    flow_haoyun16kg: float = 0


class DeliveryHistoryCreate(DeliveryHistoryBase):
    """Schema for creating delivery history record"""

    pass


class DeliveryHistoryUpdate(BaseModel):
    """Schema for updating delivery history record"""

    transaction_time: Optional[str] = None
    salesperson: Optional[str] = None

    # Cylinder quantities
    qty_50kg: Optional[int] = None
    qty_ying20: Optional[int] = None
    qty_ying16: Optional[int] = None
    qty_20kg: Optional[int] = None
    qty_16kg: Optional[int] = None
    qty_10kg: Optional[int] = None
    qty_4kg: Optional[int] = None
    qty_haoyun16: Optional[int] = None
    qty_pingantong10: Optional[int] = None
    qty_xingfuwan4: Optional[int] = None
    qty_haoyun20: Optional[int] = None

    # Flow quantities
    flow_50kg: Optional[float] = None
    flow_20kg: Optional[float] = None
    flow_16kg: Optional[float] = None
    flow_haoyun20kg: Optional[float] = None
    flow_haoyun16kg: Optional[float] = None


class DeliveryHistoryInDB(DeliveryHistoryBase):
    """Schema for delivery history in database"""

    id: int
    customer_id: int
    total_weight_kg: float
    total_cylinders: int
    import_date: datetime
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeliveryHistory(DeliveryHistoryInDB):
    """Schema for delivery history response"""

    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    delivery_items: List[DeliveryHistoryItem] = []


class DeliveryHistoryList(BaseModel):
    """Schema for paginated delivery history list"""

    items: List[DeliveryHistory]
    total: int
    skip: int
    limit: int


class DeliveryHistoryStats(BaseModel):
    """Schema for delivery history statistics"""

    total_deliveries: int
    total_weight_kg: float
    total_cylinders: int
    unique_customers: int
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    # By cylinder type
    cylinders_by_type: dict = Field(default_factory=dict)

    # By customer
    top_customers: List[dict] = Field(default_factory=list)

    # By date
    deliveries_by_date: List[dict] = Field(default_factory=list)
