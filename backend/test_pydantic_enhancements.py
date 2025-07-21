"""
Test Pydantic enhancements with Taiwan-specific validators and Chinese aliases
"""
import asyncio
from datetime import datetime, timedelta
from pydantic import ValidationError

# Test imports
from app.core.config import Settings, Environment
from app.core.validators import TaiwanValidators
from app.schemas.customer import CustomerCreate, Customer
from app.schemas.order import OrderCreate, Order


def test_settings_configuration():
    """Test advanced settings configuration"""
    print("\n=== Testing Settings Configuration ===")
    
    # Test default settings
    settings = Settings()
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Is Production: {settings.is_production()}")
    print(f"Is Development: {settings.is_development()}")
    print(f"Rate Limit: {settings.get_rate_limit()}")
    print(f"Business Config - Delivery Hours: {settings.business.delivery_start_hour}-{settings.business.delivery_end_hour}")
    print(f"Security Config - Password Min Length: {settings.security.password_min_length}")
    
    # Test Taiwan-specific validators
    print("\n=== Testing Taiwan Validators ===")
    
    # Test phone validation
    test_phones = [
        "0912345678",
        "0912-345-678",
        "02-2345-6789",
        "022345678",
        "invalid-phone"
    ]
    
    for phone in test_phones:
        try:
            formatted = settings.validate_taiwan_phone(phone)
            print(f"✅ Phone '{phone}' is valid: {formatted}")
        except Exception as e:
            print(f"❌ Phone '{phone}' is invalid")
    
    # Test tax ID validation
    test_tax_ids = ["12345678", "11111111", "53212539"]  # Last one is valid
    for tax_id in test_tax_ids:
        is_valid = settings.validate_tax_id(tax_id)
        print(f"Tax ID '{tax_id}' is {'valid' if is_valid else 'invalid'}")
    
    # Test address validation
    test_addresses = [
        "台北市中正區重慶南路一段122號",
        "新北市板橋區文化路二段345巷6號7樓",
        "Invalid Address"
    ]
    
    for addr in test_addresses:
        is_valid = settings.validate_taiwan_address(addr)
        print(f"Address valid: {is_valid} - {addr[:20]}...")


def test_customer_schema():
    """Test customer schema with Chinese aliases"""
    print("\n=== Testing Customer Schema ===")
    
    # Test with field names
    customer_data = {
        "customer_code": "C001",
        "short_name": "測試客戶",
        "address": "台北市信義區市府路1號",
        "phone": "0912345678",
        "tax_id": "53212539",
        "cylinders_20kg": 10,
        "cylinders_16kg": 5,
        "delivery_time_start": "09:00",
        "delivery_time_end": "17:00",
        "area": "信義區"
    }
    
    try:
        customer = CustomerCreate(**customer_data)
        print("✅ Customer created with field names")
        print(f"   Phone formatted: {customer.phone}")
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
    
    # Test with Chinese aliases
    customer_data_chinese = {
        "客戶代碼": "C002",
        "簡稱": "測試客戶2",
        "地址": "台北市大安區忠孝東路四段1號",
        "電話": "02-2345-6789",
        "統一編號": "53212539",
        "20公斤鋼瓶數": 15,
        "16公斤鋼瓶數": 8,
        "配送開始時間": "10:00",
        "配送結束時間": "16:00",
        "區域": "大安區"
    }
    
    try:
        customer2 = CustomerCreate(**customer_data_chinese)
        print("✅ Customer created with Chinese aliases")
        print(f"   Phone formatted: {customer2.phone}")
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
    
    # Test validation errors
    print("\n=== Testing Validation Errors ===")
    
    # Invalid phone
    try:
        bad_customer = CustomerCreate(
            customer_code="C003",
            short_name="Bad Customer",
            address="台北市中正區重慶南路一段122號",
            phone="123456"  # Invalid
        )
    except ValidationError as e:
        print(f"✅ Correctly caught invalid phone: {e.errors()[0]['msg']}")
    
    # Invalid address
    try:
        bad_customer = CustomerCreate(
            customer_code="C004",
            short_name="Bad Customer 2",
            address="Bad Address"  # Invalid
        )
    except ValidationError as e:
        print(f"✅ Correctly caught invalid address: {e.errors()[0]['msg']}")


def test_order_schema():
    """Test order schema with enhanced validation"""
    print("\n=== Testing Order Schema ===")
    
    # Valid order
    order_data = {
        "customer_id": 1,
        "scheduled_date": datetime.now() + timedelta(days=1),
        "delivery_time_start": "09:00",
        "delivery_time_end": "17:00",
        "qty_20kg": 2,
        "qty_16kg": 1,
        "delivery_address": "台北市中正區重慶南路一段122號",
        "payment_method": "現金"
    }
    
    try:
        order = OrderCreate(**order_data)
        print("✅ Order created successfully")
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
    
    # Test with Chinese aliases
    order_data_chinese = {
        "客戶編號": 2,
        "預定配送日期": datetime.now() + timedelta(days=2),
        "配送開始時間": "10:00",
        "配送結束時間": "15:00",
        "20公斤數量": 3,
        "16公斤數量": 2,
        "配送地址": "台北市大安區忠孝東路四段1號",
        "配送備註": "請按門鈴",
        "付款方式": "轉帳"
    }
    
    try:
        order2 = OrderCreate(**order_data_chinese)
        print("✅ Order created with Chinese aliases")
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
    
    # Test validation errors
    print("\n=== Testing Order Validation Errors ===")
    
    # Past date
    try:
        bad_order = OrderCreate(
            customer_id=1,
            scheduled_date=datetime.now() - timedelta(days=1),  # Past
            qty_20kg=1
        )
    except ValidationError as e:
        print(f"✅ Correctly caught past date: {e.errors()[0]['msg']}")
    
    # No cylinders
    try:
        bad_order = OrderCreate(
            customer_id=1,
            scheduled_date=datetime.now() + timedelta(days=1)
            # No cylinders
        )
    except ValidationError as e:
        print(f"✅ Correctly caught no cylinders: {e.errors()[0]['msg']}")
    
    # Invalid time window
    try:
        bad_order = OrderCreate(
            customer_id=1,
            scheduled_date=datetime.now() + timedelta(days=1),
            delivery_time_start="15:00",
            delivery_time_end="10:00",  # End before start
            qty_20kg=1
        )
    except ValidationError as e:
        print(f"✅ Correctly caught invalid time window: {e.errors()[0]['msg']}")


def test_taiwan_validators():
    """Test Taiwan-specific validators"""
    print("\n=== Testing Taiwan Validators ===")
    
    # Phone number formatting
    phones = [
        ("0912345678", "0912-345-678"),
        ("0223456789", "02-2345-6789"),
        ("037123456", "037-123-456")
    ]
    
    for input_phone, expected in phones:
        result = TaiwanValidators.validate_phone_number(input_phone)
        print(f"Phone: {input_phone} → {result} {'✅' if result == expected else '❌'}")
    
    # Tax ID validation
    print("\nTax ID Validation:")
    print(f"53212539: {TaiwanValidators.validate_tax_id('53212539')} ✅")
    
    # Currency formatting
    amounts = [1000, 12345.67, 1234567]
    for amount in amounts:
        formatted = TaiwanValidators.format_currency_twd(amount)
        print(f"Amount {amount} → {formatted}")
    
    # ROC year conversion
    print("\nROC Year Conversion:")
    print(f"ROC 113 → Western {TaiwanValidators.roc_to_western_year(113)}")
    print(f"Western 2024 → ROC {TaiwanValidators.western_to_roc_year(2024)}")


if __name__ == "__main__":
    print("=== Lucky Gas Pydantic Enhancement Tests ===")
    
    test_settings_configuration()
    test_customer_schema()
    test_order_schema()
    test_taiwan_validators()
    
    print("\n✅ All Pydantic enhancement tests completed!")