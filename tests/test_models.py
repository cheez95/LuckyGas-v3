"""
Test database models and schemas
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

import pytest
from datetime import datetime
from app.models.user import User, UserRole
from app.models.customer import Customer
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.core.security import get_password_hash, verify_password


class TestUserModel:
    def test_user_roles(self):
        """Test all user roles are defined correctly"""
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.OFFICE_STAFF.value == "office_staff"
        assert UserRole.DRIVER.value == "driver"
        assert UserRole.CUSTOMER.value == "customer"
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)


class TestUserSchemas:
    def test_user_create_validation(self):
        """Test user creation schema validation"""
        # Valid user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "password123",
            "role": UserRole.OFFICE_STAFF
        }
        user = UserCreate(**user_data)
        assert user.email == "test@example.com"
        
        # Invalid password (too short)
        with pytest.raises(ValueError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                full_name="Test User",
                password="short",
                role=UserRole.OFFICE_STAFF
            )
        assert "密碼長度必須至少8個字符" in str(exc_info.value)


class TestCustomerModel:
    def test_customer_fields(self):
        """Test customer model has all required fields"""
        customer_fields = [
            'customer_code', 'invoice_title', 'short_name', 'address',
            'cylinders_50kg', 'cylinders_20kg', 'cylinders_16kg',
            'delivery_time_start', 'delivery_time_end', 'area',
            'avg_daily_usage', 'max_cycle_days', 'can_delay_days',
            'is_subscription', 'is_terminated', 'needs_same_day_delivery'
        ]
        
        # Check all fields exist in Customer model
        customer_columns = [col.name for col in Customer.__table__.columns]
        for field in customer_fields:
            assert field in customer_columns


class TestCustomerSchemas:
    def test_time_validation(self):
        """Test delivery time format validation"""
        # Valid time format
        customer_data = {
            "customer_code": "C001",
            "short_name": "測試客戶",
            "address": "台北市信義區",
            "delivery_time_start": "08:00",
            "delivery_time_end": "17:00"
        }
        customer = CustomerCreate(**customer_data)
        assert customer.delivery_time_start == "08:00"
        
        # Invalid time format
        with pytest.raises(ValueError) as exc_info:
            CustomerCreate(
                customer_code="C002",
                short_name="測試客戶2",
                address="台北市大安區",
                delivery_time_start="8:00"  # Missing leading zero
            )
        assert "時間格式必須為 HH:MM" in str(exc_info.value)


class TestTaiwanSpecificFormats:
    def test_chinese_characters_in_fields(self):
        """Test that Chinese characters are properly handled"""
        customer = CustomerCreate(
            customer_code="1400103",
            invoice_title="豐年國小",
            short_name="豐年附幼",
            address="臺東市中興路三段320號",
            customer_type="學校"
        )
        
        assert customer.invoice_title == "豐年國小"
        assert customer.address == "臺東市中興路三段320號"
        assert customer.customer_type == "學校"
    
    def test_taiwan_address_format(self):
        """Test Taiwan address formats"""
        addresses = [
            "950 臺東市中興路三段320號",
            "100 臺北市中正區重慶南路一段122號",
            "407 臺中市西屯區臺灣大道三段99號"
        ]
        
        for addr in addresses:
            customer = CustomerCreate(
                customer_code=f"C{addresses.index(addr)}",
                short_name="測試",
                address=addr
            )
            assert customer.address == addr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])