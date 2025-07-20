from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Delivery(Base):
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    
    # Delivery tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Location
    latitude = Column(Float)
    longitude = Column(Float)
    actual_address = Column(String(500))
    
    # Proof of delivery
    recipient_name = Column(String(100))
    recipient_signature = Column(Text)  # Base64 encoded signature
    proof_photo_url = Column(String(500))
    delivery_notes = Column(Text)
    
    # Status
    is_successful = Column(Boolean, default=True)
    failure_reason = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="delivery")


class DeliveryPrediction(Base):
    __tablename__ = "delivery_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Prediction details
    predicted_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Predicted quantities for each cylinder size
    predicted_quantity_50kg = Column(Integer, default=0)
    predicted_quantity_20kg = Column(Integer, default=0)
    predicted_quantity_16kg = Column(Integer, default=0)
    predicted_quantity_10kg = Column(Integer, default=0)
    predicted_quantity_4kg = Column(Integer, default=0)
    
    # Prediction metadata
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0
    model_version = Column(String(50))
    factors_json = Column(Text)  # JSON string of factors that influenced the prediction
    
    # Status
    is_converted_to_order = Column(Boolean, default=False)
    converted_order_id = Column(Integer, ForeignKey("orders.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="predictions")