from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class PredictionBatch(Base):
    __tablename__ = "prediction_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, nullable=False)  # User ID
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    total_customers = Column(Integer, default=0)
    processed_customers = Column(Integer, default=0)
    successful_predictions = Column(Integer, default=0)
    failed_predictions = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)