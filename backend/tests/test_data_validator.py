"""
Test cases for data validation framework
"""
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from app.utils.data_validator import DataValidator, validate_migration_data


class TestTaiwanFormatValidators:
    """Test Taiwan-specific format validators."""
    
    def test_validate_taiwan_phone_mobile(self):
        """Test mobile phone validation."""
        validator = DataValidator()
        
        # Valid mobile numbers
        test_cases = [
            ('0912345678', '0912-345-678'),
            ('0912-345-678', '0912-345-678'),
            ('0912 345 678', '0912-345-678'),
            ('0987654321', '0987-654-321'),
        ]
        
        for input_phone, expected in test_cases:
            is_valid, normalized = validator.validate_taiwan_phone(input_phone)
            assert is_valid is True
            assert normalized == expected
        
        # Invalid mobile numbers
        invalid_cases = ['091234567', '09123456789', '0812345678', '123456789']
        for phone in invalid_cases:
            is_valid, _ = validator.validate_taiwan_phone(phone)
            assert is_valid is False
    
    def test_validate_taiwan_phone_landline(self):
        """Test landline phone validation."""
        validator = DataValidator()
        
        # Valid landline numbers
        test_cases = [
            ('0223456789', '02-2345-6789'),  # Taipei
            ('02-2345-6789', '02-2345-6789'),
            ('0423456789', '04-2345-6789'),  # Taichung
            ('0712345678', '07-1234-5678'),  # Kaohsiung
        ]
        
        for input_phone, expected in test_cases:
            is_valid, normalized = validator.validate_taiwan_phone(input_phone)
            assert is_valid is True
            assert normalized == expected
    
    def test_validate_taiwan_address(self):
        """Test Taiwan address validation."""
        validator = DataValidator()
        
        # Valid addresses
        valid_addresses = [
            '台北市大安區和平東路123號',
            '106台北市大安區和平東路二段123號5樓',
            '新北市板橋區文化路一段456號',
            '台中市西屯區台灣大道四段789號',
            '高雄市前鎮區中山二路10號',
        ]
        
        for address in valid_addresses:
            is_valid, issues = validator.validate_taiwan_address(address)
            assert is_valid is True
            assert len(issues) == 0
        
        # Invalid addresses
        invalid_cases = [
            ('', ['Address is empty']),
            ('台北市', ['Missing 區鄉鎮 in address', 'Missing 路街 in address', 'Missing 號 in address']),
            ('123 Main Street', ['Missing 縣市 in address', 'Missing 區鄉鎮 in address', 
                               'Missing 路街 in address', 'Missing 號 in address']),
        ]
        
        for address, expected_issues in invalid_cases:
            is_valid, issues = validator.validate_taiwan_address(address)
            assert is_valid is False
            for expected in expected_issues:
                assert any(expected in issue for issue in issues)
    
    def test_validate_taiwan_tax_id(self):
        """Test Taiwan tax ID validation."""
        validator = DataValidator()
        
        # Valid tax IDs (these are example numbers, not real)
        valid_ids = [
            ('12345675', '12345675'),  # Valid checksum
            ('', None),  # Empty is valid (optional field)
        ]
        
        for tax_id, expected in valid_ids:
            is_valid, formatted = validator.validate_taiwan_tax_id(tax_id)
            assert is_valid is True
            assert formatted == expected
        
        # Invalid tax IDs
        invalid_ids = ['1234567', '123456789', 'ABCD1234', '12345678']  # Wrong checksum
        for tax_id in invalid_ids:
            is_valid, _ = validator.validate_taiwan_tax_id(tax_id)
            assert is_valid is False


class TestCustomerDataValidation:
    """Test customer data validation."""
    
    @pytest.fixture
    def sample_customer_df(self):
        """Create sample customer DataFrame."""
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'client_code': ['C001', 'C002', '', 'C004', 'C005'],
            'address': [
                '台北市大安區和平東路123號',
                '新北市板橋區文化路456號',
                '',  # Missing address
                '123 Invalid Address',
                '台中市西屯區台灣大道789號'
            ],
            'phone': ['0912345678', '0223456789', 'invalid', '', '0987654321'],
            'contact_person': ['張先生 0912345678', '李小姐', None, '王先生', '陳太太'],
            'tax_id': ['12345675', 'invalid', '', None, '87654321'],  # Last one has wrong checksum
            'latitude': [25.033, 25.012, None, 100.0, 24.147],  # 4th is outside Taiwan
            'longitude': [121.543, 121.462, None, 200.0, 120.673],  # 4th is outside Taiwan
            'cylinder_50kg': [10, 5, -1, 2000, 0],  # 3rd is negative, 4th is too high
            'cylinder_20kg': [20, 10, 5, 15, 0],
            'needs_same_day_delivery': [True, False, False, True, False],
            'hour_8_9': [True, False, False, False, False],  # 4th needs same day but no slots
            'hour_9_10': [False, False, False, False, False],
        })
    
    def test_customer_validation(self, sample_customer_df):
        """Test customer data validation."""
        validator = DataValidator()
        
        # Run validation
        validated_df = validator.validate_customer_data(sample_customer_df)
        
        # Check results
        assert len(validated_df) == 5
        assert 'is_valid' in validated_df.columns
        assert 'validation_errors' in validated_df.columns
        assert 'validation_warnings' in validated_df.columns
        
        # Check specific validations
        assert validated_df.iloc[0]['is_valid'] is True  # First record should be valid
        assert validated_df.iloc[2]['is_valid'] is False  # Missing address and negative inventory
        assert 'Missing client_code' in validated_df.iloc[2]['validation_errors']
        assert 'Missing address' in validated_df.iloc[2]['validation_errors']
        assert 'Negative cylinder_50kg' in validated_df.iloc[2]['validation_errors']
        
        # Check warnings
        assert 'Invalid phone format' in validated_df.iloc[2]['validation_warnings']
        assert 'Invalid tax ID' in validated_df.iloc[1]['validation_warnings']
        assert 'Coordinates outside Taiwan' in validated_df.iloc[3]['validation_warnings']
        assert 'Unusually high cylinder_50kg' in validated_df.iloc[3]['validation_warnings']
        assert 'Same-day delivery requested but no time slots' in validated_df.iloc[3]['validation_warnings']
        
        # Check statistics
        assert validator.validation_stats['total_records'] == 5
        assert validator.validation_stats['valid_records'] == 2
        assert validator.validation_stats['invalid_records'] == 3
        assert validator.validation_stats['errors_by_type']['missing_address'] == 1
        assert validator.validation_stats['warnings_by_type']['invalid_phone'] == 1


class TestOrderDataValidation:
    """Test order data validation."""
    
    @pytest.fixture
    def sample_order_df(self):
        """Create sample order DataFrame."""
        today = date.today()
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'client_id': [1, 2, None, 4, 5],  # 3rd is missing
            'scheduled_date': [
                today - timedelta(days=1),
                today + timedelta(days=1),
                today - timedelta(days=2000),  # Very old
                today + timedelta(days=500),  # Far future
                'invalid_date'
            ],
            'status': ['delivered', 'pending', 'invalid_status', 'delivered', 'cancelled'],
            'delivered_50kg': [2, 1, -1, 0, 5],  # 3rd is negative, 4th delivered none but status is delivered
            'delivered_20kg': [0, 2, 3, 0, 0],
            'returned_50kg': [1, 0, 5, 0, 10],  # 3rd returned > delivered, 5th returned > delivered
            'returned_20kg': [0, 0, 1, 0, 0],
            'actual_delivery_time': [
                datetime.now(),
                None,
                None,
                None,  # Status is delivered but no time
                None
            ]
        })
    
    def test_order_validation(self, sample_order_df):
        """Test order data validation."""
        validator = DataValidator()
        
        # Run validation
        validated_df = validator.validate_order_data(sample_order_df)
        
        # Check results
        assert len(validated_df) == 5
        
        # Check specific validations
        assert validated_df.iloc[0]['is_valid'] is True  # First record should be valid
        assert validated_df.iloc[2]['is_valid'] is False  # Multiple errors
        
        # Check errors
        assert 'Missing client_id' in validated_df.iloc[2]['validation_errors']
        assert 'Invalid status' in validated_df.iloc[2]['validation_errors']
        assert 'Negative delivered_50kg' in validated_df.iloc[2]['validation_errors']
        assert 'Invalid date format' in validated_df.iloc[4]['validation_errors']
        
        # Check warnings
        assert 'Very old order' in validated_df.iloc[2]['validation_warnings']
        assert 'Far future order' in validated_df.iloc[3]['validation_warnings']
        assert 'Returned > delivered' in validated_df.iloc[2]['validation_warnings']
        assert 'Status is delivered but no items' in validated_df.iloc[3]['validation_warnings']
        assert 'Delivered but no actual_delivery_time' in validated_df.iloc[3]['validation_warnings']


class TestValidationReport:
    """Test validation report generation."""
    
    def test_generate_validation_report(self):
        """Test validation report generation."""
        validator = DataValidator()
        
        # Add some test data
        validator.validation_stats = {
            'total_records': 100,
            'valid_records': 85,
            'invalid_records': 15,
            'warnings': 25,
            'errors_by_type': {
                'missing_address': 5,
                'invalid_phone': 10
            },
            'warnings_by_type': {
                'invalid_tax_id': 15,
                'old_order': 10
            }
        }
        
        validator.validation_errors = [
            {'record': 'C001', 'errors': ['Missing address']},
            {'record': 'C002', 'errors': ['Invalid phone', 'Missing client_code']}
        ]
        
        validator.validation_warnings = [
            {'record': 'C003', 'warnings': ['Invalid tax ID']},
            {'record': 'C004', 'warnings': ['Old order']}
        ]
        
        # Generate report
        report = validator.generate_validation_report()
        
        # Check report content
        assert 'Lucky Gas Data Validation Report' in report
        assert 'Total Records: 100' in report
        assert 'Valid Records: 85' in report
        assert 'Invalid Records: 15' in report
        assert 'Validity Rate: 85.00%' in report
        assert 'missing_address: 5' in report
        assert 'invalid_phone: 10' in report
        assert 'invalid_tax_id: 15' in report
        assert 'SAMPLE ERRORS' in report
        assert 'SAMPLE WARNINGS' in report


class TestReferentialIntegrity:
    """Test referential integrity validation."""
    
    @pytest.mark.asyncio
    async def test_validate_referential_integrity(self):
        """Test referential integrity checks."""
        validator = DataValidator()
        
        # Create test data
        customer_df = pd.DataFrame({
            'id': [1, 2, 3, 3],  # Duplicate ID 3
            'client_code': ['C001', 'C002', 'C003', 'C003']  # Duplicate code
        })
        
        order_df = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'client_id': [1, 2, 5, 6],  # 5 and 6 don't exist in customers
            'scheduled_date': [date.today()] * 4
        })
        
        # Mock session (not used in this implementation)
        session = None
        
        # Run validation
        results = await validator.validate_referential_integrity(
            session, customer_df, order_df
        )
        
        # Check results
        assert results['total_customers'] == 4
        assert results['total_orders'] == 4
        assert results['orphaned_orders'] == 2  # Orders with client_id 5 and 6
        assert results['duplicate_customers'] == 1  # Client code C003
        
        # Check details
        orphaned = results['issues']['orphaned_orders']
        assert len(orphaned) == 2
        assert any(o['client_id'] == 5 for o in orphaned)
        assert any(o['client_id'] == 6 for o in orphaned)
        
        duplicates = results['issues']['duplicate_customers']
        assert len(duplicates) == 1
        assert duplicates[0]['client_code'] == 'C003'
        assert duplicates[0]['count'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])