from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CustomerInventory(Base):
    """Track customer's gas cylinder inventory by product type"""

    __tablename__ = "customer_inventory"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    gas_product_id = Column(Integer, ForeignKey("gas_products.id"), nullable=False)

    # Inventory counts
    quantity_owned = Column(Integer, default=0)  # Cylinders owned by customer
    quantity_rented = Column(Integer, default=0)  # Cylinders rented from us
    quantity_total = Column(Integer, default=0)  # Total cylinders at customer

    # Flow meter tracking
    flow_meter_count = Column(Integer, default=0)  # Number of flow meters
    last_meter_reading = Column(Float, default=0)  # Last flow meter reading

    # Deposit tracking
    deposit_paid = Column(Float, default=0)  # Total deposit paid for rented cylinders

    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    customer = relationship("Customer", back_populates="inventory_items")
    gas_product = relationship("GasProduct")

    # Unique constraint - one record per customer per product
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "gas_product_id", name="uq_customer_product_inventory"
        ),
    )

    @property
    def needs_refill(self):
        """Check if inventory might need refilling based on quantity"""
        # Simple logic - can be enhanced with consumption patterns
        return self.quantity_total <= 1

    def update_total(self):
        """Update total quantity"""
        self.quantity_total = self.quantity_owned + self.quantity_rented
