"""
Test cases for Big5 to UTF-8 encoding converter
"""
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from app.utils.encoding_converter import (Big5ToUTF8Converter,
                                          convert_customer_data,
                                          validate_taiwan_data)


class TestBig5ToUTF8Converter:
    """Test cases for encoding converter."""
    
    @pytest.fixture
    def converter(self):
        """Create converter instance."""
        return Big5ToUTF8Converter()
    
    def test_string_conversion_basic(self, converter):
        """Test basic string conversion."""
        # Test with common Traditional Chinese characters
        test_cases = [
            # (input_bytes, expected_output)
            (b'\xa4\xa4\xa4\xe5', '中文'),  # "Chinese" in Big5
            (b'\xb4\xfa\xb8\xd5', '測試'),  # "Test" in Big5
            (b'\xa5x\xc6W', '台灣'),        # "Taiwan" in Big5
        ]
        
        for input_bytes, expected in test_cases:
            result = converter.convert_string(input_bytes, 'big5')
            assert result == expected
    
    def test_string_conversion_with_special_chars(self, converter):
        """Test conversion with special characters."""
        # Test address with special characters
        address_big5 = b'\xa5x\xa5_\xa5\xab\xa4j\xa6w\xb0\xcf\xa9M\xa5\xad\xb8\xf4123\xb8\xb9'
        result = converter.convert_string(address_big5, 'big5')
        assert '台北市' in result
        assert '路' in result
        assert '號' in result
    
    def test_already_utf8_string(self, converter):
        """Test handling of already UTF-8 strings."""
        utf8_string = "這是UTF-8字串"
        result = converter.convert_string(utf8_string)
        assert result == utf8_string
        assert converter.conversion_stats['successful'] == 1
    
    def test_none_handling(self, converter):
        """Test handling of None values."""
        assert converter.convert_string(None) is None
    
    def test_dict_conversion(self, converter):
        """Test dictionary conversion."""
        test_dict = {
            'name': b'\xa7\xf5\xa4j\xa9\xfa',  # "李大明" in Big5
            'address': b'\xa5x\xa5_\xa5\xab',  # "台北市" in Big5
            'phone': '0912-345-678',  # Already ASCII
            'quantity': 10,  # Number
            'is_active': True,  # Boolean
        }
        
        result = converter.convert_dict(test_dict)
        
        assert result['name'] == '李大明'
        assert result['address'] == '台北市'
        assert result['phone'] == '0912-345-678'
        assert result['quantity'] == 10
        assert result['is_active'] is True
    
    def test_dataframe_conversion(self, converter):
        """Test pandas DataFrame conversion."""
        # Create test DataFrame
        df = pd.DataFrame({
            'customer_name': [b'\xa7\xf5\xa4j\xa9\xfa', b'\xb3\xaf\xa4p\xac\xfc'],
            'address': [b'\xa5x\xa5_\xa5\xab', b'\xb0\xaa\xb6\xaf\xa5\xab'],
            'phone': ['0912-345-678', '0922-345-678'],
            'amount': [1000, 2000]
        })
        
        # Convert specific columns
        result_df = converter.convert_dataframe(df, columns=['customer_name', 'address'])
        
        assert result_df['customer_name'][0] == '李大明'
        assert result_df['customer_name'][1] == '陳小美'
        assert result_df['address'][0] == '台北市'
        assert result_df['address'][1] == '高雄市'
        assert result_df['phone'][0] == '0912-345-678'  # Unchanged
    
    def test_encoding_detection(self, converter):
        """Test encoding detection."""
        # Big5 encoded text
        big5_bytes = b'\xa4\xa4\xa4\xe5\xb4\xfa\xb8\xd5'
        detected = converter.detect_encoding(big5_bytes)
        assert detected.lower() in ['big5', 'big5-tw', 'big5hkscs', 'cp950']
        
        # UTF-8 encoded text
        utf8_bytes = '中文測試'.encode('utf-8')
        detected = converter.detect_encoding(utf8_bytes)
        assert detected.lower() == 'utf-8'
    
    def test_error_handling(self, converter):
        """Test error handling strategies."""
        # Invalid Big5 sequence
        invalid_bytes = b'\xff\xfe\xfd'
        
        # Test with 'replace' mode (default)
        result = converter.convert_string(invalid_bytes, 'big5')
        assert '�' in result or '\ufffd' in result  # Replacement character
        
        # Test with 'strict' mode
        strict_converter = Big5ToUTF8Converter(fallback_errors='strict')
        with pytest.raises(UnicodeDecodeError):
            strict_converter.convert_string(invalid_bytes, 'big5')
    
    def test_conversion_statistics(self, converter):
        """Test conversion statistics tracking."""
        # Reset stats
        converter.reset_stats()
        
        # Perform conversions
        converter.convert_string(b'\xa4\xa4\xa4\xe5', 'big5')  # Success
        converter.convert_string('Already UTF-8')  # Already UTF-8
        converter.convert_string(b'\xff\xfe', 'big5')  # Fail
        
        stats = converter.get_conversion_report()
        
        assert stats['statistics']['total_processed'] == 3
        assert stats['statistics']['successful'] == 2
        assert stats['statistics']['failed'] == 1
        assert stats['success_rate'] == pytest.approx(66.67, rel=0.01)


class TestTaiwanDataValidation:
    """Test Taiwan-specific data validation."""
    
    def test_phone_validation(self):
        """Test Taiwan phone number validation."""
        # Valid phone numbers
        assert validate_taiwan_data('0912-345-678', 'phone') is True
        assert validate_taiwan_data('0912345678', 'phone') is True
        assert validate_taiwan_data('02-2345-6789', 'phone') is True
        assert validate_taiwan_data('0223456789', 'phone') is True
        
        # Invalid phone numbers
        assert validate_taiwan_data('1234567890', 'phone') is False
        assert validate_taiwan_data('091-234-5678', 'phone') is False  # Wrong format
        assert validate_taiwan_data('', 'phone') is False
    
    def test_address_validation(self):
        """Test Taiwan address validation."""
        # Valid addresses
        assert validate_taiwan_data('台北市大安區和平東路123號', 'address') is True
        assert validate_taiwan_data('新北市板橋區文化路二段456號', 'address') is True
        assert validate_taiwan_data('台中市西屯區台灣大道四段789號', 'address') is True
        
        # Invalid addresses
        assert validate_taiwan_data('123 Main Street', 'address') is False
        assert validate_taiwan_data('台北市', 'address') is False  # Too short
        assert validate_taiwan_data('', 'address') is False
    
    def test_tax_id_validation(self):
        """Test Taiwan tax ID validation."""
        # Valid tax IDs (8 digits)
        assert validate_taiwan_data('12345678', 'tax_id') is True
        assert validate_taiwan_data('87654321', 'tax_id') is True
        
        # Invalid tax IDs
        assert validate_taiwan_data('1234567', 'tax_id') is False  # Too short
        assert validate_taiwan_data('123456789', 'tax_id') is False  # Too long
        assert validate_taiwan_data('1234567A', 'tax_id') is False  # Contains letter
        assert validate_taiwan_data('', 'tax_id') is False


class TestSQLiteConversion:
    """Test SQLite database conversion."""
    
    @pytest.fixture
    def sample_db(self, tmp_path):
        """Create sample SQLite database with Big5 data."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        
        # Create sample table
        conn.execute("""
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY,
                client_code VARCHAR(20),
                name VARCHAR(100),
                address VARCHAR(200),
                phone VARCHAR(20),
                notes TEXT
            )
        """)
        
        # Insert sample data (simulating Big5 encoded data)
        sample_data = [
            (1, 'C001', '李大明', '台北市大安區和平東路123號', '0912-345-678', '重要客戶'),
            (2, 'C002', '陳小美', '新北市板橋區文化路456號', '0922-345-678', '月結客戶'),
            (3, 'C003', '王建國', '台中市西屯區台灣大道789號', '0933-345-678', None),
        ]
        
        conn.executemany(
            "INSERT INTO clients VALUES (?, ?, ?, ?, ?, ?)",
            sample_data
        )
        conn.commit()
        conn.close()
        
        return db_path
    
    def test_sqlite_table_conversion(self, sample_db, tmp_path):
        """Test SQLite table conversion."""
        converter = Big5ToUTF8Converter()
        output_csv = tmp_path / "clients_utf8.csv"
        
        # Convert table
        df = converter.convert_sqlite_table(
            db_path=str(sample_db),
            table_name='clients',
            text_columns=['name', 'address', 'notes'],
            output_path=str(output_csv)
        )
        
        # Verify conversion
        assert len(df) == 3
        assert df['name'][0] == '李大明'
        assert df['address'][1] == '新北市板橋區文化路456號'
        assert df['phone'][2] == '0933-345-678'
        
        # Verify output file
        assert output_csv.exists()
        df_loaded = pd.read_csv(output_csv)
        assert len(df_loaded) == 3
    
    def test_convert_customer_data_function(self, sample_db, tmp_path):
        """Test the convert_customer_data utility function."""
        output_dir = tmp_path / "converted"
        
        # Run conversion
        results = convert_customer_data(str(sample_db), str(output_dir))
        
        # Verify results
        assert 'clients' in results
        assert results['clients'] is not None
        assert len(results['clients']) == 3
        
        # Verify output files
        assert (output_dir / 'clients_utf8.csv').exists()
        assert (output_dir / 'conversion_report.txt').exists()
        
        # Check report content
        with open(output_dir / 'conversion_report.txt', 'r', encoding='utf-8') as f:
            report = f.read()
            assert 'Big5 to UTF-8 Conversion Report' in report
            assert 'clients' in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])