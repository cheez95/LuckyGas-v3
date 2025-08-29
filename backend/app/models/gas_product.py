from enum import Enum

from sqlalchemy import Boolean, Column
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Integer, String, UniqueConstraint

from app.core.database import Base


class DeliveryMethod(str, Enum):
    """Gas delivery methods"""

    CYLINDER = "CYLINDER"  # 桶裝
    FLOW = "FLOW"  # 流量


class ProductAttribute(str, Enum):
    """Gas product attributes"""

    REGULAR = "REGULAR"  # 一般
    COMMERCIAL = "COMMERCIAL"  # 營業用 (營)
    HAOYUN = "HAOYUN"  # 好運
    PINGAN = "PINGAN"  # 瓶安
    XINGFU = "XINGFU"  # 幸福
    SPECIAL = "SPECIAL"  # 特殊 (for special products like 幸福丸)


class GasProduct(Base):
    """Gas product catalog with flexible combinations"""

    __tablename__ = "gas_products"

    id = Column(Integer, primary_key=True, index=True)

    # Product characteristics
    delivery_method = Column(SQLEnum(DeliveryMethod), nullable=False)
    size_kg = Column(Integer, nullable=False)  # 4, 10, 16, 20, 50
    attribute = Column(SQLEnum(ProductAttribute), nullable=False)

    # SKU and naming
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name_zh = Column(String(100), nullable=False)  # Traditional Chinese name
    name_en = Column(String(100))  # English name (optional)
    description = Column(String(500))

    # Pricing
    unit_price = Column(Float, nullable=False)
    deposit_amount = Column(Float, default=0)  # Cylinder deposit if applicable

    # Status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)

    # Inventory tracking hints
    track_inventory = Column(Boolean, default=True)
    low_stock_threshold = Column(Integer, default=10)

    # Unique constraint to prevent duplicate combinations
    __table_args__ = (
        UniqueConstraint(
            "delivery_method", "size_kg", "attribute", name="uq_product_combination"
        ),
    )

    @property
    def display_name(self):
        """Generate display name based on attributes"""
        method_name = (
            "桶裝" if self.delivery_method == DeliveryMethod.CYLINDER else "流量"
        )
        attr_name = {
            ProductAttribute.REGULAR: "",
            ProductAttribute.COMMERCIAL: "營",
            ProductAttribute.HAOYUN: "好運",
            ProductAttribute.PINGAN: "瓶安",
            ProductAttribute.XINGFU: "幸福",
            ProductAttribute.SPECIAL: "特殊",
        }.get(self.attribute, "")

        # Special handling for certain products
        if self.attribute == ProductAttribute.XINGFU and self.size_kg == 0:
            return "幸福丸"  # Special product
        
        # For flow products with size
        if self.delivery_method == DeliveryMethod.FLOW and self.size_kg > 0:
            if attr_name:
                return f"流量{attr_name}{self.size_kg}公斤"
            else:
                return f"流量{self.size_kg}公斤"
        
        # For regular cylinder products
        if attr_name:
            if self.delivery_method == DeliveryMethod.CYLINDER:
                return f"{attr_name}{self.size_kg}"  # e.g., "營20" or "好運16"
            else:
                return f"{attr_name}{self.size_kg}公斤{method_name}"
        else:
            return f"{self.size_kg}KG" if self.size_kg else method_name

    def generate_sku(self):
        """Generate SKU based on product attributes"""
        method_code = "C" if self.delivery_method == DeliveryMethod.CYLINDER else "F"
        attr_code = {
            ProductAttribute.REGULAR: "R",
            ProductAttribute.COMMERCIAL: "CM",
            ProductAttribute.HAOYUN: "H",
            ProductAttribute.PINGAN: "P",
            ProductAttribute.XINGFU: "X",
            ProductAttribute.SPECIAL: "SP",
        }.get(self.attribute, "R")

        # Handle special case for products without size
        if self.size_kg == 0:
            return f"GAS-{method_code}00-{attr_code}"
        
        return f"GAS-{method_code}{self.size_kg:02d}-{attr_code}"
