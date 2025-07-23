from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(20), unique=True, index=True, nullable=False)
    invoice_title = Column(String(200))
    short_name = Column(String(100), nullable=False)
    address = Column(String(500), nullable=False)
    
    # Cylinder inventory
    cylinders_50kg = Column(Integer, default=0)
    cylinders_20kg = Column(Integer, default=0)
    cylinders_16kg = Column(Integer, default=0)
    cylinders_10kg = Column(Integer, default=0)
    cylinders_4kg = Column(Integer, default=0)
    
    # Special cylinder types
    cylinders_ying20 = Column(Integer, default=0)  # 營20
    cylinders_ying16 = Column(Integer, default=0)  # 營16
    cylinders_haoyun20 = Column(Integer, default=0)  # 好運20
    cylinders_haoyun16 = Column(Integer, default=0)  # 好運16
    
    # Delivery preferences
    delivery_time_start = Column(String(5))  # "08:00"
    delivery_time_end = Column(String(5))    # "09:00"
    delivery_time_slot = Column(Integer)     # 0=全天, 1=早, 2=午, 3=晚
    area = Column(String(50))
    delivery_type = Column(Integer, default=0)  # 0=全部, 1=汽車, 2=機車
    
    # Consumption data
    avg_daily_usage = Column(Float)
    max_cycle_days = Column(Integer)
    can_delay_days = Column(Integer)
    monthly_delivery_volume = Column(Float)
    
    # Pricing and payment
    pricing_method = Column(String(50))
    payment_method = Column(String(50))
    
    # Status flags
    is_subscription = Column(Boolean, default=False)  # 訂閱式會員
    needs_report = Column(Boolean, default=False)     # 發報
    needs_patrol = Column(Boolean, default=False)     # 排巡
    is_equipment_purchased = Column(Boolean, default=False)  # 設備客戶買斷
    is_terminated = Column(Boolean, default=False)    # 已解約
    needs_same_day_delivery = Column(Boolean, default=False)  # 需要當天配送
    
    # Business days
    closed_days = Column(String(100))  # 公休日
    
    # Equipment
    regulator_model = Column(String(100))  # 切替器型號
    has_flow_meter = Column(Boolean, default=False)  # 流量表
    has_wired_flow_meter = Column(Boolean, default=False)  # 帶線流量錶
    has_regulator = Column(Boolean, default=False)  # 切替器
    has_pressure_gauge = Column(Boolean, default=False)  # 接點式壓力錶
    has_pressure_switch = Column(Boolean, default=False)  # 壓差開關
    has_micro_switch = Column(Boolean, default=False)  # 微動開關
    has_smart_scale = Column(Boolean, default=False)  # 智慧秤
    
    # Customer type
    customer_type = Column(String(50))  # 類型 (學校, 商業, etc.)
    
    # Contact information
    phone = Column(String(15))  # 電話
    tax_id = Column(String(8))  # 統一編號
    
    # Location
    latitude = Column(Float)  # 緯度
    longitude = Column(Float)  # 經度
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    inventory_items = relationship("CustomerInventory", back_populates="customer", cascade="all, delete-orphan")
    predictions = relationship("DeliveryPrediction", back_populates="customer")