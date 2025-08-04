from sqlalchemy import Column, Integer, ForeignKey, Float, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class OrderItem(Base):
    """Individual line items in an order"""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    gas_product_id = Column(Integer, ForeignKey("gas_products.id"), nullable=False)

    # Quantity and pricing
    quantity = Column(Integer, nullable=False)  # Number of cylinders or kg for flow
    unit_price = Column(Float, nullable=False)  # Price at time of order
    subtotal = Column(Float, nullable=False)  # quantity * unit_price

    # Discounts
    discount_percentage = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    final_amount = Column(Float, nullable=False)  # subtotal - discount_amount

    # Delivery details
    is_exchange = Column(Boolean, default=True)  # Exchange empty for full cylinder
    empty_received = Column(Integer, default=0)  # Empty cylinders received

    # Flow meter specific
    is_flow_delivery = Column(Boolean, default=False)
    meter_reading_start = Column(Float)  # For flow deliveries
    meter_reading_end = Column(Float)
    actual_quantity = Column(Float)  # Actual kg delivered for flow

    # Special instructions
    notes = Column(String(500))

    # Relationships
    order = relationship("Order", back_populates="order_items")
    gas_product = relationship("GasProduct")

    @property
    def is_cylinder_product(self):
        """Check if this is a cylinder product"""
        return not self.is_flow_delivery

    def calculate_subtotal(self):
        """Calculate subtotal based on quantity and unit price"""
        if self.is_flow_delivery and self.actual_quantity:
            self.subtotal = self.actual_quantity * self.unit_price
        else:
            self.subtotal = self.quantity * self.unit_price
        return self.subtotal

    def calculate_final_amount(self):
        """Calculate final amount after discounts"""
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)
        self.final_amount = self.subtotal - self.discount_amount
        return self.final_amount
