import enum

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CustomerType(str, enum.Enum):
    """Customer type enumeration"""

    # Support both uppercase (from DB) and lowercase
    RESIDENTIAL = "RESIDENTIAL"  # 住宅
    COMMERCIAL = "COMMERCIAL"  # 商業
    INDUSTRIAL = "INDUSTRIAL"  # 工業
    RESTAURANT = "RESTAURANT"  # 餐廳
    SCHOOL = "SCHOOL"  # 學校
    HOSPITAL = "HOSPITAL"  # 醫院
    OTHER = "OTHER"  # 其他
    
    # Also support lowercase for backwards compatibility
    residential = "residential"  # 住宅
    commercial = "commercial"  # 商業
    industrial = "industrial"  # 工業
    restaurant = "restaurant"  # 餐廳
    school = "school"  # 學校
    hospital = "hospital"  # 醫院
    other = "other"  # 其他


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
    # cylinders_4kg = Column(Integer, default=0)  # Not in DB

    # Special cylinder types - NOT IN DATABASE
    # cylinders_ying20 = Column(Integer, default=0)  # 營20
    # cylinders_ying16 = Column(Integer, default=0)  # 營16
    # cylinders_haoyun20 = Column(Integer, default=0)  # 好運20
    # cylinders_haoyun16 = Column(Integer, default=0)  # 好運16

    # Delivery preferences - PARTIALLY IN DATABASE
    # delivery_time_start = Column(String(5))  # "08:00" - Not in DB
    # delivery_time_end = Column(String(5))  # "09:00" - Not in DB
    # delivery_time_slot = Column(Integer)  # 0=全天, 1=早, 2=午, 3=晚 - Not in DB
    area = Column(String(50))
    # delivery_type = Column(Integer, default=0)  # 0=全部, 1=汽車, 2=機車 - Not in DB

    # Consumption data - NOT IN DATABASE
    # avg_daily_usage = Column(Float)

    # Relationships
    order_templates = relationship("OrderTemplate", back_populates="customer")
    # max_cycle_days = Column(Integer)  # Not in DB
    # can_delay_days = Column(Integer)  # Not in DB
    # monthly_delivery_volume = Column(Float)  # Not in DB

    # Pricing and payment - NOT IN DATABASE
    # pricing_method = Column(String(50))
    # payment_method = Column(String(50))

    # Banking information for automatic payment - NOT IN DATABASE
    # bank_code = Column(String(10))  # 銀行代碼
    # bank_account_number = Column(String(20))  # 銀行帳號
    # bank_account_holder = Column(String(100))  # 戶名

    # Customer classification
    customer_type = Column(String(50))  # household, restaurant, industrial, commercial

    # Credit management - NOT IN DATABASE
    # credit_limit = Column(Float, default=0.0)  # 信用額度
    # current_balance = Column(Float, default=0.0)  # 當前應收帳款
    # is_credit_blocked = Column(Boolean, default=False)  # 信用額度封鎖

    # Status flags
    is_active = Column(Boolean, default=True)  # 是否有效客戶
    is_subscription = Column(Boolean, default=False)  # 訂閱式會員
    # needs_report = Column(Boolean, default=False)  # 發報 - Not in DB
    # needs_patrol = Column(Boolean, default=False)  # 排巡 - Not in DB
    # is_equipment_purchased = Column(Boolean, default=False)  # 設備客戶買斷 - Not in DB
    # is_terminated = Column(Boolean, default=False)  # 已解約 - Not in DB
    # needs_same_day_delivery = Column(Boolean, default=False)  # 需要當天配送 - Not in DB

    # Business days - NOT IN DATABASE
    # closed_days = Column(String(100))  # 公休日

    # Equipment - NOT IN DATABASE
    # regulator_model = Column(String(100))  # 切替器型號
    # has_flow_meter = Column(Boolean, default=False)  # 流量表
    # has_wired_flow_meter = Column(Boolean, default=False)  # 帶線流量錶
    # has_regulator = Column(Boolean, default=False)  # 切替器
    # has_pressure_gauge = Column(Boolean, default=False)  # 接點式壓力錶
    # has_pressure_switch = Column(Boolean, default=False)  # 壓差開關
    # has_micro_switch = Column(Boolean, default=False)  # 微動開關
    # has_smart_scale = Column(Boolean, default=False)  # 智慧秤

    # Contact information
    phone = Column(String(15))  # 電話
    # tax_id = Column(String(8))  # 統一編號 - Not in DB

    # Location - NOT IN DATABASE
    # latitude = Column(Float)  # 緯度
    # longitude = Column(Float)  # 經度

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    orders = relationship("Order", back_populates="customer")
    inventory_items = relationship(
        "CustomerInventory", back_populates="customer", cascade="all, delete-orphan"
    )
    predictions = relationship("DeliveryPrediction", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
