"""
Taiwan-specific validators for Pydantic models
"""

import re
from typing import Optional
from pydantic import field_validator, Field
from datetime import datetime


class TaiwanValidators:
    """Collection of Taiwan-specific validators"""

    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """
        Validate and format Taiwan phone number
        Accepts: 0912345678, 0912-345-678, 09-1234-5678
        Returns: 0912-345-678 format
        """
        # Remove all non-digits
        digits = re.sub(r"\D", "", phone)

        # Mobile phone (10 digits starting with 09)
        if re.match(r"^09\d{8}$", digits):
            return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"

        # Landline (9-10 digits)
        if re.match(r"^0[2-8]\d{7,8}$", digits):
            if len(digits) == 9:  # 2-digit area code
                return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
            else:  # 3-digit area code
                return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

        raise ValueError(f"無效的電話號碼格式: {phone}")

    @staticmethod
    def validate_tax_id(tax_id: str) -> str:
        """
        Validate Taiwan company tax ID (統一編號)
        8 digits with checksum validation
        """
        # Remove any spaces or hyphens
        tax_id_clean = re.sub(r"[\s\-]", "", tax_id)

        if not re.match(r"^\d{8}$", tax_id_clean):
            raise ValueError("統一編號必須為8位數字")

        # Taiwan tax ID checksum algorithm
        weights = [1, 2, 1, 2, 1, 2, 4, 1]
        checksum = 0

        for i, digit in enumerate(tax_id_clean):
            product = int(digit) * weights[i]
            checksum += product // 10 + product % 10

        if checksum % 10 != 0:
            raise ValueError("無效的統一編號")

        return tax_id_clean

    @staticmethod
    def validate_postal_code(postal_code: str) -> str:
        """
        Validate Taiwan postal code (3 or 5 digits)
        """
        postal_code_clean = re.sub(r"\D", "", postal_code)

        if re.match(r"^\d{3}$", postal_code_clean):
            return postal_code_clean
        elif re.match(r"^\d{5}$", postal_code_clean):
            return postal_code_clean[:3] + "-" + postal_code_clean[3:]
        else:
            raise ValueError("郵遞區號必須為3或5位數字")

    @staticmethod
    def validate_address(address: str) -> str:
        """
        Validate Taiwan address format
        Must contain: 縣/市, 區/鄉/鎮, 路/街, 號
        """
        # Check for required components
        if not re.search(r"(縣|市)", address):
            raise ValueError("地址必須包含縣或市")
        if not re.search(r"(區|鄉|鎮|市)", address):
            raise ValueError("地址必須包含區、鄉、鎮或市")
        if not re.search(r"(路|街|巷)", address):
            raise ValueError("地址必須包含路、街或巷")
        if not re.search(r"號", address):
            raise ValueError("地址必須包含號")

        return address.strip()

    @staticmethod
    def validate_national_id(id_number: str) -> str:
        """
        Validate Taiwan National ID (身分證字號)
        Format: 1 letter + 9 digits with checksum
        """
        id_clean = id_number.upper().strip()

        if not re.match(r"^[A-Z]\d{9}$", id_clean):
            raise ValueError("身分證字號格式錯誤")

        # Letter to number mapping
        letter_map = {
            "A": 10,
            "B": 11,
            "C": 12,
            "D": 13,
            "E": 14,
            "F": 15,
            "G": 16,
            "H": 17,
            "I": 34,
            "J": 18,
            "K": 19,
            "L": 20,
            "M": 21,
            "N": 22,
            "O": 35,
            "P": 23,
            "Q": 24,
            "R": 25,
            "S": 26,
            "T": 27,
            "U": 28,
            "V": 29,
            "W": 32,
            "X": 30,
            "Y": 31,
            "Z": 33,
        }

        # Convert first letter to number
        n1 = letter_map[id_clean[0]]
        n1_1 = n1 // 10
        n1_2 = n1 % 10

        # Calculate checksum
        weights = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        total = n1_1 * weights[0] + n1_2 * weights[1]

        for i in range(1, 10):
            total += int(id_clean[i]) * weights[i + 1]

        if total % 10 != 0:
            raise ValueError("身分證字號檢查碼錯誤")

        return id_clean

    @staticmethod
    def format_currency_twd(amount: float) -> str:
        """Format amount as TWD currency with thousand separators"""
        return f"NT${amount:,.0f}"

    @staticmethod
    def validate_invoice_number(invoice_number: str) -> str:
        """
        Validate Taiwan invoice number format
        Format: XX-12345678 (2 letters + 8 digits)
        """
        invoice_clean = invoice_number.upper().strip()

        if re.match(r"^[A-Z]{2}-?\d{8}$", invoice_clean):
            # Normalize format
            if "-" not in invoice_clean:
                return f"{invoice_clean[:2]}-{invoice_clean[2:]}"
            return invoice_clean
        else:
            raise ValueError("發票號碼格式錯誤 (應為: XX-12345678)")

    @staticmethod
    def validate_roc_year(year: int) -> int:
        """
        Validate ROC year (民國年)
        Accepts years from 1 to current ROC year
        """
        current_year = datetime.now().year
        current_roc_year = current_year - 1911

        if year < 1 or year > current_roc_year:
            raise ValueError(f"民國年份必須在1到{current_roc_year}之間")

        return year

    @staticmethod
    def roc_to_western_year(roc_year: int) -> int:
        """Convert ROC year to Western year"""
        return roc_year + 1911

    @staticmethod
    def western_to_roc_year(western_year: int) -> int:
        """Convert Western year to ROC year"""
        return western_year - 1911


# Pydantic field validators for common Taiwan fields
def phone_validator(cls, v: str) -> str:
    """Pydantic validator for phone numbers"""
    return TaiwanValidators.validate_phone_number(v)


def tax_id_validator(cls, v: str) -> str:
    """Pydantic validator for tax IDs"""
    return TaiwanValidators.validate_tax_id(v)


def address_validator(cls, v: str) -> str:
    """Pydantic validator for addresses"""
    return TaiwanValidators.validate_address(v)


def postal_code_validator(cls, v: str) -> str:
    """Pydantic validator for postal codes"""
    return TaiwanValidators.validate_postal_code(v)


def national_id_validator(cls, v: str) -> str:
    """Pydantic validator for national IDs"""
    return TaiwanValidators.validate_national_id(v)


def invoice_validator(cls, v: str) -> str:
    """Pydantic validator for invoice numbers"""
    return TaiwanValidators.validate_invoice_number(v)


# Pre-configured Pydantic Fields for Taiwan data
TaiwanPhoneField = Field(
    ...,
    min_length=9,
    max_length=15,
    description="Taiwan phone number",
    examples=["0912-345-678", "02-2345-6789"],
)

TaiwanTaxIdField = Field(
    ...,
    min_length=8,
    max_length=8,
    description="Taiwan company tax ID (統一編號)",
    examples=["12345678"],
)

TaiwanAddressField = Field(
    ...,
    min_length=10,
    max_length=200,
    description="Taiwan address",
    examples=["台北市中正區重慶南路一段122號"],
)

TaiwanPostalCodeField = Field(
    ...,
    min_length=3,
    max_length=6,
    description="Taiwan postal code",
    examples=["100", "100-01"],
)

TaiwanNationalIdField = Field(
    ...,
    min_length=10,
    max_length=10,
    description="Taiwan national ID",
    examples=["A123456789"],
)

TaiwanInvoiceField = Field(
    ...,
    min_length=10,
    max_length=11,
    description="Taiwan invoice number",
    examples=["AB-12345678"],
)
