"""Unit tests for banking service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import io
import paramiko

from sqlalchemy.orm import Session
from app.services.banking_service import (
    BankingService, BankingFormatError, SFTPConnectionError
)
from app.models.banking import (
    PaymentBatch, PaymentTransaction, ReconciliationLog, BankConfiguration,
    PaymentBatchStatus, ReconciliationStatus, TransactionStatus
)
from app.models.invoice import Invoice, InvoicePaymentStatus
from app.models.customer import Customer


@pytest.fixture
def db_session():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def banking_service(db_session):
    """Create banking service instance."""
    return BankingService(db_session)


@pytest.fixture
def bank_config():
    """Sample bank configuration."""
    config = Mock(spec=BankConfiguration)
    config.bank_code = "CTBC"
    config.bank_name = "中國信託"
    config.sftp_host = "sftp.ctbcbank.com"
    config.sftp_port = 22
    config.sftp_username = "testuser"
    config.sftp_password = "testpass"
    config.sftp_private_key = None
    config.upload_path = "/upload/"
    config.download_path = "/download/"
    config.archive_path = "/archive/"
    config.file_format = "fixed_width"
    config.encoding = "UTF-8"
    config.delimiter = None
    config.payment_file_pattern = "PAY_{YYYYMMDD}_{BATCH}.txt"
    config.reconciliation_file_pattern = "REC_{YYYYMMDD}.txt"
    config.is_active = True
    return config


@pytest.fixture
def payment_batch():
    """Sample payment batch."""
    batch = Mock(spec=PaymentBatch)
    batch.id = 1
    batch.batch_number = "CTBC202401201001"
    batch.bank_code = "CTBC"
    batch.status = PaymentBatchStatus.GENERATED
    batch.processing_date = datetime(2024, 1, 20)
    batch.total_transactions = 2
    batch.total_amount = Decimal("5000.00")
    batch.file_content = None
    batch.transactions = []
    return batch


@pytest.fixture
def payment_transactions():
    """Sample payment transactions."""
    transactions = []
    
    # Transaction 1
    t1 = Mock(spec=PaymentTransaction)
    t1.id = 1
    t1.transaction_id = "CTBC202401201001-000001"
    t1.customer_id = 1
    t1.invoice_id = 1
    t1.account_number = "12345678901234"
    t1.account_holder = "張三"
    t1.amount = Decimal("3000.00")
    t1.scheduled_date = datetime(2024, 1, 20)
    t1.status = TransactionStatus.PENDING
    transactions.append(t1)
    
    # Transaction 2
    t2 = Mock(spec=PaymentTransaction)
    t2.id = 2
    t2.transaction_id = "CTBC202401201001-000002"
    t2.customer_id = 2
    t2.invoice_id = 2
    t2.account_number = "98765432109876"
    t2.account_holder = "李四"
    t2.amount = Decimal("2000.00")
    t2.scheduled_date = datetime(2024, 1, 20)
    t2.status = TransactionStatus.PENDING
    transactions.append(t2)
    
    return transactions


class TestBankingService:
    """Test cases for banking service."""
    
    def test_sftp_connection_success(self, banking_service, bank_config):
        """Test successful SFTP connection."""
        with patch('paramiko.Transport') as mock_transport_class:
            mock_transport = Mock()
            mock_transport_class.return_value = mock_transport
            
            with patch('paramiko.SFTPClient.from_transport') as mock_sftp_class:
                mock_sftp = Mock()
                mock_sftp_class.return_value = mock_sftp
                
                with banking_service.get_sftp_client(bank_config) as sftp:
                    assert sftp == mock_sftp
                    mock_transport_class.assert_called_once_with(
                        (bank_config.sftp_host, bank_config.sftp_port)
                    )
                    mock_transport.connect.assert_called_once_with(
                        username=bank_config.sftp_username,
                        password=bank_config.sftp_password
                    )
    
    def test_sftp_connection_with_private_key(self, banking_service, bank_config):
        """Test SFTP connection with private key authentication."""
        bank_config.sftp_private_key = "-----BEGIN RSA PRIVATE KEY-----\ntest_key\n-----END RSA PRIVATE KEY-----"
        
        with patch('paramiko.Transport') as mock_transport_class:
            mock_transport = Mock()
            mock_transport_class.return_value = mock_transport
            
            with patch('paramiko.RSAKey.from_private_key') as mock_key_class:
                mock_key = Mock()
                mock_key_class.return_value = mock_key
                
                with patch('paramiko.SFTPClient.from_transport') as mock_sftp_class:
                    mock_sftp = Mock()
                    mock_sftp_class.return_value = mock_sftp
                    
                    with banking_service.get_sftp_client(bank_config) as sftp:
                        assert sftp == mock_sftp
                        mock_transport.connect.assert_called_once_with(
                            username=bank_config.sftp_username,
                            pkey=mock_key
                        )
    
    def test_sftp_connection_failure(self, banking_service, bank_config):
        """Test SFTP connection failure."""
        with patch('paramiko.Transport') as mock_transport_class:
            mock_transport_class.side_effect = Exception("Connection failed")
            
            with pytest.raises(SFTPConnectionError) as exc_info:
                with banking_service.get_sftp_client(bank_config):
                    pass
            
            assert "Failed to connect to CTBC" in str(exc_info.value)
    
    def test_circuit_breaker(self, banking_service, bank_config):
        """Test circuit breaker functionality."""
        # Simulate multiple failures
        for _ in range(3):
            banking_service._record_circuit_failure(bank_config.bank_code)
        
        # Circuit should be open
        assert banking_service._is_circuit_open(bank_config.bank_code)
        
        # Should raise error when circuit is open
        with pytest.raises(SFTPConnectionError) as exc_info:
            with banking_service.get_sftp_client(bank_config):
                pass
        
        assert "Circuit breaker open" in str(exc_info.value)
    
    def test_generate_fixed_width_payment_file(self, banking_service, payment_batch, payment_transactions, bank_config, db_session):
        """Test generating fixed-width format payment file."""
        payment_batch.transactions = payment_transactions
        
        db_session.query().filter_by().first.side_effect = [payment_batch, bank_config]
        
        content = banking_service.generate_payment_file(payment_batch.id)
        
        # Verify file structure
        lines = content.split('\r\n')
        assert len(lines) == 4  # Header + 2 details + trailer
        
        # Check header
        assert lines[0][0] == 'H'
        assert payment_batch.batch_number in lines[0]
        
        # Check details
        assert lines[1][0] == 'D'
        assert lines[2][0] == 'D'
        
        # Check trailer
        assert lines[3][0] == 'T'
        assert '000002' in lines[3]  # Transaction count
        assert '500000' in lines[3]  # Total amount in cents
    
    def test_generate_csv_payment_file(self, banking_service, payment_batch, payment_transactions, bank_config, db_session):
        """Test generating CSV format payment file."""
        bank_config.file_format = 'csv'
        bank_config.delimiter = ','
        payment_batch.transactions = payment_transactions
        
        db_session.query().filter_by().first.side_effect = [payment_batch, bank_config]
        
        content = banking_service.generate_payment_file(payment_batch.id)
        
        # Verify CSV structure
        lines = content.strip().split('\n')
        assert len(lines) == 3  # Header + 2 data rows
        
        # Check header
        assert '交易序號' in lines[0]
        assert '扣款帳號' in lines[0]
        
        # Check data
        assert '000001' in lines[1]
        assert '12345678901234' in lines[1]
        assert '3000' in lines[1]
    
    def test_upload_payment_file_success(self, banking_service, payment_batch, bank_config, db_session):
        """Test successful payment file upload."""
        payment_batch.file_content = "test content"
        
        db_session.query().filter_by().first.side_effect = [payment_batch, bank_config]
        
        with patch.object(banking_service, 'get_sftp_client') as mock_get_sftp:
            mock_sftp = Mock()
            mock_get_sftp.return_value.__enter__.return_value = mock_sftp
            
            result = banking_service.upload_payment_file(payment_batch.id)
            
            assert result is True
            assert payment_batch.status == PaymentBatchStatus.UPLOADED
            assert payment_batch.uploaded_at is not None
            
            # Verify SFTP upload
            mock_sftp.putfo.assert_called_once()
            db_session.commit.assert_called_once()
    
    def test_upload_payment_file_failure(self, banking_service, payment_batch, bank_config, db_session):
        """Test payment file upload failure."""
        payment_batch.file_content = "test content"
        
        db_session.query().filter_by().first.side_effect = [payment_batch, bank_config]
        
        with patch.object(banking_service, 'get_sftp_client') as mock_get_sftp:
            mock_sftp = Mock()
            mock_sftp.putfo.side_effect = Exception("Upload failed")
            mock_get_sftp.return_value.__enter__.return_value = mock_sftp
            
            result = banking_service.upload_payment_file(payment_batch.id)
            
            assert result is False
            assert payment_batch.status == PaymentBatchStatus.FAILED
            assert payment_batch.error_message == "Upload failed"
            assert payment_batch.retry_count == 1
    
    def test_check_reconciliation_files(self, banking_service, bank_config, db_session):
        """Test checking for new reconciliation files."""
        db_session.query().filter_by().first.side_effect = [bank_config, None, None]
        
        with patch.object(banking_service, 'get_sftp_client') as mock_get_sftp:
            mock_sftp = Mock()
            mock_sftp.listdir.return_value = [
                "REC_20240120.txt",
                "REC_20240119.txt",
                "OTHER_FILE.txt"
            ]
            mock_get_sftp.return_value.__enter__.return_value = mock_sftp
            
            new_files = banking_service.check_reconciliation_files(bank_config.bank_code)
            
            # Should return only reconciliation files that match pattern
            assert len(new_files) == 2
            assert "REC_20240120.txt" in new_files
            assert "REC_20240119.txt" in new_files
    
    def test_process_fixed_width_reconciliation(self, banking_service, bank_config, db_session):
        """Test processing fixed-width reconciliation file."""
        # Mock reconciliation file content
        file_content = """H20240120CTBC001
D000001CTBC202401201001-000001REF001000Payment successful       20240120
D000002CTBC202401201001-000002REF002001Card declined           20240120
T00000200000300000"""
        
        db_session.query().filter_by().first.side_effect = [
            bank_config,
            Mock(transaction_id="CTBC202401201001-000001", invoice_id=1, batch=payment_batch),
            Mock(transaction_id="CTBC202401201001-000002", invoice_id=2, batch=payment_batch),
            Mock(id=1)  # Invoice
        ]
        
        log = ReconciliationLog(
            file_name="REC_20240120.txt",
            file_received_at=datetime.utcnow()
        )
        
        with patch.object(banking_service, 'get_sftp_client') as mock_get_sftp:
            mock_sftp = Mock()
            mock_file = io.BytesIO(file_content.encode('UTF-8'))
            mock_sftp.getfo = Mock(side_effect=lambda remote, local: local.write(mock_file.read()))
            mock_get_sftp.return_value.__enter__.return_value = mock_sftp
            
            result = banking_service.process_reconciliation_file(bank_config.bank_code, "REC_20240120.txt")
            
            # Verify processing results
            assert db_session.add.called
            assert db_session.commit.called
    
    def test_create_payment_batch(self, banking_service, db_session):
        """Test creating a new payment batch."""
        # Mock database queries
        db_session.query().filter().scalar.return_value = 0  # Batch count
        db_session.query().filter_by().scalar.return_value = "fixed_width"  # File format
        
        # Mock invoices
        mock_invoice1 = Mock(
            id=1,
            customer_id=1,
            total_amount=Decimal("1000.00"),
            payment_status=InvoicePaymentStatus.PENDING
        )
        mock_invoice1.customer = Mock(
            payment_method="bank_transfer",
            bank_code="CTBC",
            bank_account_number="12345678",
            bank_account_holder="Test User",
            name="Test User"
        )
        
        db_session.query().join().filter().all.return_value = [mock_invoice1]
        
        batch = banking_service.create_payment_batch(
            bank_code="CTBC",
            processing_date=datetime(2024, 1, 20)
        )
        
        # Verify batch creation
        assert db_session.add.called
        assert db_session.commit.called
    
    def test_get_payment_status_report(self, banking_service, payment_batch, db_session):
        """Test getting payment status report."""
        # Mock batch query
        db_session.query().filter_by().first.return_value = payment_batch
        
        # Mock statistics query
        mock_stats = [
            (TransactionStatus.SUCCESS, 5, Decimal("5000.00")),
            (TransactionStatus.FAILED, 2, Decimal("2000.00")),
            (TransactionStatus.PENDING, 3, Decimal("3000.00"))
        ]
        db_session.query().filter_by().group_by().all.return_value = mock_stats
        
        # Mock failed transactions
        mock_failed = Mock(
            transaction_id="TEST001",
            customer_id=1,
            customer=Mock(name="Test Customer"),
            amount=Decimal("1000.00"),
            bank_response_code="001",
            bank_response_message="Insufficient funds"
        )
        db_session.query().filter_by().all.return_value = [mock_failed]
        
        report = banking_service.get_payment_status_report(payment_batch.id)
        
        assert report['batch_id'] == payment_batch.id
        assert report['batch_number'] == payment_batch.batch_number
        assert len(report['status_summary']) == 3
        assert report['status_summary']['success']['count'] == 5
        assert len(report['failed_transactions']) == 1
    
    def test_file_name_generation(self, banking_service):
        """Test file name generation from pattern."""
        pattern = "PAY_{YYYYMMDD}_{BATCH}.txt"
        batch_number = "CTBC001"
        date = datetime(2024, 1, 20)
        
        file_name = banking_service._generate_file_name(pattern, batch_number, date)
        
        assert file_name == "PAY_20240120_CTBC001.txt"
    
    def test_file_pattern_compilation(self, banking_service):
        """Test file pattern compilation to regex."""
        pattern = "REC_{YYYYMMDD}.txt"
        regex = banking_service._compile_file_pattern(pattern)
        
        assert regex.match("REC_20240120.txt")
        assert not regex.match("PAY_20240120.txt")
        assert not regex.match("REC_2024-01-20.txt")
    
    def test_format_amount(self, banking_service):
        """Test amount formatting for banking files."""
        assert banking_service._format_amount(Decimal("100.00")) == "0000000010000"
        assert banking_service._format_amount(Decimal("1.50")) == "0000000000150"
        assert banking_service._format_amount(Decimal("0.01")) == "0000000000001"
    
    def test_format_fixed_width(self, banking_service):
        """Test fixed-width field formatting."""
        fields = [
            ("ABC", 5),
            ("12345678", 5),
            ("", 3)
        ]
        
        result = banking_service._format_fixed_width(fields)
        
        assert result == "ABC  12345   "
        assert len(result) == 13