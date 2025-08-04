"""
Data import service for Lucky Gas.
Handles importing data from CSV, Excel files with validation.
"""

import csv
import io
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

import aiofiles
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.driver import Driver
from app.models.gas_product import GasProduct as Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.customer import CustomerCreate
from app.schemas.gas_product import GasProductCreate as ProductCreate
from app.schemas.order import OrderCreate
from app.schemas.order_item import OrderItemCreate
from app.utils.validators import validate_email, validate_phone_number

logger = logging.getLogger(__name__)


class DataImportError(Exception):
    """Custom exception for data import errors."""

    pass


class ValidationError(DataImportError):
    """Validation error during import."""

    pass


class DataImportService:
    """Service for importing data from various formats."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    async def import_customers(
        self,
        file: BinaryIO,
        file_type: str,
        update_existing: bool = False,
        validate_only: bool = False,
    ) -> Dict[str, Any]:
        """Import customer data from file."""
        self.errors = []
        self.warnings = []

        # Read file based on type
        if file_type == "csv":
            df = self._read_csv(file)
        elif file_type in ["excel", "xlsx", "xls"]:
            df = self._read_excel(file, sheet_name=0)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Validate and map columns
        required_columns = ["客戶名稱", "電話"]
        optional_columns = [
            "地址",
            "區域",
            "客戶類型",
            "信用額度",
            "付款條件",
            "聯絡人",
            "聯絡人電話",
            "電子郵件",
            "統一編號",
            "備註",
        ]

        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")

        # Process each row
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for index, row in df.iterrows():
            try:
                # Clean and validate data
                customer_data = {
                    "name": str(row["客戶名稱"]).strip(),
                    "phone": self._clean_phone(str(row["電話"])),
                    "address": str(row.get("地址", "")).strip() or None,
                    "district": str(row.get("區域", "")).strip() or None,
                    "customer_type": self._map_customer_type(
                        row.get("客戶類型", "individual")
                    ),
                    "credit_limit": self._parse_decimal(row.get("信用額度", 0)),
                    "payment_terms": self._parse_int(row.get("付款條件", 0)),
                    "contact_person": str(row.get("聯絡人", "")).strip() or None,
                    "contact_phone": self._clean_phone(str(row.get("聯絡人電話", "")))
                    or None,
                    "email": str(row.get("電子郵件", "")).strip() or None,
                    "tax_id": str(row.get("統一編號", "")).strip() or None,
                    "notes": str(row.get("備註", "")).strip() or None,
                    "is_active": True,
                }

                # Validate phone
                if not validate_phone_number(customer_data["phone"]):
                    self.errors.append(
                        {
                            "row": index + 2,
                            "field": "電話",
                            "value": row["電話"],
                            "error": "Invalid phone number format",
                        }
                    )
                    continue

                # Validate email if provided
                if customer_data["email"] and not validate_email(
                    customer_data["email"]
                ):
                    self.errors.append(
                        {
                            "row": index + 2,
                            "field": "電子郵件",
                            "value": row["電子郵件"],
                            "error": "Invalid email format",
                        }
                    )
                    customer_data["email"] = None

                if validate_only:
                    continue

                # Check if customer exists
                existing = await self.db.execute(
                    select(Customer).where(Customer.phone == customer_data["phone"])
                )
                existing_customer = existing.scalar_one_or_none()

                if existing_customer:
                    if update_existing:
                        # Update existing customer
                        for key, value in customer_data.items():
                            if value is not None:
                                setattr(existing_customer, key, value)
                        updated_count += 1
                    else:
                        self.warnings.append(
                            {
                                "row": index + 2,
                                "message": f"Customer with phone {customer_data['phone']} already exists",
                                "action": "skipped",
                            }
                        )
                        skipped_count += 1
                else:
                    # Create new customer
                    customer = Customer(**customer_data)
                    self.db.add(customer)
                    created_count += 1

            except Exception as e:
                self.errors.append({"row": index + 2, "error": str(e)})

        if not validate_only:
            try:
                await self.db.commit()
            except IntegrityError as e:
                await self.db.rollback()
                raise DataImportError(f"Database integrity error: {str(e)}")

        return {
            "total_rows": len(df),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "validate_only": validate_only,
        }

    async def import_products(
        self,
        file: BinaryIO,
        file_type: str,
        update_existing: bool = False,
        validate_only: bool = False,
    ) -> Dict[str, Any]:
        """Import product data from file."""
        self.errors = []
        self.warnings = []

        # Read file
        if file_type == "csv":
            df = self._read_csv(file)
        elif file_type in ["excel", "xlsx", "xls"]:
            df = self._read_excel(file, sheet_name=0)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Validate columns
        required_columns = ["產品代碼", "產品名稱", "單價"]
        optional_columns = [
            "類別",
            "規格",
            "單位",
            "成本",
            "庫存量",
            "最低庫存",
            "描述",
        ]

        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")

        # Process each row
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for index, row in df.iterrows():
            try:
                product_data = {
                    "code": str(row["產品代碼"]).strip(),
                    "name": str(row["產品名稱"]).strip(),
                    "category": str(row.get("類別", "gas")).strip(),
                    "specification": str(row.get("規格", "")).strip() or None,
                    "unit": str(row.get("單位", "桶")).strip(),
                    "unit_price": self._parse_decimal(row["單價"]),
                    "cost": self._parse_decimal(row.get("成本", 0)),
                    "stock_quantity": self._parse_int(row.get("庫存量", 0)),
                    "minimum_stock": self._parse_int(row.get("最低庫存", 0)),
                    "description": str(row.get("描述", "")).strip() or None,
                    "is_active": True,
                }

                # Validate price
                if product_data["unit_price"] <= 0:
                    self.errors.append(
                        {
                            "row": index + 2,
                            "field": "單價",
                            "value": row["單價"],
                            "error": "Price must be greater than 0",
                        }
                    )
                    continue

                if validate_only:
                    continue

                # Check if product exists
                existing = await self.db.execute(
                    select(Product).where(Product.code == product_data["code"])
                )
                existing_product = existing.scalar_one_or_none()

                if existing_product:
                    if update_existing:
                        for key, value in product_data.items():
                            if value is not None:
                                setattr(existing_product, key, value)
                        updated_count += 1
                    else:
                        self.warnings.append(
                            {
                                "row": index + 2,
                                "message": f"Product with code {product_data['code']} already exists",
                                "action": "skipped",
                            }
                        )
                        skipped_count += 1
                else:
                    product = Product(**product_data)
                    self.db.add(product)
                    created_count += 1

            except Exception as e:
                self.errors.append({"row": index + 2, "error": str(e)})

        if not validate_only:
            try:
                await self.db.commit()
            except IntegrityError as e:
                await self.db.rollback()
                raise DataImportError(f"Database integrity error: {str(e)}")

        return {
            "total_rows": len(df),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "validate_only": validate_only,
        }

    async def import_orders(
        self, file: BinaryIO, file_type: str, validate_only: bool = False
    ) -> Dict[str, Any]:
        """Import order data from file."""
        self.errors = []
        self.warnings = []

        # Read file
        if file_type == "csv":
            # For orders, we expect two sheets/files
            raise ValidationError(
                "Order import requires Excel file with two sheets: Orders and Order Items"
            )
        elif file_type in ["excel", "xlsx", "xls"]:
            # Read both sheets
            try:
                orders_df = self._read_excel(file, sheet_name="訂單")
                items_df = self._read_excel(file, sheet_name="訂單明細")
            except Exception as e:
                raise ValidationError(
                    f"Excel file must contain '訂單' and '訂單明細' sheets: {str(e)}"
                )
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Validate order columns
        order_required = ["客戶電話", "配送日期", "配送地址"]
        order_optional = ["付款方式", "備註", "優先級"]

        missing_columns = set(order_required) - set(orders_df.columns)
        if missing_columns:
            raise ValidationError(
                f"Missing required columns in orders sheet: {missing_columns}"
            )

        # Validate item columns
        item_required = ["訂單編號", "產品代碼", "數量"]
        item_optional = ["單價", "折扣"]

        missing_columns = set(item_required) - set(items_df.columns)
        if missing_columns:
            raise ValidationError(
                f"Missing required columns in items sheet: {missing_columns}"
            )

        # Process orders
        created_count = 0
        order_map = {}  # Map row number to order ID

        for index, row in orders_df.iterrows():
            try:
                # Find customer by phone
                phone = self._clean_phone(str(row["客戶電話"]))
                customer_result = await self.db.execute(
                    select(Customer).where(Customer.phone == phone)
                )
                customer = customer_result.scalar_one_or_none()

                if not customer:
                    self.errors.append(
                        {
                            "row": index + 2,
                            "sheet": "訂單",
                            "error": f"Customer with phone {phone} not found",
                        }
                    )
                    continue

                # Parse delivery date
                delivery_date = self._parse_date(row["配送日期"])
                if not delivery_date:
                    self.errors.append(
                        {
                            "row": index + 2,
                            "sheet": "訂單",
                            "field": "配送日期",
                            "error": "Invalid date format",
                        }
                    )
                    continue

                order_data = {
                    "customer_id": customer.id,
                    "delivery_date": delivery_date,
                    "delivery_address": str(row["配送地址"]).strip(),
                    "payment_method": row.get("付款方式", "cash"),
                    "notes": str(row.get("備註", "")).strip() or None,
                    "priority": row.get("優先級", "normal"),
                    "status": "pending",
                    "items": [],
                }

                # Store for later processing with items
                order_map[index + 2] = order_data

            except Exception as e:
                self.errors.append({"row": index + 2, "sheet": "訂單", "error": str(e)})

        # Process order items
        for index, row in items_df.iterrows():
            try:
                order_row = int(row["訂單編號"])
                if order_row not in order_map:
                    self.warnings.append(
                        {
                            "row": index + 2,
                            "sheet": "訂單明細",
                            "message": f"Order row {order_row} not found or has errors",
                            "action": "skipped",
                        }
                    )
                    continue

                # Find product
                product_code = str(row["產品代碼"]).strip()
                product_result = await self.db.execute(
                    select(Product).where(Product.code == product_code)
                )
                product = product_result.scalar_one_or_none()

                if not product:
                    self.errors.append(
                        {
                            "row": index + 2,
                            "sheet": "訂單明細",
                            "error": f"Product with code {product_code} not found",
                        }
                    )
                    continue

                quantity = self._parse_int(row["數量"])
                if quantity <= 0:
                    self.errors.append(
                        {
                            "row": index + 2,
                            "sheet": "訂單明細",
                            "field": "數量",
                            "error": "Quantity must be greater than 0",
                        }
                    )
                    continue

                item_data = {
                    "product_id": product.id,
                    "quantity": quantity,
                    "unit_price": self._parse_decimal(
                        row.get("單價", product.unit_price)
                    ),
                    "discount_amount": self._parse_decimal(row.get("折扣", 0)),
                }

                order_map[order_row]["items"].append(item_data)

            except Exception as e:
                self.errors.append(
                    {"row": index + 2, "sheet": "訂單明細", "error": str(e)}
                )

        # Create orders if not validate only
        if not validate_only:
            for order_data in order_map.values():
                if not order_data["items"]:
                    self.warnings.append(
                        {
                            "message": f"Order for customer {order_data['customer_id']} has no items",
                            "action": "skipped",
                        }
                    )
                    continue

                try:
                    # Calculate totals
                    total_amount = sum(
                        item["quantity"] * item["unit_price"] - item["discount_amount"]
                        for item in order_data["items"]
                    )

                    # Create order
                    order = Order(
                        customer_id=order_data["customer_id"],
                        delivery_date=order_data["delivery_date"],
                        delivery_address=order_data["delivery_address"],
                        payment_method=order_data["payment_method"],
                        notes=order_data["notes"],
                        priority=order_data["priority"],
                        status=order_data["status"],
                        total_amount=total_amount,
                        final_amount=total_amount,  # Can be adjusted later
                    )
                    self.db.add(order)
                    await self.db.flush()

                    # Create order items
                    for item_data in order_data["items"]:
                        item = OrderItem(
                            order_id=order.id,
                            product_id=item_data["product_id"],
                            quantity=item_data["quantity"],
                            unit_price=item_data["unit_price"],
                            discount_amount=item_data["discount_amount"],
                            subtotal=item_data["quantity"] * item_data["unit_price"],
                            total_amount=item_data["quantity"] * item_data["unit_price"]
                            - item_data["discount_amount"],
                        )
                        self.db.add(item)

                    created_count += 1

                except Exception as e:
                    self.errors.append({"error": f"Failed to create order: {str(e)}"})

            try:
                await self.db.commit()
            except IntegrityError as e:
                await self.db.rollback()
                raise DataImportError(f"Database integrity error: {str(e)}")

        return {
            "total_orders": len(order_map),
            "created": created_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "validate_only": validate_only,
        }

    def _read_csv(self, file: BinaryIO) -> pd.DataFrame:
        """Read CSV file into DataFrame."""
        # Detect encoding
        file.seek(0)
        raw_data = file.read()
        file.seek(0)

        # Try different encodings
        encodings = ["utf-8-sig", "utf-8", "big5", "gb2312"]

        for encoding in encodings:
            try:
                file.seek(0)
                df = pd.read_csv(io.BytesIO(raw_data), encoding=encoding)
                return df
            except UnicodeDecodeError:
                continue

        raise ValidationError(
            "Unable to decode CSV file. Please ensure it's saved in UTF-8 encoding."
        )

    def _read_excel(self, file: BinaryIO, sheet_name=0) -> pd.DataFrame:
        """Read Excel file into DataFrame."""
        file.seek(0)
        try:
            df = pd.read_excel(file, sheet_name=sheet_name)
            return df
        except Exception as e:
            raise ValidationError(f"Error reading Excel file: {str(e)}")

    def _clean_phone(self, phone: str) -> str:
        """Clean phone number."""
        # Remove common separators
        phone = (
            phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        )

        # Add country code if missing
        if phone.startswith("09") and len(phone) == 10:
            phone = "+886" + phone[1:]
        elif phone.startswith("0") and len(phone) == 9:
            phone = "+886" + phone

        return phone

    def _parse_decimal(self, value: Any) -> Decimal:
        """Parse decimal value."""
        if pd.isna(value) or value == "":
            return Decimal("0")
        try:
            return Decimal(str(value).replace(",", ""))
        except:
            return Decimal("0")

    def _parse_int(self, value: Any) -> int:
        """Parse integer value."""
        if pd.isna(value) or value == "":
            return 0
        try:
            return int(float(str(value).replace(",", "")))
        except:
            return 0

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse date value."""
        if pd.isna(value):
            return None

        # If it's already a date
        if isinstance(value, (date, datetime)):
            return value.date() if isinstance(value, datetime) else value

        # Try to parse string
        date_str = str(value).strip()
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y年%m月%d日"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue

        return None

    def _map_customer_type(self, value: str) -> str:
        """Map customer type to valid enum value."""
        mapping = {
            "個人": "individual",
            "公司": "company",
            "餐廳": "restaurant",
            "工廠": "factory",
            "其他": "other",
        }

        return mapping.get(value, "individual")
