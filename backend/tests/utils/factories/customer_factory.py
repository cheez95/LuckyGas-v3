"""
Customer factory for test data generation
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.models.customer import Customer

from .base import BaseFactory


class CustomerFactory(BaseFactory):
    """Factory for creating Customer instances"""

    model = Customer

    async def get_default_data(self) -> Dict[str, Any]:
        """Get default customer data"""
        customer_types = ["residential", "business", "restaurant", "factory", "store"]
        customer_type = self.fake.random_element(customer_types)
        is_corporate = customer_type in ["business", "restaurant", "factory"]

        return {
            "customer_code": f"C{self.random_string(6, '0123456789')}",
            "short_name": self.fake.company() if is_corporate else self.fake.name(),
            "invoice_title": self.fake.company() if is_corporate else self.fake.name(),
            "tax_id": self.random_tax_id() if is_corporate else "",
            "address": self.random_address(),
            "phone1": self.random_phone(),
            "phone2": self.random_landline() if is_corporate else "",
            "contact_person": self.fake.name(),
            "delivery_address": self.random_address(),
            "area": self.fake.random_element(
                [
                    "信義區",
                    "大安區",
                    "中山區",
                    "松山區",
                    "內湖區",
                    "南港區",
                    "文山區",
                    "萬華區",
                ]
            ),
            "is_corporate": is_corporate,
            "customer_type": customer_type,
            "is_active": True,
            "is_terminated": False,
            "is_subscription": self.fake.boolean(chance_of_getting_true=30),
            "credit_limit": self.random_amount(0, 200000) if is_corporate else 0,
            "current_credit": 0.0,
            "payment_terms": (
                self.fake.random_element([0, 30, 45, 60]) if is_corporate else 0
            ),
            "bank_name": (
                self.fake.random_element(
                    ["台灣銀行", "合作金庫", "第一銀行", "華南銀行", "彰化銀行"]
                )
                if is_corporate
                else ""
            ),
            "bank_account": (
                f"{self.random_string(14, '0123456789')}" if is_corporate else ""
            ),
            "notes": "",
            "created_by": 1,
            "updated_by": 1,
        }

    async def create_residential(self, **kwargs) -> Customer:
        """Create a residential customer"""
        data = {
            "customer_type": "residential",
            "is_corporate": False,
            "credit_limit": 0,
            "payment_terms": 0,
            "short_name": self.fake.name(),
            "invoice_title": self.fake.name(),
            "tax_id": "",
            "bank_name": "",
            "bank_account": "",
        }
        data.update(kwargs)
        return await self.create(**data)

    async def create_business(self, **kwargs) -> Customer:
        """Create a business customer"""
        company_name = self.fake.company()
        data = {
            "customer_type": "business",
            "is_corporate": True,
            "short_name": company_name,
            "invoice_title": f"{company_name}股份有限公司",
            "tax_id": self.random_tax_id(),
            "credit_limit": self.random_amount(50000, 200000),
            "payment_terms": self.fake.random_element([30, 45, 60]),
            "bank_name": self.fake.random_element(["台灣銀行", "合作金庫", "第一銀行"]),
            "bank_account": self.random_string(14, "0123456789"),
        }
        data.update(kwargs)
        return await self.create(**data)

    async def create_restaurant(self, **kwargs) -> Customer:
        """Create a restaurant customer"""
        restaurant_types = ["餐廳", "小吃店", "火鍋店", "燒烤店", "早餐店"]
        restaurant_name = (
            f"{self.fake.word()}{self.fake.random_element(restaurant_types)}"
        )
        data = {
            "customer_type": "restaurant",
            "is_corporate": True,
            "short_name": restaurant_name,
            "invoice_title": f"{restaurant_name}有限公司",
            "tax_id": self.random_tax_id(),
            "credit_limit": self.random_amount(30000, 150000),
            "payment_terms": self.fake.random_element([30, 45]),
            "is_subscription": True,  # Most restaurants have regular orders
        }
        data.update(kwargs)
        return await self.create(**data)

    async def create_factory(self, **kwargs) -> Customer:
        """Create a factory customer"""
        factory_types = ["工廠", "製造廠", "加工廠", "生產工廠"]
        factory_name = f"{self.fake.word()}{self.fake.random_element(factory_types)}"
        data = {
            "customer_type": "factory",
            "is_corporate": True,
            "short_name": factory_name,
            "invoice_title": f"{factory_name}股份有限公司",
            "tax_id": self.random_tax_id(),
            "credit_limit": self.random_amount(100000, 500000),
            "payment_terms": 60,
            "notes": "大型工業客戶，需要穩定供應",
        }
        data.update(kwargs)
        return await self.create(**data)

    async def create_with_credit(self, credit_used: float, **kwargs) -> Customer:
        """Create a customer with existing credit usage"""
        credit_limit = credit_used + self.random_amount(10000, 50000)
        data = {
            "credit_limit": credit_limit,
            "current_credit": credit_used,
            "is_corporate": True,
            "payment_terms": 30,
        }
        data.update(kwargs)
        return await self.create(**data)

    async def create_inactive(self, **kwargs) -> Customer:
        """Create an inactive customer"""
        data = {"is_active": False}
        data.update(kwargs)
        return await self.create(**data)

    async def create_terminated(self, **kwargs) -> Customer:
        """Create a terminated customer"""
        data = {
            "is_terminated": True,
            "is_active": False,
            "termination_date": datetime.now()
            - timedelta(days=self.fake.random_int(1, 365)),
            "termination_reason": self.fake.random_element(
                ["搬遷", "結業", "改用其他供應商", "長期未訂購"]
            ),
        }
        data.update(kwargs)
        return await self.create(**data)

    async def create_subscription(self, **kwargs) -> Customer:
        """Create a subscription customer"""
        data = {
            "is_subscription": True,
            "subscription_frequency": self.fake.random_element(
                ["weekly", "biweekly", "monthly"]
            ),
            "subscription_day": (
                self.fake.random_int(1, 7)
                if kwargs.get("subscription_frequency") == "weekly"
                else self.fake.random_int(1, 28)
            ),
            "notes": "定期配送客戶",
        }
        data.update(kwargs)
        return await self.create(**data)
