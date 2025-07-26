"""
Driver API schemas
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class RouteStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class DeliveryStatusEnum(str, Enum):
    PENDING = "pending"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"

class RouteListResponse(BaseModel):
    """Route summary for list view"""
    id: str
    name: str
    deliveryCount: int = Field(..., description="Total number of deliveries")
    completedCount: int = Field(..., description="Number of completed deliveries")
    estimatedTime: str = Field(..., description="Estimated time in format like '4小時30分'")
    distance: float = Field(..., description="Total distance in kilometers")
    status: RouteStatusEnum

class DeliveryProduct(BaseModel):
    """Product in a delivery"""
    name: str
    quantity: int

class DeliveryDetail(BaseModel):
    """Delivery details within a route"""
    id: str
    customerName: str
    address: str
    phone: str
    products: List[DeliveryProduct]
    notes: Optional[str] = None
    status: str
    sequence: int

class RouteDetailResponse(BaseModel):
    """Detailed route information"""
    id: str
    name: str
    totalDeliveries: int
    completedDeliveries: int
    estimatedDuration: str
    totalDistance: float
    deliveries: List[DeliveryDetail]

class DeliveryStatsResponse(BaseModel):
    """Driver's delivery statistics"""
    total: int
    completed: int
    pending: int
    failed: int

class LocationUpdateRequest(BaseModel):
    """Driver location update"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, description="GPS accuracy in meters")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    speed: Optional[float] = Field(None, description="Speed in km/h")
    heading: Optional[float] = Field(None, description="Heading in degrees")

class DeliveryStatusUpdateRequest(BaseModel):
    """Update delivery status"""
    status: DeliveryStatusEnum
    notes: Optional[str] = None
    issue_type: Optional[str] = Field(None, description="Issue type if status is failed")

class DeliveryConfirmRequest(BaseModel):
    """Confirm delivery completion"""
    recipient_name: Optional[str] = None
    notes: Optional[str] = None
    signature: Optional[str] = Field(None, description="Base64 encoded signature image")
    photo: Optional[str] = Field(None, description="Base64 encoded photo")

class DeliveryConfirmResponse(BaseModel):
    """Delivery confirmation response"""
    success: bool
    message: str
    delivery_id: str
    order_id: str

class DriverSyncRequest(BaseModel):
    """Sync offline data from driver app"""
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    deliveries: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DriverSyncResponse(BaseModel):
    """Sync response with updated data"""
    success: bool
    synced_count: int
    failed_count: int
    synced_items: List[Dict[str, Any]]
    failed_items: List[Dict[str, Any]]
    updated_routes: List[RouteListResponse]
    updated_stats: DeliveryStatsResponse