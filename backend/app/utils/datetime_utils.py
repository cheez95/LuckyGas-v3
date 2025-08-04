"""
Date and time utilities for Taiwan localization.
"""

from datetime import date, datetime
from typing import Optional, Union


def format_taiwan_date(dt: Union[datetime, date, None]) -> str:
    """
    Format date/datetime for Taiwan display.

    Args:
        dt: datetime, date, or None

    Returns:
        Formatted date string in Taiwan format (YYYY/MM/DD HH:mm)
    """
    if dt is None:
        return ""

    if isinstance(dt, datetime):
        return dt.strftime("%Y/%m/%d %H:%M")
    elif isinstance(dt, date):
        return dt.strftime("%Y/%m/%d")
    else:
        return str(dt)


def get_taiwan_year(dt: Union[datetime, date]) -> int:
    """
    Get Taiwan year (民國年) from datetime.

    Args:
        dt: datetime or date

    Returns:
        Taiwan year (西元年 - 1911)
    """
    return dt.year - 1911


def format_taiwan_year_date(dt: Union[datetime, date, None]) -> str:
    """
    Format date with Taiwan year (民國年).

    Args:
        dt: datetime, date, or None

    Returns:
        Formatted date string with Taiwan year (e.g., "民國113年1月20日")
    """
    if dt is None:
        return ""

    taiwan_year = get_taiwan_year(dt)

    if isinstance(dt, datetime):
        return (
            f"民國{taiwan_year}年{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}"
        )
    else:
        return f"民國{taiwan_year}年{dt.month}月{dt.day}日"
