from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class DeliveryHistoryItem(Base):
    """Individual line items in historical deliveries"""

    __tablename__ = "delivery_history_items"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    delivery_history_id = Column(
        Integer, ForeignKey("delivery_history.id"), nullable=False
    )
    gas_product_id = Column(Integer, ForeignKey("gas_products.id"), nullable=False)

    # Quantity and pricing
    quantity = Column(Integer, nullable=False)  # Number of cylinders or kg for flow
    unit_price = Column(Float, nullable=False)  # Price at time of delivery
    subtotal = Column(Float, nullable=False)  # quantity * unit_price

    # Delivery type
    is_flow_delivery = Column(Boolean, default=False)

    # Flow meter specific (for historical data import)
    flow_quantity = Column(Float)  # Actual kg delivered for flow deliveries

    # Legacy product identification (for import/mapping)
    legacy_product_code = Column(String(50))  # e.g., "qty_50kg", "flow_haoyun20kg"

    # Relationships
    delivery_history = relationship("DeliveryHistory", back_populates="delivery_items")
    gas_product = relationship("GasProduct")

    @property
    def is_cylinder_product(self):
        """Check if this is a cylinder product"""
        return not self.is_flow_delivery

    def calculate_subtotal(self):
        """Calculate subtotal based on quantity and unit price"""
        if self.is_flow_delivery and self.flow_quantity:
            self.subtotal = self.flow_quantity * self.unit_price
        else:
            self.subtotal = self.quantity * self.unit_price
        return self.subtotal
