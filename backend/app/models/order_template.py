from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrderTemplate(Base):
    __tablename__ = "order_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Template identification
    template_name = Column(String(100), nullable=False)
    template_code = Column(String(50), unique=True, index=True)
    description = Column(Text)

    # Customer association
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="order_templates")

    # Template content (stored as JSON for flexibility)
    products = Column(JSON, nullable=False)
    # Example structure:
    # [
    #   {
    #     "gas_product_id": 1,
    #     "quantity": 2,
    #     "unit_price": 800,
    #     "discount_percentage": 0,
    #     "is_exchange": True,
    #     "empty_received": 2
    #   }
    # ]

    # Delivery preferences
    delivery_notes = Column(Text)
    priority = Column(String(20), default="normal")  # normal, urgent, scheduled
    payment_method = Column(String(20), default="cash")  # cash, transfer, credit

    # Scheduling options
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50))  # daily, weekly, monthly, custom
    recurrence_interval = Column(Integer, default=1)  # Every N days/weeks/months
    recurrence_days = Column(JSON)  # For weekly: [1,3,5] for Mon/Wed/Fri
    next_scheduled_date = Column(DateTime)

    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime)

    # Status
    is_active = Column(Boolean, default=True)

    # Audit fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))
    updated_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    def to_dict(self):
        """Convert template to dictionary"""
        return {
            "id": self.id,
            "template_name": self.template_name,
            "template_code": self.template_code,
            "description": self.description,
            "customer_id": self.customer_id,
            "products": self.products,
            "delivery_notes": self.delivery_notes,
            "priority": self.priority,
            "payment_method": self.payment_method,
            "is_recurring": self.is_recurring,
            "recurrence_pattern": self.recurrence_pattern,
            "recurrence_interval": self.recurrence_interval,
            "recurrence_days": self.recurrence_days,
            "next_scheduled_date": (
                self.next_scheduled_date.isoformat()
                if self.next_scheduled_date
                else None
            ),
            "times_used": self.times_used,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
