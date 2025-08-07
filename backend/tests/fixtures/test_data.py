"""
Test Data Fixtures for Lucky Gas v3
Provides sample data for testing including customer migration scenarios
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List


class TestDataFixtures:
    """Centralized test data fixtures"""

    @staticmethod
    def get_sample_customers() -> List[Dict[str, Any]]:
        """Get sample customer data for testing"""
        return [
            {
                "customer_code": "C001",
                "short_name": "王小明瓦斯行",
                "invoice_title": "王小明瓦斯行有限公司",
                "tax_id": "53212539",
                "address": "台北市信義區信義路五段123號",
                "phone1": "02 - 27584321",
                "phone2": "0912 - 345 - 678",
                "contact_person": "王小明",
                "delivery_address": "台北市信義區信義路五段123號1樓",
                "area": "信義區",
                "is_corporate": True,
                "customer_type": "business",
                "credit_limit": 50000.0,
                "current_credit": 15000.0,
                "payment_terms": 30,
                "notes": "老客戶，信用良好",
            },
            {
                "customer_code": "C002",
                "short_name": "陳太太",
                "invoice_title": "陳美惠",
                "tax_id": "",
                "address": "台北市大安區復興南路二段45巷8號3樓",
                "phone1": "0933 - 456 - 789",
                "contact_person": "陳美惠",
                "delivery_address": "台北市大安區復興南路二段45巷8號3樓",
                "area": "大安區",
                "is_corporate": False,
                "customer_type": "residential",
                "credit_limit": 0.0,
                "current_credit": 0.0,
                "payment_terms": 0,
                "notes": "週二、週四不在家",
            },
            {
                "customer_code": "C003",
                "short_name": "幸福餐廳",
                "invoice_title": "幸福餐飲股份有限公司",
                "tax_id": "28457693",
                "address": "台北市中山區民生東路三段88號",
                "phone1": "02 - 25147896",
                "phone2": "02 - 25147897",
                "contact_person": "李經理",
                "delivery_address": "台北市中山區民生東路三段88號B1",
                "area": "中山區",
                "is_corporate": True,
                "customer_type": "restaurant",
                "credit_limit": 100000.0,
                "current_credit": 35000.0,
                "payment_terms": 45,
                "notes": "大型餐廳，每週需求量大，需優先配送",
            },
            {
                "customer_code": "C004",
                "short_name": "林先生",
                "invoice_title": "林志成",
                "tax_id": "",
                "address": "新北市板橋區文化路一段268號15樓",
                "phone1": "0922 - 789 - 456",
                "contact_person": "林志成",
                "delivery_address": "新北市板橋區文化路一段268號15樓",
                "area": "板橋區",
                "is_corporate": False,
                "customer_type": "residential",
                "credit_limit": 0.0,
                "current_credit": 0.0,
                "payment_terms": 0,
                "notes": "新客戶，需要門鈴通知",
            },
            {
                "customer_code": "C005",
                "short_name": "快樂工廠",
                "invoice_title": "快樂製造有限公司",
                "tax_id": "16842957",
                "address": "桃園市龜山區文化二路188號",
                "phone1": "03 - 3698741",
                "phone2": "0911 - 222 - 333",
                "contact_person": "張廠長",
                "delivery_address": "桃園市龜山區文化二路188號側門",
                "area": "龜山區",
                "is_corporate": True,
                "customer_type": "factory",
                "credit_limit": 200000.0,
                "current_credit": 85000.0,
                "payment_terms": 60,
                "notes": "工廠客戶，需要大量供應，月結60天",
            },
        ]

    @staticmethod
    def get_sample_orders() -> List[Dict[str, Any]]:
        """Get sample order data for testing"""
        future_date = datetime.now() + timedelta(days=7)
        return [
            {
                "customer_id": 1,
                "scheduled_date": future_date.isoformat(),
                "qty_50kg": 2,
                "qty_20kg": 1,
                "qty_16kg": 0,
                "qty_10kg": 0,
                "qty_4kg": 0,
                "total_amount": 7500.0,
                "discount_amount": 0.0,
                "final_amount": 7500.0,
                "delivery_address": "台北市信義區信義路五段123號1樓",
                "delivery_notes": "請放置於後門",
                "is_urgent": False,
                "payment_method": "monthly_billing",
                "payment_status": "unpaid",
            },
            {
                "customer_id": 2,
                "scheduled_date": (future_date + timedelta(days=1)).isoformat(),
                "qty_50kg": 0,
                "qty_20kg": 0,
                "qty_16kg": 1,
                "qty_10kg": 0,
                "qty_4kg": 2,
                "total_amount": 2200.0,
                "discount_amount": 0.0,
                "final_amount": 2200.0,
                "delivery_address": "台北市大安區復興南路二段45巷8號3樓",
                "delivery_notes": "週二、週四不在家，請週一或週三送",
                "is_urgent": False,
                "payment_method": "cash",
                "payment_status": "unpaid",
            },
            {
                "customer_id": 3,
                "scheduled_date": future_date.isoformat(),
                "qty_50kg": 5,
                "qty_20kg": 3,
                "qty_16kg": 0,
                "qty_10kg": 0,
                "qty_4kg": 0,
                "total_amount": 15900.0,
                "discount_amount": 500.0,
                "final_amount": 15400.0,
                "delivery_address": "台北市中山區民生東路三段88號B1",
                "delivery_notes": "請從後門進入，找李經理",
                "is_urgent": True,
                "payment_method": "monthly_billing",
                "payment_status": "unpaid",
            },
        ]

    @staticmethod
    def get_sample_payment_records() -> List[Dict[str, Any]]:
        """Get sample payment records for testing"""
        return [
            {
                "customer_id": 1,
                "amount": 15000.0,
                "payment_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "payment_method": "bank_transfer",
                "reference_number": "TRF202312150001",
                "notes": "上月帳款",
            },
            {
                "customer_id": 3,
                "amount": 35000.0,
                "payment_date": (datetime.now() - timedelta(days=10)).isoformat(),
                "payment_method": "check",
                "reference_number": "CHK202312100001",
                "notes": "11月份貨款",
            },
            {
                "customer_id": 5,
                "amount": 50000.0,
                "payment_date": (datetime.now() - timedelta(days=15)).isoformat(),
                "payment_method": "bank_transfer",
                "reference_number": "TRF202312050002",
                "notes": "部分付款",
            },
        ]

    @staticmethod
    def get_sample_invoices() -> List[Dict[str, Any]]:
        """Get sample invoice records for testing"""
        return [
            {
                "order_id": 1,
                "invoice_number": "AA12345678",
                "invoice_date": datetime.now().isoformat(),
                "amount": 7500.0,
                "tax_amount": 375.0,
                "total_amount": 7875.0,
                "buyer_tax_id": "53212539",
                "buyer_name": "王小明瓦斯行有限公司",
                "status": "issued",
            },
            {
                "order_id": 3,
                "invoice_number": "AA12345679",
                "invoice_date": datetime.now().isoformat(),
                "amount": 15400.0,
                "tax_amount": 770.0,
                "total_amount": 16170.0,
                "buyer_tax_id": "28457693",
                "buyer_name": "幸福餐飲股份有限公司",
                "status": "issued",
            },
        ]

    @staticmethod
    def get_migration_test_scenarios() -> List[Dict[str, Any]]:
        """Get customer migration test scenarios"""
        return [
            {
                "scenario": "simple_migration",
                "description": "Basic customer data migration",
                "customer_count": 5,
                "expected_duration": 2,  # seconds
                "validation_rules": [
                    "all_fields_migrated",
                    "phone_format_correct",
                    "address_valid",
                    "credit_limit_preserved",
                ],
            },
            {
                "scenario": "bulk_migration",
                "description": "Large batch customer migration",
                "customer_count": 100,
                "expected_duration": 30,  # seconds
                "validation_rules": [
                    "no_duplicates",
                    "all_records_processed",
                    "error_rate_below_1_percent",
                ],
            },
            {
                "scenario": "migration_with_orders",
                "description": "Customer migration with order history",
                "customer_count": 10,
                "orders_per_customer": 5,
                "expected_duration": 10,  # seconds
                "validation_rules": [
                    "customer_order_relationship_preserved",
                    "order_totals_accurate",
                    "payment_history_linked",
                ],
            },
            {
                "scenario": "migration_rollback",
                "description": "Test migration rollback on error",
                "customer_count": 20,
                "inject_error_at": 15,  # Inject error at 15th record
                "expected_behavior": "full_rollback",
                "validation_rules": [
                    "no_partial_data",
                    "original_state_restored",
                    "error_logged",
                ],
            },
            {
                "scenario": "encoding_issues",
                "description": "Handle various character encodings",
                "test_data": [
                    {"name": "測試客戶", "encoding": "utf - 8"},
                    {"name": "测试客户", "encoding": "gb2312"},
                    {"name": "テスト顧客", "encoding": "shift - jis"},
                ],
                "expected_behavior": "convert_to_utf8",
                "validation_rules": ["all_characters_readable", "no_data_corruption"],
            },
        ]

    @staticmethod
    def get_chaos_test_data() -> Dict[str, Any]:
        """Get data specifically for chaos engineering tests"""
        return {
            "high_load_customers": [
                {
                    "customer_code": f"LOAD{i:04d}",
                    "short_name": f"負載測試客戶{i}",
                    "address": f"測試地址{i}號",
                    "phone1": f"0900{i:06d}",
                    "area": "測試區",
                }
                for i in range(1000)  # 1000 customers for load testing
            ],
            "concurrent_orders": [
                {
                    "customer_id": (i % 100) + 1,  # Distribute among 100 customers
                    "scheduled_date": (
                        datetime.now() + timedelta(days=i % 7)
                    ).isoformat(),
                    "qty_50kg": (i % 5) + 1,
                    "payment_method": "cash" if i % 2 == 0 else "monthly_billing",
                }
                for i in range(500)  # 500 concurrent orders
            ],
            "network_test_endpoints": [
                "/api / v1 / health",
                "/api / v1 / customers",
                "/api / v1 / orders",
                "/api / v1 / routes / optimize",
                "/api / v1 / predictions / daily",
            ],
            "resource_limits": {
                "max_memory_mb": 512,
                "max_cpu_percent": 80,
                "max_connections": 100,
                "max_file_descriptors": 1024,
            },
        }


# Export test data generator functions


def generate_customers(count: int) -> List[Dict[str, Any]]:
    """Generate specified number of test customers"""
    base_customers = TestDataFixtures.get_sample_customers()
    customers = []

    for i in range(count):
        base_index = i % len(base_customers)
        customer = base_customers[base_index].copy()
        customer["customer_code"] = f"TEST{i:04d}"
        customer["short_name"] = f"{customer['short_name']}_{i}"
        customers.append(customer)

    return customers


def generate_orders(count: int, customer_ids: List[int]) -> List[Dict[str, Any]]:
    """Generate specified number of test orders"""
    base_orders = TestDataFixtures.get_sample_orders()
    orders = []

    for i in range(count):
        base_index = i % len(base_orders)
        order = base_orders[base_index].copy()
        order["customer_id"] = customer_ids[i % len(customer_ids)]
        order["scheduled_date"] = (
            datetime.now() + timedelta(days=(i % 30))
        ).isoformat()
        orders.append(order)

    return orders
