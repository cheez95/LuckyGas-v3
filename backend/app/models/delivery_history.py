from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DeliveryHistory(Base):
    """Historical delivery records imported from Excel files"""

    __tablename__ = "delivery_history"

    id = Column(Integer, primary_key=True, index=True)

    # Basic information
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_time = Column(String(10))
    salesperson = Column(String(100))
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer_code = Column(String(20), index=True)

    # Cylinder quantities delivered
    qty_50kg = Column(Integer, default=0)
    qty_ying20 = Column(Integer, default=0)  # 丙烷20
    qty_ying16 = Column(Integer, default=0)  # 丙烷16
    qty_20kg = Column(Integer, default=0)
    qty_16kg = Column(Integer, default=0)
    qty_10kg = Column(Integer, default=0)
    qty_4kg = Column(Integer, default=0)
    qty_haoyun16 = Column(Integer, default=0)  # 好運桶16
    qty_pingantong10 = Column(Integer, default=0)  # 瓶安桶10
    qty_xingfuwan4 = Column(Integer, default=0)  # 幸福丸4
    qty_haoyun20 = Column(Integer, default=0)  # 好運桶20

    # Flow meter quantities (流量)
    flow_50kg = Column(Float, default=0)  # 流量50公斤
    flow_20kg = Column(Float, default=0)  # 流量20公斤
    flow_16kg = Column(Float, default=0)  # 流量16公斤
    flow_haoyun20kg = Column(Float, default=0)  # 流量好運20公斤
    flow_haoyun16kg = Column(Float, default=0)  # 流量好運16公斤

    # Calculated fields
    total_weight_kg = Column(Float)  # Total weight delivered
    total_cylinders = Column(Integer)  # Total number of cylinders

    # Metadata
    import_date = Column(DateTime(timezone=True), server_default=func.now())
    source_file = Column(String(200))  # Which Excel file this came from
    source_sheet = Column(String(100))  # Which sheet in the Excel file

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", backref="delivery_history")
    delivery_items = relationship(
        "DeliveryHistoryItem",
        back_populates="delivery_history",
        cascade="all, delete-orphan",
    )
