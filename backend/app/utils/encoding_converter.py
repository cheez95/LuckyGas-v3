"""
Big5 to UTF-8 encoding converter for Taiwan data migration
Handles Traditional Chinese character conversion with proper error handling
"""
import codecs
import logging
from typing import Any, Dict, List, Optional, Union
import chardet
import sqlite3
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class Big5ToUTF8Converter:
    """
    Converter for Big5 (Traditional Chinese) to UTF-8 encoding.
    Handles various data types and provides detailed error reporting.
    """
    
    # Common Big5 characters that may have issues
    SPECIAL_CHARS_MAP = {
        # Common problematic mappings
        '\uff0c': '，',  # Full-width comma
        '\uff08': '（',  # Full-width left parenthesis  
        '\uff09': '）',  # Full-width right parenthesis
        '\u3000': '　',  # Ideographic space
        '\uff1a': '：',  # Full-width colon
        '\uff1b': '；',  # Full-width semicolon
        '\u2013': '–',   # En dash
        '\u2014': '—',   # Em dash
    }
    
    # Known problematic Big5 code points
    PROBLEM_CHARS = {
        b'\xa1\x40': '　',  # Ideographic space
        b'\xa1\x41': '，',  # Ideographic comma
        b'\xa1\x42': '、',  # Ideographic comma variant
        b'\xa1\x43': '。',  # Ideographic full stop
        b'\xa1\x44': '．',  # Middle dot
        b'\xa1\x45': '‧',  # Hyphenation point
        b'\xa1\x48': '？',  # Full-width question mark
        b'\xa1\x49': '！',  # Full-width exclamation mark
    }
    
    def __init__(self, fallback_errors: str = 'replace'):
        """
        Initialize converter with error handling strategy.
        
        Args:
            fallback_errors: Error handling mode ('strict', 'ignore', 'replace')
        """
        self.fallback_errors = fallback_errors
        self.conversion_errors = []
        self.conversion_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'replaced_chars': 0,
            'encoding_detected': {}
        }
    
    def detect_encoding(self, data: bytes) -> str:
        """
        Detect the encoding of byte data.
        
        Args:
            data: Byte data to analyze
            
        Returns:
            Detected encoding name
        """
        result = chardet.detect(data)
        encoding = result['encoding']
        confidence = result['confidence']
        
        # Log detection results
        logger.debug(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")
        
        # Common aliases for Big5
        if encoding and encoding.lower() in ['big5', 'big5-tw', 'big5hkscs', 'cp950']:
            return 'big5'
        
        return encoding or 'big5'
    
    def convert_string(self, text: Union[str, bytes], source_encoding: str = None) -> str:
        """
        Convert a single string from Big5 to UTF-8.
        
        Args:
            text: Text to convert
            source_encoding: Force specific encoding (default: auto-detect)
            
        Returns:
            UTF-8 encoded string
        """
        self.conversion_stats['total_processed'] += 1
        
        if text is None:
            return None
        
        # If already string, check if needs conversion
        if isinstance(text, str):
            # Try to encode/decode to verify it's valid UTF-8
            try:
                text.encode('utf-8')
                self.conversion_stats['successful'] += 1
                return text
            except UnicodeEncodeError:
                # Contains non-UTF-8 characters, needs conversion
                text = text.encode('big5', errors='ignore')
        
        # Convert bytes to string
        if isinstance(text, bytes):
            if not source_encoding:
                source_encoding = self.detect_encoding(text)
                self.conversion_stats['encoding_detected'][source_encoding] = \
                    self.conversion_stats['encoding_detected'].get(source_encoding, 0) + 1
            
            try:
                # Primary conversion attempt
                result = text.decode(source_encoding, errors='strict')
                
                # Apply special character mappings
                for old_char, new_char in self.SPECIAL_CHARS_MAP.items():
                    if old_char in result:
                        result = result.replace(old_char, new_char)
                        self.conversion_stats['replaced_chars'] += 1
                
                self.conversion_stats['successful'] += 1
                return result
                
            except UnicodeDecodeError as e:
                # Try handling known problematic characters
                result = self._handle_problem_chars(text, source_encoding)
                if result:
                    self.conversion_stats['successful'] += 1
                    return result
                
                # Fallback error handling
                self.conversion_stats['failed'] += 1
                self.conversion_errors.append({
                    'text': text[:50],  # First 50 bytes for logging
                    'error': str(e),
                    'position': e.start
                })
                
                if self.fallback_errors == 'strict':
                    raise
                
                # Use fallback error handling
                return text.decode(source_encoding, errors=self.fallback_errors)
        
        return str(text)
    
    def _handle_problem_chars(self, text: bytes, encoding: str) -> Optional[str]:
        """
        Handle known problematic Big5 characters.
        
        Args:
            text: Byte text with problems
            encoding: Source encoding
            
        Returns:
            Converted string if successful, None otherwise
        """
        try:
            # Replace known problem bytes
            modified_text = text
            for problem_bytes, replacement in self.PROBLEM_CHARS.items():
                if problem_bytes in modified_text:
                    modified_text = modified_text.replace(
                        problem_bytes, 
                        replacement.encode('utf-8')
                    )
                    self.conversion_stats['replaced_chars'] += 1
            
            # Try decoding again
            return modified_text.decode('utf-8', errors='strict')
        except:
            return None
    
    def convert_dict(self, data: Dict[str, Any], fields_to_convert: List[str] = None) -> Dict[str, Any]:
        """
        Convert dictionary values from Big5 to UTF-8.
        
        Args:
            data: Dictionary to convert
            fields_to_convert: Specific fields to convert (None = all string fields)
            
        Returns:
            Dictionary with converted values
        """
        result = {}
        
        for key, value in data.items():
            if fields_to_convert and key not in fields_to_convert:
                result[key] = value
            elif isinstance(value, (str, bytes)):
                result[key] = self.convert_string(value)
            elif isinstance(value, dict):
                result[key] = self.convert_dict(value, fields_to_convert)
            elif isinstance(value, list):
                result[key] = [
                    self.convert_string(item) if isinstance(item, (str, bytes)) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    def convert_dataframe(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """
        Convert pandas DataFrame columns from Big5 to UTF-8.
        
        Args:
            df: DataFrame to convert
            columns: Specific columns to convert (None = all string columns)
            
        Returns:
            DataFrame with converted values
        """
        df_copy = df.copy()
        
        # Determine columns to convert
        if columns is None:
            columns = df_copy.select_dtypes(include=['object']).columns.tolist()
        
        # Convert each column
        for col in columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(
                    lambda x: self.convert_string(x) if pd.notna(x) else x
                )
        
        return df_copy
    
    def convert_sqlite_table(
        self, 
        db_path: str, 
        table_name: str,
        text_columns: List[str],
        output_path: str = None
    ) -> pd.DataFrame:
        """
        Convert SQLite table from Big5 to UTF-8.
        
        Args:
            db_path: Path to SQLite database
            table_name: Table name to convert
            text_columns: List of text columns to convert
            output_path: Optional path to save converted data
            
        Returns:
            Converted DataFrame
        """
        # Connect to database
        conn = sqlite3.connect(db_path)
        
        # Read table
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert specified columns
        df_converted = self.convert_dataframe(df, columns=text_columns)
        
        # Save if output path provided
        if output_path:
            if output_path.endswith('.csv'):
                df_converted.to_csv(output_path, index=False, encoding='utf-8')
            elif output_path.endswith('.xlsx'):
                df_converted.to_excel(output_path, index=False)
            else:
                # Save as new SQLite
                conn_out = sqlite3.connect(output_path)
                df_converted.to_sql(table_name, conn_out, if_exists='replace', index=False)
                conn_out.close()
        
        return df_converted
    
    def convert_file(self, input_path: str, output_path: str, source_encoding: str = 'big5'):
        """
        Convert entire file from Big5 to UTF-8.
        
        Args:
            input_path: Input file path
            output_path: Output file path
            source_encoding: Source file encoding
        """
        try:
            # Read file in binary mode
            with open(input_path, 'rb') as f:
                content = f.read()
            
            # Detect encoding if not specified
            if not source_encoding:
                source_encoding = self.detect_encoding(content)
            
            # Convert content
            converted_content = self.convert_string(content, source_encoding)
            
            # Write UTF-8 file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
            logger.info(f"Successfully converted {input_path} to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to convert file {input_path}: {e}")
            raise
    
    def get_conversion_report(self) -> Dict[str, Any]:
        """
        Get detailed conversion statistics and errors.
        
        Returns:
            Dictionary with conversion report
        """
        return {
            'statistics': self.conversion_stats,
            'errors': self.conversion_errors,
            'success_rate': (
                self.conversion_stats['successful'] / self.conversion_stats['total_processed']
                if self.conversion_stats['total_processed'] > 0 else 0
            ) * 100
        }
    
    def reset_stats(self):
        """Reset conversion statistics and errors."""
        self.conversion_errors = []
        self.conversion_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'replaced_chars': 0,
            'encoding_detected': {}
        }


# Utility functions for common conversion tasks

def convert_customer_data(db_path: str, output_dir: str) -> Dict[str, pd.DataFrame]:
    """
    Convert all customer-related tables from Big5 to UTF-8.
    
    Args:
        db_path: Path to legacy SQLite database
        output_dir: Directory to save converted files
        
    Returns:
        Dictionary of converted DataFrames
    """
    converter = Big5ToUTF8Converter()
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Define tables and their text columns
    tables_config = {
        'clients': [
            'client_code', 'invoice_title', 'short_name', 'address',
            'name', 'contact_person', 'district', 'notes', 'area',
            'primary_usage_area', 'secondary_usage_area', 'switch_model',
            'client_type', 'holiday', 'payment_file', 'pricing_method'
        ],
        'deliveries': ['notes'],
        'drivers': ['name', 'phone', 'employee_id', 'license_type', 'familiar_areas'],
        'vehicles': ['plate_number', 'vehicle_type'],
        'routes': ['route_name', 'area', 'route_details']
    }
    
    results = {}
    
    for table_name, text_columns in tables_config.items():
        logger.info(f"Converting table: {table_name}")
        
        try:
            # Convert table
            df_converted = converter.convert_sqlite_table(
                db_path=db_path,
                table_name=table_name,
                text_columns=text_columns,
                output_path=str(output_dir / f"{table_name}_utf8.csv")
            )
            
            results[table_name] = df_converted
            
            # Log statistics
            stats = converter.get_conversion_report()
            logger.info(f"Table {table_name} conversion complete. Success rate: {stats['success_rate']:.2f}%")
            
            if stats['errors']:
                logger.warning(f"Errors encountered in {table_name}: {len(stats['errors'])}")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")
            
            # Reset for next table
            converter.reset_stats()
            
        except Exception as e:
            logger.error(f"Failed to convert table {table_name}: {e}")
            results[table_name] = None
    
    # Generate summary report
    report_path = output_dir / 'conversion_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("Big5 to UTF-8 Conversion Report\n")
        f.write("=" * 50 + "\n\n")
        
        for table_name, df in results.items():
            if df is not None:
                f.write(f"Table: {table_name}\n")
                f.write(f"  Rows converted: {len(df)}\n")
                f.write(f"  Columns: {', '.join(df.columns)}\n\n")
            else:
                f.write(f"Table: {table_name} - FAILED\n\n")
    
    logger.info(f"Conversion complete. Report saved to {report_path}")
    return results


def validate_taiwan_data(text: str, data_type: str) -> bool:
    """
    Validate Taiwan-specific data after conversion.
    
    Args:
        text: Converted text to validate
        data_type: Type of data ('phone', 'address', 'tax_id')
        
    Returns:
        True if valid, False otherwise
    """
    if not text:
        return False
    
    if data_type == 'phone':
        # Taiwan phone: 09XX-XXX-XXX or 0X-XXXX-XXXX
        import re
        pattern = r'^(09\d{2}-?\d{3}-?\d{3}|0[2-8]-?\d{4}-?\d{4})$'
        return bool(re.match(pattern, text.replace(' ', '')))
    
    elif data_type == 'address':
        # Must contain county/city and common address components
        required_chars = ['縣', '市', '區', '鄉', '鎮', '路', '街', '號']
        return any(char in text for char in required_chars[:3]) and \
               any(char in text for char in required_chars[5:])
    
    elif data_type == 'tax_id':
        # Taiwan tax ID: 8 digits
        return text.isdigit() and len(text) == 8
    
    return True


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python encoding_converter.py <input_db> <output_dir>")
        sys.exit(1)
    
    input_db = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run conversion
    results = convert_customer_data(input_db, output_dir)
    
    print(f"\nConversion complete. Converted {len(results)} tables.")
    for table, df in results.items():
        if df is not None:
            print(f"  - {table}: {len(df)} rows")