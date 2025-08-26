"""
Comprehensive database models for Lucky Gas Management System
全面的幸福氣管理系統資料庫模型

This schema ensures ALL data from the Excel client list is preserved.
此模式確保保留Excel客戶清單中的所有資料。
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, 
    ForeignKey, Text, Enum, JSON, Date, Time, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ============================
# ENUMERATIONS 列舉型態
# ============================

class UserRole(str, enum.Enum):
    """使用者角色"""
    SUPER_ADMIN = "SUPER_ADMIN"  # 超級管理員
    MANAGER = "MANAGER"  # 經理
    OFFICE_STAFF = "OFFICE_STAFF"  # 辦公室職員
    DRIVER = "DRIVER"  # 司機
    CUSTOMER = "CUSTOMER"  # 客戶


class OrderStatus(str, enum.Enum):
    """訂單狀態"""
    PENDING = "pending"  # 待處理
    CONFIRMED = "confirmed"  # 已確認
    ASSIGNED = "assigned"  # 已分配
    IN_PROGRESS = "in_progress"  # 配送中
    DELIVERED = "delivered"  # 已送達
    CANCELLED = "cancelled"  # 已取消


class CustomerType(str, enum.Enum):
    """客戶類型"""
    RESIDENTIAL = "residential"  # 住宅
    COMMERCIAL = "commercial"  # 商業
    RESTAURANT = "restaurant"  # 餐廳
    INDUSTRIAL = "industrial"  # 工業
    SCHOOL = "school"  # 學校
    HOSPITAL = "hospital"  # 醫院
    HOTEL = "hotel"  # 飯店
    OTHER = "other"  # 其他


class CylinderType(str, enum.Enum):
    """瓦斯桶類型"""
    STANDARD_50KG = "standard_50kg"  # 標準50公斤
    STANDARD_20KG = "standard_20kg"  # 標準20公斤
    STANDARD_16KG = "standard_16kg"  # 標準16公斤
    STANDARD_10KG = "standard_10kg"  # 標準10公斤
    STANDARD_4KG = "standard_4kg"  # 標準4公斤
    COMMERCIAL_20KG = "commercial_20kg"  # 營業用20公斤
    COMMERCIAL_16KG = "commercial_16kg"  # 營業用16公斤
    LUCKY_20KG = "lucky_20kg"  # 好運20公斤
    LUCKY_16KG = "lucky_16kg"  # 好運16公斤
    LUCKY_PILL = "lucky_pill"  # 幸福丸
    SAFETY_BUCKET_10KG = "safety_bucket_10kg"  # 瓶安桶10公斤
    FLOW_50KG = "flow_50kg"  # 流量50公斤
    FLOW_20KG = "flow_20kg"  # 流量20公斤
    FLOW_16KG = "flow_16kg"  # 流量16公斤
    FLOW_LUCKY_20KG = "flow_lucky_20kg"  # 流量好運20公斤
    FLOW_LUCKY_16KG = "flow_lucky_16kg"  # 流量好運16公斤


class PricingMethod(str, enum.Enum):
    """計價方式"""
    BY_CYLINDER = "by_cylinder"  # 桶裝計價
    BY_WEIGHT = "by_weight"  # 重量計價
    BY_FLOW = "by_flow"  # 流量計價
    FIXED_MONTHLY = "fixed_monthly"  # 月費固定


class PaymentMethod(str, enum.Enum):
    """結帳方式"""
    MONTHLY = "monthly"  # 月結
    CASH = "cash"  # 現金
    TRANSFER = "transfer"  # 轉帳
    CREDIT_CARD = "credit_card"  # 信用卡


class VehicleType(str, enum.Enum):
    """運輸工具類型"""
    CAR = "car"  # 汽車
    MOTORCYCLE = "motorcycle"  # 機車
    BOTH = "both"  # 兩者都可


class TimePreference(str, enum.Enum):
    """時段偏好"""
    MORNING = "morning"  # 早上 (1)
    AFTERNOON = "afternoon"  # 下午 (2)
    EVENING = "evening"  # 晚上 (3)
    ALL_DAY = "all_day"  # 全天 (0)


class WeekDay(str, enum.Enum):
    """星期幾"""
    MONDAY = "monday"  # 星期一
    TUESDAY = "tuesday"  # 星期二
    WEDNESDAY = "wednesday"  # 星期三
    THURSDAY = "thursday"  # 星期四
    FRIDAY = "friday"  # 星期五
    SATURDAY = "saturday"  # 星期六
    SUNDAY = "sunday"  # 星期日
    RED = "red"  # 紅字日（國定假日）


# ============================
# USER MODELS 使用者模型
# ============================

class User(Base):
    """使用者資料表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)  # 電子郵件
    username = Column(String(50), unique=True, index=True, nullable=False)  # 使用者名稱
    full_name = Column(String(100))  # 全名
    phone = Column(String(20))  # 電話號碼
    hashed_password = Column(String(255), nullable=False)  # 加密密碼
    is_active = Column(Boolean, default=True)  # 是否啟用
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)  # 角色
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))  # 最後登入時間
    
    # Relationships
    notifications = relationship("Notification", back_populates="user")


# ============================
# CUSTOMER MODELS 客戶模型
# ============================

class Customer(Base):
    """客戶主資料表"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(20), unique=True, index=True, nullable=False)  # 客戶代碼
    
    # 基本資訊
    invoice_title = Column(String(200))  # 電子發票抬頭
    short_name = Column(String(100), nullable=False)  # 客戶簡稱
    address = Column(String(500), nullable=False)  # 地址
    phone = Column(String(20))  # 電話
    tax_id = Column(String(20))  # 統一編號
    
    # 區域與類型
    area = Column(String(50))  # 區域 (e.g., "D-東方大鎮")
    customer_type = Column(Enum(CustomerType), default=CustomerType.COMMERCIAL)  # 客戶類型
    
    # 訂購與結帳設定
    pricing_method = Column(Enum(PricingMethod), default=PricingMethod.BY_CYLINDER)  # 計價方式
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.MONTHLY)  # 結帳方式
    requires_invoice_file = Column(Boolean, default=False)  # 結帳用檔案
    
    # 會員與服務狀態
    is_subscription = Column(Boolean, default=False)  # 訂閱式會員
    auto_report = Column(Boolean, default=False)  # 發報 (自動通報)
    scheduled_patrol = Column(Boolean, default=True)  # 排巡 (定期巡檢)
    equipment_owned_by_customer = Column(Text)  # 設備客戶買斷
    
    # 配送設定
    same_day_delivery = Column(Boolean, default=False)  # 需要當天配送
    vehicle_requirement = Column(Enum(VehicleType), default=VehicleType.CAR)  # 1汽車/2機車/0全部
    single_area_supply = Column(Integer)  # 單一區域供應
    
    # 狀態
    is_active = Column(Boolean, default=True)  # 是否啟用
    is_terminated = Column(Boolean, default=False)  # 已解約
    termination_date = Column(Date)  # 解約日期
    termination_reason = Column(Text)  # 解約原因
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    cylinders = relationship("CustomerCylinder", back_populates="customer", cascade="all, delete-orphan")
    time_availability = relationship("CustomerTimeAvailability", back_populates="customer", cascade="all, delete-orphan")
    equipment = relationship("CustomerEquipment", back_populates="customer", cascade="all, delete-orphan")
    usage_areas = relationship("CustomerUsageArea", back_populates="customer", cascade="all, delete-orphan")
    usage_metrics = relationship("CustomerUsageMetrics", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer")
    order_templates = relationship("OrderTemplate", back_populates="customer")
    delivery_history = relationship("DeliveryHistory", back_populates="customer")
    
    # Indexes
    __table_args__ = (
        Index('idx_customer_area', 'area'),
        Index('idx_customer_type', 'customer_type'),
        Index('idx_customer_active', 'is_active'),
    )


class CustomerCylinder(Base):
    """客戶瓦斯桶庫存資料表 - 整合所有瓦斯桶相關欄位"""
    __tablename__ = "customer_cylinders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # 瓦斯桶類型與數量
    cylinder_type = Column(Enum(CylinderType), nullable=False)  # 瓦斯桶類型
    quantity = Column(Integer, default=0)  # 數量
    
    # 系統記錄的設定
    system_config = Column(String(100))  # 系統上鋼瓶數量 (e.g., "20*5+16*1")
    
    # 備用桶設定
    is_spare = Column(Boolean, default=False)  # 是否為備用桶
    spare_config = Column(String(100))  # 預備桶設定
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="cylinders")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', 'cylinder_type', name='uq_customer_cylinder'),
        Index('idx_customer_cylinder', 'customer_id', 'cylinder_type'),
    )


class CustomerTimeAvailability(Base):
    """客戶可配送時間資料表 - 整合所有時段欄位"""
    __tablename__ = "customer_time_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # 時段偏好設定
    time_preference = Column(Enum(TimePreference), default=TimePreference.ALL_DAY)  # 時段早1午2晚3全天0
    
    # 各時段可用性 (True = 可配送)
    available_0800_0900 = Column(Boolean, default=False)  # 8~9
    available_0900_1000 = Column(Boolean, default=False)  # 9~10
    available_1000_1100 = Column(Boolean, default=False)  # 10~11
    available_1100_1200 = Column(Boolean, default=False)  # 11~12
    available_1200_1300 = Column(Boolean, default=False)  # 12~13
    available_1300_1400 = Column(Boolean, default=False)  # 13~14
    available_1400_1500 = Column(Boolean, default=False)  # 14~15
    available_1500_1600 = Column(Boolean, default=False)  # 15~16
    available_1600_1700 = Column(Boolean, default=False)  # 16~17
    available_1700_1800 = Column(Boolean, default=False)  # 17~18
    available_1800_1900 = Column(Boolean, default=False)  # 18~19
    available_1900_2000 = Column(Boolean, default=False)  # 19~20
    
    # 公休日設定
    rest_day = Column(Enum(WeekDay))  # 公休日
    
    # 特殊配送需求
    needs_same_day_service = Column(Float)  # 是否需要當天去 (評分)
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="time_availability")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', name='uq_customer_time'),
    )


class CustomerEquipment(Base):
    """客戶設備資料表 - 整合所有設備監控相關欄位"""
    __tablename__ = "customer_equipment"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # 切替器與監控設備
    switch_model = Column(String(100))  # 切替器型號
    
    # 各種監控設備 (Boolean表示有無)
    has_flow_meter = Column(Boolean, default=False)  # 流量表
    has_wired_flow_meter = Column(Boolean, default=False)  # 帶線流量錶
    has_switch = Column(Boolean, default=False)  # 切替器
    has_contact_pressure_gauge = Column(Boolean, default=False)  # 接點式壓力錶
    has_pressure_switch = Column(Boolean, default=False)  # 壓差開關
    has_micro_switch = Column(Boolean, default=False)  # 微動開關
    has_yongsheng = Column(Boolean, default=False)  # 永勝
    has_smart_scale = Column(Boolean, default=False)  # 智慧秤
    
    # 串接場所申報
    connection_site_declaration = Column(Text)  # 串接場所申報
    
    # 備註
    notes = Column(Text)  # 設備相關備註
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="equipment")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', name='uq_customer_equipment'),
    )


class CustomerUsageArea(Base):
    """客戶使用區域資料表 - 整合第一到第五使用區域"""
    __tablename__ = "customer_usage_areas"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # 使用區域序號
    area_sequence = Column(Integer, nullable=False)  # 1-5 表示第一到第五使用區域
    
    # 區域資訊
    area_description = Column(String(200))  # 區域描述 (e.g., "煎台16*1", "快速20*1")
    cylinder_config = Column(String(100))  # 瓦斯桶配置 (e.g., "20KG:3", "20*2+16*2")
    
    # 串接資訊
    is_connected = Column(Boolean, default=False)  # 是否串接
    connection_count = Column(Integer)  # 串接數量
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="usage_areas")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', 'area_sequence', name='uq_customer_area_seq'),
        Index('idx_customer_usage_area', 'customer_id', 'area_sequence'),
    )


class CustomerUsageMetrics(Base):
    """客戶使用指標資料表 - 整合消費模式相關欄位"""
    __tablename__ = "customer_usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # 消費量指標
    monthly_delivery_volume = Column(Float)  # 月配送量
    gas_return_volume = Column(Float)  # 退氣
    actual_purchase_kg = Column(Float)  # 實際購買公斤數
    gas_return_ratio = Column(Float)  # 退氣比例
    avg_daily_usage = Column(Float)  # 平均日使用
    
    # 串接與備用量
    connection_quantity = Column(Float)  # 串接數量
    reserve_quantity = Column(Float)  # 備用量
    
    # 週期指標
    max_cycle_days = Column(Float)  # 最大週期
    postpone_days = Column(Float)  # 可延後天數
    
    # 計算日期
    calculated_date = Column(Date)  # 計算日期
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="usage_metrics")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', 'calculated_date', name='uq_customer_metrics_date'),
        Index('idx_customer_metrics', 'customer_id', 'calculated_date'),
    )


# ============================
# DRIVER MODELS 司機模型
# ============================

class Driver(Base):
    """司機資料表"""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)  # 司機代碼
    name = Column(String(100), nullable=False)  # 姓名
    phone = Column(String(20))  # 電話
    
    # 關聯使用者帳號 (可選)
    user_id = Column(Integer, ForeignKey("users.id"))  # 使用者ID
    
    # 車輛資訊
    vehicle_type = Column(Enum(VehicleType))  # 車輛類型
    license_plate = Column(String(20))  # 車牌號碼
    
    # 工作設定
    max_daily_orders = Column(Integer, default=30)  # 每日最大訂單數
    working_area = Column(String(100))  # 工作區域
    
    # 狀態
    is_active = Column(Boolean, default=True)  # 是否啟用
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="driver", uselist=False)
    routes = relationship("Route", back_populates="driver")
    orders = relationship("Order", back_populates="driver")


# ============================
# ORDER MODELS 訂單模型
# ============================

class Order(Base):
    """訂單資料表"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)  # 訂單編號
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)  # 客戶ID
    
    # 訂單詳情
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)  # 訂單狀態
    order_date = Column(DateTime(timezone=True), default=func.now())  # 訂單日期
    delivery_date = Column(DateTime(timezone=True))  # 預定配送日期
    
    # 瓦斯桶數量 (JSON格式儲存各種類型)
    cylinder_quantities = Column(JSON)  # {"standard_50kg": 2, "standard_20kg": 1, ...}
    
    # 價格
    total_amount = Column(Float, default=0.0)  # 總金額
    discount_amount = Column(Float, default=0.0)  # 折扣金額
    
    # 分配
    driver_id = Column(Integer, ForeignKey("drivers.id"))  # 司機ID
    route_id = Column(Integer, ForeignKey("routes.id"))  # 路線ID
    
    # 備註
    customer_notes = Column(Text)  # 客戶備註
    internal_notes = Column(Text)  # 內部備註
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    driver = relationship("Driver", back_populates="orders")
    route = relationship("Route", back_populates="orders")
    delivery = relationship("Delivery", back_populates="order", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_order_customer', 'customer_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_date', 'order_date'),
    )


class OrderTemplate(Base):
    """訂單範本資料表 - 用於定期訂單"""
    __tablename__ = "order_templates"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)  # 客戶ID
    
    # 範本詳情
    template_name = Column(String(100))  # 範本名稱
    
    # 預設瓦斯桶數量 (JSON格式)
    default_cylinders = Column(JSON)  # {"standard_50kg": 2, "standard_20kg": 1, ...}
    
    # 重複設定
    frequency_days = Column(Integer, default=30)  # 頻率（天）
    is_active = Column(Boolean, default=True)  # 是否啟用
    
    # 時間戳記
    last_used = Column(DateTime(timezone=True))  # 最後使用時間
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="order_templates")


# ============================
# ROUTE MODELS 路線模型
# ============================

class Route(Base):
    """路線資料表"""
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(50), unique=True, index=True, nullable=False)  # 路線代碼
    route_date = Column(Date, nullable=False)  # 路線日期
    driver_id = Column(Integer, ForeignKey("drivers.id"))  # 司機ID
    
    # 路線資訊
    area = Column(String(50))  # 區域
    total_stops = Column(Integer, default=0)  # 總停靠點
    completed_stops = Column(Integer, default=0)  # 已完成停靠點
    total_distance = Column(Float, default=0.0)  # 總距離（公里）
    
    # 狀態
    is_optimized = Column(Boolean, default=False)  # 是否已優化
    is_completed = Column(Boolean, default=False)  # 是否已完成
    
    # 時間戳記
    start_time = Column(DateTime(timezone=True))  # 開始時間
    end_time = Column(DateTime(timezone=True))  # 結束時間
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    driver = relationship("Driver", back_populates="routes")
    orders = relationship("Order", back_populates="route")
    deliveries = relationship("Delivery", back_populates="route")
    
    # Indexes
    __table_args__ = (
        Index('idx_route_date', 'route_date'),
        Index('idx_route_driver', 'driver_id'),
    )


# ============================
# DELIVERY MODELS 配送模型
# ============================

class Delivery(Base):
    """配送記錄資料表"""
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)  # 訂單ID
    route_id = Column(Integer, ForeignKey("routes.id"))  # 路線ID
    
    # 配送資訊
    delivered_at = Column(DateTime(timezone=True))  # 配送時間
    signature = Column(Text)  # 簽名
    photo_url = Column(String(500))  # 照片URL
    
    # 實際配送數量 (JSON格式)
    delivered_cylinders = Column(JSON)  # {"standard_50kg": 2, "standard_20kg": 1, ...}
    
    # 狀態與備註
    is_successful = Column(Boolean, default=True)  # 是否成功
    failure_reason = Column(Text)  # 失敗原因
    notes = Column(Text)  # 備註
    
    # GPS位置
    delivery_latitude = Column(Float)  # 配送緯度
    delivery_longitude = Column(Float)  # 配送經度
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="delivery")
    route = relationship("Route", back_populates="deliveries")


class DeliveryHistory(Base):
    """歷史配送記錄資料表 - 用於分析與預測"""
    __tablename__ = "delivery_history"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)  # 客戶ID
    
    # 配送資訊
    delivery_date = Column(Date, nullable=False)  # 配送日期
    cylinders_delivered = Column(JSON)  # 配送的瓦斯桶 {"type": quantity}
    
    # 消費指標
    days_since_last = Column(Integer)  # 距離上次配送天數
    consumption_rate = Column(Float)  # 消費率
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="delivery_history")
    
    # Indexes
    __table_args__ = (
        Index('idx_delivery_history_customer', 'customer_id'),
        Index('idx_delivery_history_date', 'delivery_date'),
    )


# ============================
# NOTIFICATION MODELS 通知模型
# ============================

class Notification(Base):
    """通知資料表"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # 使用者ID
    
    # 通知詳情
    title = Column(String(200), nullable=False)  # 標題
    message = Column(Text, nullable=False)  # 訊息
    type = Column(String(50))  # 類型 (info, warning, error, success)
    priority = Column(Integer, default=0)  # 優先級
    
    # 狀態
    is_read = Column(Boolean, default=False)  # 是否已讀
    read_at = Column(DateTime(timezone=True))  # 讀取時間
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # 過期時間
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_read', 'is_read'),
    )


# ============================
# SYSTEM MODELS 系統模型
# ============================

class FeatureFlag(Base):
    """功能開關資料表"""
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)  # 功能名稱
    description = Column(Text)  # 描述
    is_enabled = Column(Boolean, default=False)  # 是否啟用
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemLog(Base):
    """系統日誌資料表"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # 使用者ID
    
    # 日誌資訊
    action = Column(String(100), nullable=False)  # 動作
    entity_type = Column(String(50))  # 實體類型
    entity_id = Column(Integer)  # 實體ID
    details = Column(JSON)  # 詳細資料
    
    # IP與裝置資訊
    ip_address = Column(String(50))  # IP位址
    user_agent = Column(Text)  # 使用者代理
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_log_user', 'user_id'),
        Index('idx_log_action', 'action'),
        Index('idx_log_created', 'created_at'),
    )