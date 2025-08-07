"""
Validation utilities for Lucky Gas backend.
"""

import re


def validate_phone_number(phone: str) -> bool:
    """
    Validate Taiwan phone number formats.

    Args:
        phone: Phone number string

    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False

    # Remove any spaces or hyphens
    phone_clean = re.sub(r"[\s\-]", "", phone)

    # Mobile pattern: 09 followed by 8 digits
    mobile_pattern = r"^09\d{8}$"
    # Landline pattern: 0 + area code (1 - 2 digits) + 7 - 8 digits
    landline_pattern = r"^0[2 - 8]\d{7, 8}$"

    return bool(
        re.match(mobile_pattern, phone_clean) or re.match(landline_pattern, phone_clean)
    )


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address string

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False

    email_regex = r"^[a - zA - Z0 - 9._%+-]+@[a - zA - Z0 - 9.-]+\.[a - zA - Z]{2, }$"
    return bool(re.match(email_regex, email))


def validate_taiwan_address(address: str) -> bool:
    """
    Validate Taiwan address format contains required components.

    Args:
        address: Address string

    Returns:
        True if valid, False otherwise
    """
    if not address:
        return False

    # Check for common Taiwan address components
    required_patterns = [
        r"(縣|市)",  # County or City
        r"(區|鄉|鎮|市)",  # District
        r"(路|街|巷)",  # Road / Street
        r"號",  # Number
    ]

    return all(re.search(pattern, address) for pattern in required_patterns)


def validate_tax_id(tax_id: str) -> bool:
    """
    Validate Taiwan tax ID (統一編號) - 8 digits with checksum.

    Args:
        tax_id: Tax ID string

    Returns:
        True if valid, False otherwise
    """
    if not tax_id or not re.match(r"^\d{8}$", tax_id):
        return False

    # Taiwan tax ID checksum algorithm
    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    checksum = 0

    for i, digit in enumerate(tax_id):
        product = int(digit) * weights[i]
        checksum += product // 10 + product % 10

    return checksum % 10 == 0
