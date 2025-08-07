"""Integration tests for banking service with mocked SFTP."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.banking import (
    BankConfiguration,
    PaymentBatch,
    PaymentBatchStatus,
    PaymentTransaction,
    TransactionStatus,
)
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoicePaymentStatus
from app.models.user import User
from app.services.banking_service import BankingService

# Import banking test marker
from tests.conftest_payment import requires_banking


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        username="testadmin",
        email="admin@luckygas.com",
        full_name="Test Admin",
        role="admin",
        is_active=True,
        is_superuser=True,
    )
    user.set_password("testpass123")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_bank_config(db: Session):
    """Create a test bank configuration."""
    config = BankConfiguration(
        bank_code="TEST",
        bank_name="Test Bank",
        sftp_host="test.bank.com",
        sftp_port=22,
        sftp_username="testuser",
        sftp_password="testpass",
        upload_path="/test / upload/",
        download_path="/test / download/",
        archive_path="/test / archive/",
        file_format="fixed_width",
        encoding="UTF - 8",
        payment_file_pattern="PAY_{YYYYMMDD}_{BATCH}.txt",
        reconciliation_file_pattern="REC_{YYYYMMDD}.txt",
        is_active=True,
        cutoff_time="15:00",
        retry_attempts=3,
        retry_delay_minutes=30,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@pytest.fixture
def test_customers(db: Session):
    """Create test customers with banking info."""
    customers = []

    for i in range(3):
        customer = Customer(
            customer_code=f"CUST00{i + 1}",
            short_name=f"Customer {i + 1}",
            address=f"Test Address {i + 1}",
            phone=f"0912345{i:03d}",
            payment_method="bank_transfer",
            bank_code="TEST",
            bank_account_number=f"123456789012{i:02d}",
            bank_account_holder=f"Customer {i + 1}",
        )
        db.add(customer)
        customers.append(customer)

    db.commit()
    return customers


@pytest.fixture
def test_invoices(db: Session, test_customers):
    """Create test invoices for payment processing."""
    invoices = []

    for i, customer in enumerate(test_customers):
        invoice = Invoice(
            invoice_number=f"INV2024010{i + 1}",
            customer_id=customer.id,
            invoice_date=datetime.now().date(),
            due_date=(datetime.now() + timedelta(days=30)).date(),
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("50.00"),
            total_amount=Decimal("1050.00"),
            payment_status=InvoicePaymentStatus.PENDING,
        )
        db.add(invoice)
        invoices.append(invoice)

    db.commit()
    return invoices


@requires_banking
class TestBankingIntegration:
    """Integration tests for banking workflows."""

    @patch("paramiko.Transport")
    @patch("paramiko.SFTPClient.from_transport")
    def test_complete_payment_workflow(
        self,
        mock_sftp_class,
        mock_transport_class,
        db: Session,
        test_bank_config,
        test_invoices,
        test_user,
    ):
        """Test complete payment processing workflow."""
        # Setup mocked SFTP
        mock_transport = Mock()
        mock_transport_class.return_value = mock_transport

        mock_sftp = Mock()
        mock_sftp_class.return_value = mock_sftp

        banking_service = BankingService(db)

        # Step 1: Create payment batch
        batch = banking_service.create_payment_batch(
            bank_code="TEST",
            processing_date=datetime.now(),
            invoice_ids=[inv.id for inv in test_invoices],
        )

        assert batch.total_transactions == 3
        assert batch.total_amount == Decimal("3150.00")
        assert batch.status == PaymentBatchStatus.DRAFT

        # Step 2: Generate payment file
        content = banking_service.generate_payment_file(batch.id)

        assert content.startswith("H")  # Header
        assert content.count("\r\nD") == 3  # 3 detail records
        assert content.endswith("\r\n")  # Proper line ending

        # Step 3: Upload payment file
        mock_sftp.putfo = Mock()

        success = banking_service.upload_payment_file(batch.id)

        assert success is True
        assert mock_sftp.putfo.called

        # Refresh batch
        db.refresh(batch)
        assert batch.status == PaymentBatchStatus.UPLOADED
        assert batch.file_name is not None

        # Step 4: Simulate bank processing and reconciliation
        reconciliation_content = self._generate_reconciliation_file(batch)

        # Mock downloading reconciliation file
        mock_sftp.listdir.return_value = ["REC_20240120.txt"]
        mock_sftp.getfo = Mock(
            side_effect=lambda remote, local: local.write(
                reconciliation_content.encode("UTF - 8")
            )
        )

        # Check for new files
        new_files = banking_service.check_reconciliation_files("TEST")
        assert len(new_files) == 1

        # Process reconciliation
        mock_sftp.rename = Mock()  # Mock archive operation
        log = banking_service.process_reconciliation_file("TEST", new_files[0])

        assert log.status == "MATCHED"
        assert log.matched_records == 2
        assert log.failed_records == 1

        # Verify transaction updates
        transactions = db.query(PaymentTransaction).filter_by(batch_id=batch.id).all()

        success_count = sum(
            1 for t in transactions if t.status == TransactionStatus.SUCCESS
        )
        failed_count = sum(
            1 for t in transactions if t.status == TransactionStatus.FAILED
        )

        assert success_count == 2
        assert failed_count == 1

        # Verify invoice updates
        paid_invoices = (
            db.query(Invoice).filter_by(payment_status=InvoicePaymentStatus.PAID).all()
        )

        assert len(paid_invoices) == 2

    def test_payment_batch_report(self, db: Session, test_bank_config, test_invoices):
        """Test payment status reporting."""
        banking_service = BankingService(db)

        # Create and process a batch
        batch = banking_service.create_payment_batch(
            bank_code="TEST", processing_date=datetime.now()
        )

        # Get initial report
        report = banking_service.get_payment_status_report(batch.id)

        assert report["batch_number"] == batch.batch_number
        assert report["total_transactions"] == batch.total_transactions
        assert "pending" in report["status_summary"]

        # Update some transactions to different statuses
        transactions = db.query(PaymentTransaction).filter_by(batch_id=batch.id).all()
        if len(transactions) >= 2:
            transactions[0].status = TransactionStatus.SUCCESS
            transactions[1].status = TransactionStatus.FAILED
            transactions[1].bank_response_code = "001"
            transactions[1].bank_response_message = "Insufficient funds"
            db.commit()

        # Get updated report
        report = banking_service.get_payment_status_report(batch.id)

        if len(transactions) >= 2:
            assert "success" in report["status_summary"]
            assert "failed" in report["status_summary"]
            assert len(report["failed_transactions"]) > 0
            assert report["failed_transactions"][0]["error_code"] == "001"

    def test_circuit_breaker_recovery(self, db: Session, test_bank_config):
        """Test circuit breaker recovery after cooldown."""
        banking_service = BankingService(db)

        # Simulate failures to open circuit
        for _ in range(3):
            banking_service._record_circuit_failure("TEST")

        assert banking_service._is_circuit_open("TEST") is True

        # Manually adjust last failure time to simulate cooldown
        banking_service._circuit_breaker_states["TEST"][
            "last_failure"
        ] = datetime.utcnow() - timedelta(minutes=6)

        # Circuit should be closed after cooldown
        assert banking_service._is_circuit_open("TEST") is False

    def test_csv_format_processing(self, db: Session, test_customers, test_invoices):
        """Test CSV format payment file generation."""
        # Create CSV format bank config
        csv_config = BankConfiguration(
            bank_code="CSV_TEST",
            bank_name="CSV Test Bank",
            sftp_host="csv.test.com",
            sftp_port=22,
            sftp_username="csvuser",
            sftp_password="csvpass",
            upload_path="/csv / upload/",
            download_path="/csv / download/",
            file_format="csv",
            encoding="UTF - 8",
            delimiter=", ",
            payment_file_pattern="PAY_{YYYYMMDD}.csv",
            is_active=True,
        )
        db.add(csv_config)

        # Update customers to use CSV bank
        for customer in test_customers:
            customer.bank_code = "CSV_TEST"

        db.commit()

        banking_service = BankingService(db)

        # Create batch
        batch = banking_service.create_payment_batch(
            bank_code="CSV_TEST", processing_date=datetime.now()
        )

        # Generate CSV file
        content = banking_service.generate_payment_file(batch.id)

        # Verify CSV format
        lines = content.strip().split("\n")
        assert "交易序號" in lines[0]  # Header row
        assert len(lines) == batch.total_transactions + 1  # Header + data rows

        # Verify data format
        for i in range(1, len(lines)):
            fields = lines[i].split(", ")
            assert len(fields) >= 6  # At least 6 fields per row

    def _generate_reconciliation_file(self, batch: PaymentBatch) -> str:
        """Generate a mock reconciliation file."""
        lines = []

        # Header
        lines.append(f"H{datetime.now().strftime('%Y % m % d')}TEST001")

        # Detail records
        transactions = batch.transactions
        for i, trans in enumerate(transactions):
            # Simulate some failures
            if i == 0:
                response_code = "000"
                response_msg = "Payment successful"
            else:
                response_code = "001"
                response_msg = "Insufficient funds"

            detail = (
                f"D{str(i + 1).zfill(6)}"
                f"{trans.transaction_id:20}"
                f"REF{str(i + 1).zfill(3):17}"
                f"{response_code}"
                f"{response_msg:100}"
                f"{datetime.now().strftime('%Y % m % d')}"
            )
            lines.append(detail)

        # Trailer
        lines.append(f"T{str(len(transactions)).zfill(6)}")

        return "\r\n".join(lines)
