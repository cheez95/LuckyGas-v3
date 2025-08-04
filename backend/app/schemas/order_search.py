from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class OrderSearchCriteria(BaseModel):
    """訂單搜尋條件"""

    # Full-text search
    keyword: Optional[str] = None

    # Date range
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Multiple selection filters
    status: Optional[List[str]] = None
    priority: Optional[List[str]] = None
    payment_status: Optional[List[str]] = None
    payment_method: Optional[List[str]] = None
    cylinder_type: Optional[List[str]] = None

    # Specific IDs
    customer_id: Optional[int] = None
    driver_id: Optional[int] = None

    # Amount range
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

    # Additional filters
    region: Optional[str] = None
    customer_type: Optional[str] = None

    # Pagination
    skip: int = 0
    limit: int = 100


class OrderSearchResult(BaseModel):
    """訂單搜尋結果"""

    orders: List[dict]
    total: int
    skip: int
    limit: int
    search_time: float  # Search execution time in milliseconds
