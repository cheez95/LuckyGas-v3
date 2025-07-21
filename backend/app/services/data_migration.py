"""
Data migration service for importing historical data
"""
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import logging
import re
from typing import Optional, Dict, Any

from app.core.database import get_async_session
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.delivery import DeliveryHistory
from app.models.gas_product import GasProduct, CylinderType
from app.models.customer_inventory import CustomerInventory

logger = logging.getLogger(__name__)


class DataMigrationService:
    """Service for migrating historical data from Excel files"""
    
    def __init__(self):
        self.customer_mapping: Dict[str, int] = {}  # Map customer code to ID
        self.product_mapping: Dict[str, int] = {}   # Map product type to ID
    
    async def ensure_default_products(self, db: AsyncSession):
        """Ensure default gas products exist in database"""
        default_products = [
            {
                "display_name": "50公斤桶裝瓦斯",
                "cylinder_type": CylinderType.KG_50,
                "unit_price": 2500,
                "deposit_amount": 1000,
                "is_available": True
            },
            {
                "display_name": "20公斤桶裝瓦斯",
                "cylinder_type": CylinderType.KG_20,
                "unit_price": 1200,
                "deposit_amount": 500,
                "is_available": True
            },
            {
                "display_name": "16公斤桶裝瓦斯",
                "cylinder_type": CylinderType.KG_16,
                "unit_price": 1000,
                "deposit_amount": 400,
                "is_available": True
            },
            {
                "display_name": "10公斤桶裝瓦斯",
                "cylinder_type": CylinderType.KG_10,
                "unit_price": 700,
                "deposit_amount": 300,
                "is_available": True
            },
            {
                "display_name": "4公斤桶裝瓦斯",
                "cylinder_type": CylinderType.KG_4,
                "unit_price": 350,
                "deposit_amount": 200,
                "is_available": True
            }
        ]
        
        for product_data in default_products:
            # Check if product exists
            result = await db.execute(
                select(GasProduct).where(GasProduct.cylinder_type == product_data["cylinder_type"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                product = GasProduct(**product_data)
                db.add(product)
                await db.flush()
                self.product_mapping[product_data["cylinder_type"]] = product.id
                logger.info(f"Created gas product: {product_data['display_name']}")
            else:
                self.product_mapping[existing.cylinder_type] = existing.id
    
    async def import_customers_from_excel(self, file_path: str):
        """Import customers from Excel file"""
        async for db in get_async_session():
            try:
                # Ensure products exist first
                await self.ensure_default_products(db)
                
                # Read Excel file
                df = pd.read_excel(file_path)
                logger.info(f"Reading {len(df)} customers from {file_path}")
                
                imported_count = 0
                skipped_count = 0
                
                for _, row in df.iterrows():
                    try:
                        # Extract customer code (handle various formats)
                        customer_code = str(row.get('客戶代號', row.get('客戶編號', ''))).strip()
                        if not customer_code:
                            logger.warning(f"Skipping row without customer code: {row}")
                            skipped_count += 1
                            continue
                        
                        # Check if customer already exists
                        result = await db.execute(
                            select(Customer).where(Customer.customer_code == customer_code)
                        )
                        existing = result.scalar_one_or_none()
                        
                        if existing:
                            self.customer_mapping[customer_code] = existing.id
                            skipped_count += 1
                            continue
                        
                        # Parse customer data
                        customer_data = {
                            "customer_code": customer_code,
                            "short_name": str(row.get('簡稱', row.get('客戶簡稱', ''))).strip() or customer_code,
                            "invoice_title": str(row.get('發票抬頭', row.get('公司名稱', ''))).strip() or "個人",
                            "tax_id": str(row.get('統編', row.get('統一編號', ''))).strip() or None,
                            "address": str(row.get('地址', row.get('送貨地址', ''))).strip(),
                            "phone1": self._clean_phone(row.get('電話1', row.get('電話', ''))),
                            "phone2": self._clean_phone(row.get('電話2', row.get('手機', ''))),
                            "contact_person": str(row.get('聯絡人', '')).strip() or None,
                            "area": self._extract_area(str(row.get('地址', ''))),
                            "delivery_notes": str(row.get('備註', '')).strip() or None,
                            "is_corporate": bool(row.get('統編', row.get('統一編號', ''))),
                            "is_terminated": False,
                            "created_at": datetime.utcnow()
                        }
                        
                        # Create customer
                        customer = Customer(**customer_data)
                        db.add(customer)
                        await db.flush()
                        
                        self.customer_mapping[customer_code] = customer.id
                        
                        # Create initial inventory if specified
                        inventory_cols = {
                            '50kg': CylinderType.KG_50,
                            '20kg': CylinderType.KG_20,
                            '16kg': CylinderType.KG_16,
                            '10kg': CylinderType.KG_10,
                            '4kg': CylinderType.KG_4
                        }
                        
                        for col, cylinder_type in inventory_cols.items():
                            qty = row.get(f'{col}瓦斯桶', 0) or row.get(f'{col}', 0) or 0
                            if qty > 0:
                                product_id = self.product_mapping.get(cylinder_type)
                                if product_id:
                                    inventory = CustomerInventory(
                                        customer_id=customer.id,
                                        gas_product_id=product_id,
                                        quantity_owned=int(qty),
                                        quantity_rented=0,
                                        is_active=True
                                    )
                                    inventory.update_total()
                                    db.add(inventory)
                        
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing customer row: {e}")
                        logger.debug(f"Row data: {row}")
                        skipped_count += 1
                
                await db.commit()
                logger.info(f"Imported {imported_count} customers, skipped {skipped_count}")
                
            except Exception as e:
                logger.error(f"Error importing customers: {e}")
                await db.rollback()
                raise
    
    async def import_delivery_history_from_excel(self, file_path: str):
        """Import delivery history from Excel file"""
        async for db in get_async_session():
            try:
                # Read Excel file
                df = pd.read_excel(file_path)
                logger.info(f"Reading {len(df)} delivery records from {file_path}")
                
                imported_count = 0
                skipped_count = 0
                
                for _, row in df.iterrows():
                    try:
                        # Extract customer code
                        customer_code = str(row.get('客戶代號', row.get('客戶編號', ''))).strip()
                        if not customer_code or customer_code not in self.customer_mapping:
                            logger.warning(f"Skipping delivery for unknown customer: {customer_code}")
                            skipped_count += 1
                            continue
                        
                        customer_id = self.customer_mapping[customer_code]
                        
                        # Parse delivery date
                        delivery_date = self._parse_date(row.get('送貨日期', row.get('配送日期', '')))
                        if not delivery_date:
                            logger.warning(f"Skipping delivery without valid date")
                            skipped_count += 1
                            continue
                        
                        # Create order record for historical delivery
                        order_data = {
                            "order_number": f"HIST-{delivery_date.strftime('%Y%m%d')}-{customer_code}",
                            "customer_id": customer_id,
                            "scheduled_date": delivery_date,
                            "status": OrderStatus.DELIVERED,
                            "is_urgent": False,
                            "payment_status": PaymentStatus.PAID,
                            "created_at": delivery_date,
                            "delivered_at": delivery_date
                        }
                        
                        # Parse quantities
                        qty_fields = {
                            'qty_50kg': ['50kg', '50公斤', '50KG'],
                            'qty_20kg': ['20kg', '20公斤', '20KG'],
                            'qty_16kg': ['16kg', '16公斤', '16KG'],
                            'qty_10kg': ['10kg', '10公斤', '10KG'],
                            'qty_4kg': ['4kg', '4公斤', '4KG']
                        }
                        
                        total_amount = 0
                        for field, possible_cols in qty_fields.items():
                            qty = 0
                            for col in possible_cols:
                                if col in row:
                                    qty = int(row[col] or 0)
                                    break
                            order_data[field] = qty
                            
                            # Calculate amount
                            if field == 'qty_50kg':
                                total_amount += qty * 2500
                            elif field == 'qty_20kg':
                                total_amount += qty * 1200
                            elif field == 'qty_16kg':
                                total_amount += qty * 1000
                            elif field == 'qty_10kg':
                                total_amount += qty * 700
                            elif field == 'qty_4kg':
                                total_amount += qty * 350
                        
                        order_data['total_amount'] = total_amount
                        order_data['final_amount'] = total_amount
                        
                        # Skip if no quantities
                        if total_amount == 0:
                            logger.warning(f"Skipping delivery with no quantities")
                            skipped_count += 1
                            continue
                        
                        # Check if order already exists
                        result = await db.execute(
                            select(Order).where(Order.order_number == order_data["order_number"])
                        )
                        existing = result.scalar_one_or_none()
                        
                        if existing:
                            skipped_count += 1
                            continue
                        
                        # Create order
                        order = Order(**order_data)
                        db.add(order)
                        await db.flush()
                        
                        # Create delivery history record
                        history = DeliveryHistory(
                            order_id=order.id,
                            customer_id=customer_id,
                            delivered_at=delivery_date,
                            qty_50kg=order.qty_50kg,
                            qty_20kg=order.qty_20kg,
                            qty_16kg=order.qty_16kg,
                            qty_10kg=order.qty_10kg,
                            qty_4kg=order.qty_4kg,
                            total_amount=total_amount,
                            payment_received=total_amount,
                            is_paid=True
                        )
                        db.add(history)
                        
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing delivery row: {e}")
                        logger.debug(f"Row data: {row}")
                        skipped_count += 1
                
                await db.commit()
                logger.info(f"Imported {imported_count} delivery records, skipped {skipped_count}")
                
            except Exception as e:
                logger.error(f"Error importing delivery history: {e}")
                await db.rollback()
                raise
    
    def _clean_phone(self, phone: Any) -> Optional[str]:
        """Clean and format phone number"""
        if not phone:
            return None
        
        phone_str = str(phone).strip()
        # Remove common separators
        phone_str = re.sub(r'[-\s\(\)]', '', phone_str)
        
        # Handle Taiwan phone formats
        if phone_str.startswith('09') and len(phone_str) == 10:
            # Mobile: 09XX-XXX-XXX
            return f"{phone_str[:4]}-{phone_str[4:7]}-{phone_str[7:]}"
        elif phone_str.startswith('0') and len(phone_str) in [9, 10]:
            # Landline: 0X-XXXX-XXXX or 0XX-XXX-XXX
            if len(phone_str) == 9:
                return f"{phone_str[:2]}-{phone_str[2:6]}-{phone_str[6:]}"
            else:
                return f"{phone_str[:3]}-{phone_str[3:6]}-{phone_str[6:]}"
        
        return phone_str
    
    def _extract_area(self, address: str) -> str:
        """Extract area from address"""
        if not address:
            return "未分區"
        
        # Common Taiwan area patterns
        area_patterns = [
            r'([\u4e00-\u9fa5]+區)',  # XX區
            r'([\u4e00-\u9fa5]+鎮)',  # XX鎮
            r'([\u4e00-\u9fa5]+鄉)',  # XX鄉
            r'([\u4e00-\u9fa5]+市)',  # XX市
        ]
        
        for pattern in area_patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(1)
        
        return "未分區"
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_value:
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y.%m.%d',
                '%Y年%m月%d日',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_value.strip(), fmt)
                except ValueError:
                    continue
        
        # Try pandas datetime conversion
        try:
            return pd.to_datetime(date_value)
        except:
            pass
        
        return None