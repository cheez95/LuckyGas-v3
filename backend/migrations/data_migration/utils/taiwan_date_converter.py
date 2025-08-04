"""
Taiwan Calendar (民國年) Date Converter
Handles conversion between Taiwan calendar and Gregorian calendar
"""

from datetime import datetime, date
from typing import Union, Optional
import re


class TaiwanDateConverter:
    """Convert between Taiwan (ROC) calendar and Gregorian calendar"""
    
    # Taiwan calendar started in 1912 (ROC year 1)
    ROC_YEAR_OFFSET = 1911
    
    @staticmethod
    def taiwan_to_gregorian(taiwan_date: Union[str, int]) -> Optional[date]:
        """
        Convert Taiwan date to Gregorian date
        
        Args:
            taiwan_date: Date in format YYYMMDD or YMMDD (e.g., 1130520 or 130520)
                        YYY = ROC year (3 digits)
                        Y = ROC year (1-2 digits) 
                        MM = month (2 digits)
                        DD = day (2 digits)
        
        Returns:
            datetime.date object or None if invalid
            
        Examples:
            1130520 -> 2024-05-20
            1100102 -> 2021-01-02
            990315 -> 2010-03-15
        """
        taiwan_str = str(taiwan_date).strip()
        
        # Remove any non-numeric characters
        taiwan_str = re.sub(r'\D', '', taiwan_str)
        
        if not taiwan_str:
            return None
        
        # Determine format based on length
        if len(taiwan_str) == 7:  # YYYMMDD
            roc_year = int(taiwan_str[:3])
            month = int(taiwan_str[3:5])
            day = int(taiwan_str[5:7])
        elif len(taiwan_str) == 6:  # YYMMDD (assume 100+ for 2-digit years)
            roc_year = int(taiwan_str[:2]) + 100
            month = int(taiwan_str[2:4])
            day = int(taiwan_str[4:6])
        elif len(taiwan_str) == 5:  # YMMDD (1-digit year, very old dates)
            roc_year = int(taiwan_str[:1]) + 100
            month = int(taiwan_str[1:3])
            day = int(taiwan_str[3:5])
        else:
            return None
        
        try:
            # Convert to Gregorian year
            gregorian_year = roc_year + TaiwanDateConverter.ROC_YEAR_OFFSET
            
            # Create date object
            return date(gregorian_year, month, day)
        except ValueError:
            # Invalid date
            return None
    
    @staticmethod
    def gregorian_to_taiwan(gregorian_date: Union[date, datetime], 
                           format: str = 'YYYMMDD') -> str:
        """
        Convert Gregorian date to Taiwan date string
        
        Args:
            gregorian_date: Python date or datetime object
            format: Output format ('YYYMMDD' or 'YYY/MM/DD' or 'YYY年MM月DD日')
        
        Returns:
            Taiwan date string
            
        Examples:
            2024-05-20 -> 1130520
            2021-01-02 -> 1100102
        """
        if isinstance(gregorian_date, datetime):
            gregorian_date = gregorian_date.date()
        
        # Calculate ROC year
        roc_year = gregorian_date.year - TaiwanDateConverter.ROC_YEAR_OFFSET
        
        # Format based on requested format
        if format == 'YYYMMDD':
            return f"{roc_year:03d}{gregorian_date.month:02d}{gregorian_date.day:02d}"
        elif format == 'YYY/MM/DD':
            return f"{roc_year:03d}/{gregorian_date.month:02d}/{gregorian_date.day:02d}"
        elif format == 'YYY年MM月DD日':
            return f"{roc_year}年{gregorian_date.month}月{gregorian_date.day}日"
        else:
            return f"{roc_year:03d}{gregorian_date.month:02d}{gregorian_date.day:02d}"
    
    @staticmethod
    def parse_mixed_date(date_str: str) -> Optional[date]:
        """
        Parse various Taiwan date formats
        
        Handles:
        - 113/05/20
        - 113.05.20
        - 113-05-20
        - 民國113年5月20日
        - 1130520
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Try to parse formatted dates
        patterns = [
            r'(\d{2,3})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',  # YYY/MM/DD
            r'民國(\d{2,3})年(\d{1,2})月(\d{1,2})日',         # 民國YYY年MM月DD日
            r'(\d{2,3})年(\d{1,2})月(\d{1,2})日',           # YYY年MM月DD日
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                roc_year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                
                try:
                    gregorian_year = roc_year + TaiwanDateConverter.ROC_YEAR_OFFSET
                    return date(gregorian_year, month, day)
                except ValueError:
                    continue
        
        # Try numeric format
        numeric_only = re.sub(r'\D', '', date_str)
        if numeric_only:
            return TaiwanDateConverter.taiwan_to_gregorian(numeric_only)
        
        return None
    
    @staticmethod
    def get_current_taiwan_year() -> int:
        """Get current year in Taiwan calendar"""
        return datetime.now().year - TaiwanDateConverter.ROC_YEAR_OFFSET


# Convenience functions
def taiwan_to_date(taiwan_date: Union[str, int]) -> Optional[date]:
    """Convert Taiwan date to Python date object"""
    return TaiwanDateConverter.taiwan_to_gregorian(taiwan_date)


def date_to_taiwan(date_obj: Union[date, datetime], format: str = 'YYYMMDD') -> str:
    """Convert Python date to Taiwan date string"""
    return TaiwanDateConverter.gregorian_to_taiwan(date_obj, format)


def parse_taiwan_date(date_str: str) -> Optional[date]:
    """Parse various Taiwan date formats"""
    return TaiwanDateConverter.parse_mixed_date(date_str)


# Test the converter
if __name__ == "__main__":
    # Test cases
    test_dates = [
        '1130520',   # Should be 2024-05-20
        '1100102',   # Should be 2021-01-02
        '990315',    # Should be 2010-03-15
        '113/05/20', # Should be 2024-05-20
        '民國113年5月20日'  # Should be 2024-05-20
    ]
    
    print("Taiwan Date Converter Tests:")
    print("-" * 50)
    
    for taiwan_date in test_dates:
        gregorian = parse_taiwan_date(taiwan_date)
        if gregorian:
            taiwan_back = date_to_taiwan(gregorian, 'YYY年MM月DD日')
            print(f"{taiwan_date:<20} -> {gregorian} -> {taiwan_back}")
        else:
            print(f"{taiwan_date:<20} -> Invalid date")
    
    print("\nCurrent Taiwan year:", TaiwanDateConverter.get_current_taiwan_year())