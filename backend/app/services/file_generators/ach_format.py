"""Taiwan ACH (Automated Clearing House) format generator for banking transactions."""

import re
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import logging

from app.models.banking import PaymentBatch, PaymentTransaction
from app.models.customer import Customer

logger = logging.getLogger(__name__)


@dataclass
class ACHRecord:
    """Base class for ACH record types."""

    record_type: str

    def to_fixed_width(self, field_definitions: List[tuple]) -> str:
        """Convert record to fixed-width format."""
        result = ""
        for field_name, width, alignment, padding in field_definitions:
            value = str(getattr(self, field_name, ""))

            # Handle encoding for Chinese characters
            if any(ord(char) > 127 for char in value):
                # For Chinese characters, we need to consider byte length in Big5
                encoded = value.encode("big5", errors="replace")
                if len(encoded) > width:
                    # Truncate by bytes, then decode back
                    encoded = encoded[:width]
                    value = encoded.decode("big5", errors="ignore")
                else:
                    # Pad with spaces
                    space_count = width - len(encoded)
                    value = value + " " * space_count
                result += value
            else:
                # ASCII characters
                if alignment == "L":
                    result += value[:width].ljust(width, padding)
                else:
                    result += value[:width].rjust(width, padding)

        return result


@dataclass
class ACHHeader(ACHRecord):
    """ACH file header record."""

    record_type: str = "H"
    batch_number: str = ""
    creation_date: str = ""
    creation_time: str = ""
    company_code: str = ""
    company_name: str = ""
    bank_code: str = ""
    file_sequence: str = "001"
    format_version: str = "1.0"

    def get_field_definitions(self) -> List[tuple]:
        """Field definitions for header record."""
        return [
            ("record_type", 1, "L", " "),
            ("batch_number", 20, "L", " "),
            ("creation_date", 8, "L", "0"),
            ("creation_time", 6, "L", "0"),
            ("company_code", 10, "L", " "),
            ("company_name", 40, "L", " "),
            ("bank_code", 3, "L", "0"),
            ("file_sequence", 3, "L", "0"),
            ("format_version", 3, "L", " "),
            ("filler", 106, "L", " "),
        ]


@dataclass
class ACHDetail(ACHRecord):
    """ACH payment detail record."""

    record_type: str = "D"
    sequence_number: str = ""
    transaction_id: str = ""
    transaction_type: str = "27"  # 27 = ACH debit
    bank_code: str = ""
    branch_code: str = ""
    account_number: str = ""
    account_holder: str = ""
    amount: str = ""
    payment_date: str = ""
    id_number: str = ""  # Taiwan ID or company tax number
    payment_description: str = ""
    customer_reference: str = ""

    def get_field_definitions(self) -> List[tuple]:
        """Field definitions for detail record."""
        return [
            ("record_type", 1, "L", " "),
            ("sequence_number", 6, "R", "0"),
            ("transaction_id", 20, "L", " "),
            ("transaction_type", 2, "L", "0"),
            ("bank_code", 3, "L", "0"),
            ("branch_code", 4, "L", "0"),
            ("account_number", 14, "L", " "),
            ("account_holder", 30, "L", " "),
            ("amount", 13, "R", "0"),
            ("payment_date", 8, "L", "0"),
            ("id_number", 10, "L", " "),
            ("payment_description", 40, "L", " "),
            ("customer_reference", 20, "L", " "),
            ("filler", 29, "L", " "),
        ]


@dataclass
class ACHTrailer(ACHRecord):
    """ACH file trailer record."""

    record_type: str = "T"
    total_records: str = ""
    total_amount: str = ""
    hash_total: str = ""  # Sum of all account numbers for validation

    def get_field_definitions(self) -> List[tuple]:
        """Field definitions for trailer record."""
        return [
            ("record_type", 1, "L", " "),
            ("total_records", 6, "R", "0"),
            ("total_amount", 15, "R", "0"),
            ("hash_total", 15, "R", "0"),
            ("filler", 163, "L", " "),
        ]


class TaiwanACHGenerator:
    """Generator for Taiwan ACH format files."""

    # Taiwan bank codes (partial list)
    BANK_CODES = {
        "mega": "017",  # 兆豐銀行
        "ctbc": "822",  # 中國信託
        "esun": "808",  # 玉山銀行
        "first": "007",  # 第一銀行
        "taishin": "812",  # 台新銀行
        "fubon": "012",  # 富邦銀行
        "cathay": "013",  # 國泰世華
        "sinopac": "807",  # 永豐銀行
    }

    def __init__(
        self, company_code: str = "LUCKYGAS", company_name: str = "幸福氣體有限公司"
    ):
        self.company_code = company_code
        self.company_name = company_name

    def generate_payment_file(
        self, batch: PaymentBatch, encoding: str = "big5"
    ) -> bytes:
        """
        Generate ACH payment file for a batch.

        Args:
            batch: Payment batch with transactions
            encoding: File encoding (big5 or utf-8)

        Returns:
            bytes: Encoded file content
        """
        lines = []

        # Generate header
        header = self._create_header(batch)
        lines.append(header.to_fixed_width(header.get_field_definitions()))

        # Generate detail records
        total_amount = Decimal("0")
        hash_total = 0

        for idx, transaction in enumerate(batch.transactions, 1):
            detail = self._create_detail(transaction, idx)
            lines.append(detail.to_fixed_width(detail.get_field_definitions()))

            total_amount += transaction.amount
            # Hash total is sum of account numbers (numeric part only)
            account_numeric = re.sub(r"\D", "", transaction.account_number)
            if account_numeric:
                hash_total += int(account_numeric[-8:])  # Use last 8 digits

        # Generate trailer
        trailer = self._create_trailer(
            len(batch.transactions), total_amount, hash_total
        )
        lines.append(trailer.to_fixed_width(trailer.get_field_definitions()))

        # Join lines with CRLF (Windows line ending for banks)
        content = "\r\n".join(lines) + "\r\n"

        # Encode to specified encoding
        return content.encode(encoding, errors="replace")

    def _create_header(self, batch: PaymentBatch) -> ACHHeader:
        """Create ACH header record."""
        now = datetime.utcnow()

        return ACHHeader(
            batch_number=batch.batch_number,
            creation_date=now.strftime("%Y%m%d"),
            creation_time=now.strftime("%H%M%S"),
            company_code=self.company_code,
            company_name=self.company_name,
            bank_code=self.BANK_CODES.get(batch.bank_code, "000"),
            file_sequence="001",
            format_version="1.0",
        )

    def _create_detail(
        self, transaction: PaymentTransaction, sequence: int
    ) -> ACHDetail:
        """Create ACH detail record."""
        # Extract bank and branch code from account number if needed
        bank_code, branch_code = self._parse_account_codes(
            transaction.account_number,
            transaction.customer.bank_code if transaction.customer else None,
        )

        # Format amount (in cents, no decimal)
        amount_cents = int(transaction.amount * 100)

        # Get customer ID number
        id_number = ""
        if transaction.customer:
            id_number = (
                transaction.customer.tax_id or transaction.customer.national_id or ""
            )

        return ACHDetail(
            sequence_number=str(sequence).zfill(6),
            transaction_id=transaction.transaction_id,
            transaction_type="27",  # ACH debit
            bank_code=bank_code,
            branch_code=branch_code,
            account_number=transaction.account_number,
            account_holder=self._format_name(transaction.account_holder),
            amount=str(amount_cents).zfill(13),
            payment_date=transaction.scheduled_date.strftime("%Y%m%d"),
            id_number=id_number,
            payment_description=(
                f"Gas Bill {transaction.invoice_id}"
                if transaction.invoice_id
                else "Gas Payment"
            ),
            customer_reference=(
                str(transaction.customer_id) if transaction.customer_id else ""
            ),
        )

    def _create_trailer(
        self, record_count: int, total_amount: Decimal, hash_total: int
    ) -> ACHTrailer:
        """Create ACH trailer record."""
        # Format total amount in cents
        total_cents = int(total_amount * 100)

        return ACHTrailer(
            total_records=str(record_count).zfill(6),
            total_amount=str(total_cents).zfill(15),
            hash_total=str(hash_total % 10**15).zfill(15),  # Keep within 15 digits
        )

    def _parse_account_codes(
        self, account_number: str, bank_code: Optional[str]
    ) -> tuple:
        """
        Parse bank and branch codes from account number.

        Taiwan account format: BBB-BBBB-AAAAAAAAAA
        Where B = Bank/Branch code, A = Account number
        """
        # Remove all non-numeric characters
        clean_account = re.sub(r"\D", "", account_number)

        if len(clean_account) >= 7:
            # Try to extract bank and branch from account
            bank = clean_account[:3]
            branch = clean_account[3:7]
        else:
            # Use provided bank code or default
            bank = self.BANK_CODES.get(bank_code, "000") if bank_code else "000"
            branch = "0000"

        return bank, branch

    def _format_name(self, name: str) -> str:
        """Format account holder name for ACH."""
        # Remove special characters that might cause issues
        cleaned = re.sub(r"[^\w\s\u4e00-\u9fff]", "", name)
        # Limit length to fit field
        return cleaned[:30]

    def validate_batch(self, batch: PaymentBatch) -> List[str]:
        """
        Validate batch for ACH processing.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not batch.transactions:
            errors.append("Batch has no transactions")
            return errors

        for idx, transaction in enumerate(batch.transactions):
            # Validate account number
            if not transaction.account_number:
                errors.append(f"Transaction {idx+1}: Missing account number")
            elif not re.match(r"^[\d\-]+$", transaction.account_number):
                errors.append(f"Transaction {idx+1}: Invalid account number format")

            # Validate account holder
            if not transaction.account_holder:
                errors.append(f"Transaction {idx+1}: Missing account holder name")
            elif len(transaction.account_holder) > 30:
                logger.warning(
                    f"Transaction {idx+1}: Account holder name will be truncated"
                )

            # Validate amount
            if transaction.amount <= 0:
                errors.append(
                    f"Transaction {idx+1}: Invalid amount {transaction.amount}"
                )
            elif transaction.amount > Decimal("9999999999.99"):
                errors.append(f"Transaction {idx+1}: Amount exceeds maximum")

            # Validate customer reference
            if transaction.customer and not transaction.customer.bank_code:
                logger.warning(f"Transaction {idx+1}: Customer missing bank code")

        return errors

    def generate_reconciliation_parser(self) -> "ACHReconciliationParser":
        """Get parser for reconciliation files."""
        return ACHReconciliationParser()


class ACHReconciliationParser:
    """Parser for ACH reconciliation files from banks."""

    def parse_reconciliation_file(
        self, content: bytes, encoding: str = "big5"
    ) -> List[Dict]:
        """
        Parse ACH reconciliation file.

        Args:
            content: File content
            encoding: File encoding

        Returns:
            List of reconciliation records
        """
        lines = content.decode(encoding, errors="replace").split("\n")
        results = []

        for line in lines:
            if not line.strip():
                continue

            record_type = line[0] if line else ""

            if record_type == "D":  # Detail record
                result = self._parse_detail_record(line)
                if result:
                    results.append(result)
            elif record_type == "R":  # Return/reject record
                result = self._parse_return_record(line)
                if result:
                    results.append(result)

        return results

    def _parse_detail_record(self, line: str) -> Optional[Dict]:
        """Parse detail reconciliation record."""
        if len(line) < 200:
            return None

        try:
            return {
                "record_type": "detail",
                "transaction_id": line[7:27].strip(),
                "bank_reference": line[27:47].strip(),
                "response_code": line[47:50].strip(),
                "response_message": self._get_response_message(line[47:50]),
                "processed_date": datetime.strptime(line[50:58], "%Y%m%d"),
                "processed_amount": Decimal(line[58:71]) / 100,
                "success": line[47:50].strip() == "000",
            }
        except Exception as e:
            logger.error(f"Error parsing detail record: {e}")
            return None

    def _parse_return_record(self, line: str) -> Optional[Dict]:
        """Parse return/reject record."""
        if len(line) < 200:
            return None

        try:
            return {
                "record_type": "return",
                "transaction_id": line[7:27].strip(),
                "return_reason_code": line[27:30].strip(),
                "return_reason": self._get_return_reason(line[27:30]),
                "return_date": datetime.strptime(line[30:38], "%Y%m%d"),
                "original_amount": Decimal(line[38:51]) / 100,
                "success": False,
            }
        except Exception as e:
            logger.error(f"Error parsing return record: {e}")
            return None

    def _get_response_message(self, code: str) -> str:
        """Get human-readable response message for code."""
        messages = {
            "000": "交易成功",
            "001": "帳號錯誤",
            "002": "餘額不足",
            "003": "帳戶已結清",
            "004": "帳戶凍結",
            "005": "無此帳號",
            "006": "金額錯誤",
            "007": "系統錯誤",
            "008": "重複交易",
            "009": "授權失敗",
            "999": "其他錯誤",
        }
        return messages.get(code.strip(), "未知錯誤")

    def _get_return_reason(self, code: str) -> str:
        """Get human-readable return reason."""
        reasons = {
            "R01": "餘額不足",
            "R02": "帳戶已結清",
            "R03": "無此帳號",
            "R04": "帳號錯誤",
            "R05": "未授權",
            "R06": "已撤銷授權",
            "R07": "客戶要求停止扣款",
            "R08": "付款已停止",
            "R09": "未收到授權",
            "R10": "客戶通知未授權",
            "R11": "檢查碼錯誤",
            "R12": "分行無法處理",
            "R99": "其他原因",
        }
        return reasons.get(code.strip(), "未知原因")
