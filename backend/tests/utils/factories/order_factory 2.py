"""
Order factory for test data generation
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.models.order import Order, OrderStatus, PaymentStatus
from .base import BaseFactory


class OrderFactory(BaseFactory):
    """Factory for creating Order instances"""
    
    model = Order
    
    # Standard gas cylinder prices
    PRODUCT_PRICES = {
        "50kg": 2500.0,
        "20kg": 1000.0,
        "16kg": 800.0,
        "10kg": 500.0,
        "4kg": 200.0
    }
    
    async def get_default_data(self) -> Dict[str, Any]:
        """Get default order data"""
        # Generate random quantities
        qty_50kg = self.fake.random_int(0, 3)
        qty_20kg = self.fake.random_int(0, 5)
        qty_16kg = self.fake.random_int(0, 2)
        qty_10kg = self.fake.random_int(0, 2)
        qty_4kg = self.fake.random_int(0, 4)
        
        # Ensure at least one product is ordered
        if all(q == 0 for q in [qty_50kg, qty_20kg, qty_16kg, qty_10kg, qty_4kg]):
            qty_20kg = 1
        
        # Calculate amounts
        total_amount = (
            qty_50kg * self.PRODUCT_PRICES["50kg"] +
            qty_20kg * self.PRODUCT_PRICES["20kg"] +
            qty_16kg * self.PRODUCT_PRICES["16kg"] +
            qty_10kg * self.PRODUCT_PRICES["10kg"] +
            qty_4kg * self.PRODUCT_PRICES["4kg"]
        )
        
        discount_amount = 0
        if total_amount > 10000:
            discount_amount = round(total_amount * 0.05, 2)  # 5% discount for large orders
        
        final_amount = total_amount - discount_amount
        
        return {
            "order_number": f"ORD-{datetime.now().strftime('%Y%m%d')}-{self.random_string(6, '0123456789')}",
            "customer_id": 1,  # Should be overridden
            "scheduled_date": datetime.now() + timedelta(days=self.fake.random_int(1, 7)),
            "status": OrderStatus.PENDING,
            "payment_status": PaymentStatus.UNPAID,
            "qty_50kg": qty_50kg,
            "qty_20kg": qty_20kg,
            "qty_16kg": qty_16kg,
            "qty_10kg": qty_10kg,
            "qty_4kg": qty_4kg,
            "total_amount": total_amount,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "delivery_address": self.random_address(),
            "delivery_notes": self.fake.random_element([
                "", 
                "請放置於後門", 
                "請先電話通知", 
                "週末才有人在家", 
                "請小心輕放",
                "警衛室代收"
            ]),
            "is_urgent": self.fake.boolean(chance_of_getting_true=20),
            "payment_method": self.fake.random_element(["cash", "credit_card", "bank_transfer", "monthly_billing"]),
            "created_by": 1,
            "updated_by": 1,
            "route_id": None,
            "driver_id": None,
            "delivery_sequence": None,
            "actual_delivery_time": None,
            "signature_url": None,
            "photo_url": None,
            "cancelled_reason": None,
            "invoice_number": None,
            "invoice_date": None
        }
    
    async def create_pending(self, customer_id: int, **kwargs) -> Order:
        """Create a pending order"""
        data = {
            "customer_id": customer_id,
            "status": OrderStatus.PENDING,
            "payment_status": PaymentStatus.UNPAID
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_confirmed(self, customer_id: int, **kwargs) -> Order:
        """Create a confirmed order"""
        data = {
            "customer_id": customer_id,
            "status": OrderStatus.CONFIRMED,
            "payment_status": PaymentStatus.UNPAID,
            "confirmed_at": datetime.now(),
            "confirmed_by": 1
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_in_delivery(self, customer_id: int, driver_id: int, **kwargs) -> Order:
        """Create an order in delivery"""
        data = {
            "customer_id": customer_id,
            "status": OrderStatus.IN_DELIVERY,
            "payment_status": PaymentStatus.UNPAID,
            "driver_id": driver_id,
            "route_id": 1,
            "delivery_sequence": self.fake.random_int(1, 20),
            "dispatched_at": datetime.now()
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_delivered(self, customer_id: int, driver_id: int, **kwargs) -> Order:
        """Create a delivered order"""
        delivery_time = datetime.now() - timedelta(hours=self.fake.random_int(1, 48))
        data = {
            "customer_id": customer_id,
            "status": OrderStatus.DELIVERED,
            "payment_status": PaymentStatus.PAID,
            "driver_id": driver_id,
            "route_id": 1,
            "delivery_sequence": self.fake.random_int(1, 20),
            "actual_delivery_time": delivery_time,
            "delivered_at": delivery_time,
            "signature_url": f"/signatures/{self.random_string(32)}.png",
            "photo_url": f"/photos/{self.random_string(32)}.jpg"
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_cancelled(self, customer_id: int, **kwargs) -> Order:
        """Create a cancelled order"""
        data = {
            "customer_id": customer_id,
            "status": OrderStatus.CANCELLED,
            "payment_status": PaymentStatus.CANCELLED,
            "cancelled_at": datetime.now(),
            "cancelled_by": 1,
            "cancelled_reason": self.fake.random_element([
                "客戶要求取消",
                "無人在家",
                "改期配送",
                "重複訂單",
                "庫存不足"
            ])
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_urgent(self, customer_id: int, **kwargs) -> Order:
        """Create an urgent order"""
        data = {
            "customer_id": customer_id,
            "is_urgent": True,
            "scheduled_date": datetime.now() + timedelta(hours=self.fake.random_int(1, 6)),
            "delivery_notes": "緊急訂單，請優先配送"
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_with_specific_products(
        self, 
        customer_id: int,
        qty_50kg: int = 0,
        qty_20kg: int = 0,
        qty_16kg: int = 0,
        qty_10kg: int = 0,
        qty_4kg: int = 0,
        **kwargs
    ) -> Order:
        """Create an order with specific product quantities"""
        total_amount = (
            qty_50kg * self.PRODUCT_PRICES["50kg"] +
            qty_20kg * self.PRODUCT_PRICES["20kg"] +
            qty_16kg * self.PRODUCT_PRICES["16kg"] +
            qty_10kg * self.PRODUCT_PRICES["10kg"] +
            qty_4kg * self.PRODUCT_PRICES["4kg"]
        )
        
        discount_amount = kwargs.get("discount_amount", 0)
        if "discount_percentage" in kwargs:
            discount_amount = round(total_amount * kwargs["discount_percentage"] / 100, 2)
        
        data = {
            "customer_id": customer_id,
            "qty_50kg": qty_50kg,
            "qty_20kg": qty_20kg,
            "qty_16kg": qty_16kg,
            "qty_10kg": qty_10kg,
            "qty_4kg": qty_4kg,
            "total_amount": total_amount,
            "discount_amount": discount_amount,
            "final_amount": total_amount - discount_amount
        }
        data.update(kwargs)
        return await self.create(**data)
    
    async def create_batch_for_route(
        self, 
        customer_ids: List[int],
        driver_id: int,
        route_id: int,
        scheduled_date: datetime = None,
        **kwargs
    ) -> List[Order]:
        """Create multiple orders for a route"""
        if not scheduled_date:
            scheduled_date = datetime.now() + timedelta(days=1)
        
        orders = []
        for i, customer_id in enumerate(customer_ids):
            order = await self.create_confirmed(
                customer_id=customer_id,
                driver_id=driver_id,
                route_id=route_id,
                delivery_sequence=i + 1,
                scheduled_date=scheduled_date,
                **kwargs
            )
            orders.append(order)
        
        return orders