"""
Unit tests for payment service
"""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.customer import Customer, CustomerType
from app.models.invoice import (Invoice, InvoicePaymentStatus, InvoiceStatus,
                                Payment, PaymentMethod)
from app.schemas.payment import PaymentCreate
from app.services.payment_service import PaymentService


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def payment_service(mock_db):
    """Create a payment service instance with mock db"""
    return PaymentService(mock_db)


@pytest.fixture
def sample_invoice():
    """Create a sample invoice"""
    return Invoice(
        id=1,
        invoice_number="INV202401260001",
        customer_id=1,
        customer_name="測試客戶有限公司",
        customer_tax_id="12345678",
        total_amount=Decimal("10000"),
        tax_amount=Decimal("500"),
        grand_total=Decimal("10500"),
        paid_amount=Decimal("0"),
        status=InvoiceStatus.ISSUED,
        invoice_date=date.today()
    )


@pytest.fixture
def sample_payment():
    """Create a sample payment"""
    return Payment(
        id=1,
        payment_number="PAY202401260001",
        invoice_id=1,
        amount=Decimal("5000"),
        payment_method=PaymentMethod.BANK_TRANSFER,
        payment_date=date.today(),
        reference_number="REF123456",
        status=PaymentStatus.PENDING
    )


class TestPaymentService:
    """Test cases for payment service"""
    
    @pytest.mark.asyncio
    async def test_record_payment_cash(self, payment_service, sample_invoice):
        """Test recording cash payment"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=1,
            amount=Decimal("5000"),
            payment_method=PaymentMethod.CASH,
            payment_date=date.today(),
            notes="現金付款"
        )
        
        # Mock database queries
        mock_invoice_result = Mock()
        mock_invoice_result.scalar_one_or_none = Mock(return_value=sample_invoice)
        
        # Mock for payment number generation
        mock_payment_result = Mock()
        mock_payment_result.scalar_one_or_none = Mock(return_value=0)
        
        payment_service.db.execute = AsyncMock(side_effect=[
            mock_invoice_result,  # First call for invoice lookup
            mock_payment_result   # Second call for payment number
        ])
        payment_service.db.add = Mock()
        payment_service.db.commit = AsyncMock()
        payment_service.db.refresh = AsyncMock()
        
        # Act
        result = await payment_service.record_payment(payment_data)
        
        # Assert
        assert result is not None
        assert result.amount == Decimal("5000")
        assert result.payment_method == PaymentMethod.CASH
        assert result.status == PaymentStatus.VERIFIED  # Cash is auto-verified
        assert result.verified_at is not None
        assert result.notes == "現金付款"
        
        # Verify invoice update
        assert sample_invoice.paid_amount == Decimal("5000")
        payment_service.db.add.assert_called_once()
        payment_service.db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_record_payment_bank_transfer(self, payment_service, sample_invoice):
        """Test recording bank transfer payment"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=1,
            amount=Decimal("10500"),  # Full payment
            payment_method=PaymentMethod.BANK_TRANSFER,
            payment_date=date.today(),
            reference_number="BANK123456",
            notes="匯款付款"
        )
        
        # Mock database queries
        mock_invoice_result = Mock()
        mock_invoice_result.scalar_one_or_none = Mock(return_value=sample_invoice)
        
        mock_payment_result = Mock()
        mock_payment_result.scalar_one_or_none = Mock(return_value=0)
        
        payment_service.db.execute = AsyncMock(side_effect=[
            mock_invoice_result,
            mock_payment_result
        ])
        payment_service.db.add = Mock()
        payment_service.db.commit = AsyncMock()
        payment_service.db.refresh = AsyncMock()
        
        # Act
        result = await payment_service.record_payment(payment_data)
        
        # Assert
        assert result is not None
        assert result.amount == Decimal("10500")
        assert result.payment_method == PaymentMethod.BANK_TRANSFER
        assert result.status == PaymentStatus.PENDING  # Bank transfer needs verification
        assert result.verified_at is None
        assert result.reference_number == "BANK123456"
        
        # Verify invoice update
        assert sample_invoice.paid_amount == Decimal("10500")
        assert sample_invoice.status == InvoiceStatus.PAID
        assert sample_invoice.paid_at is not None
    
    @pytest.mark.asyncio
    async def test_record_payment_overpayment(self, payment_service, sample_invoice):
        """Test recording payment that exceeds invoice amount"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=1,
            amount=Decimal("15000"),  # More than invoice amount
            payment_method=PaymentMethod.CASH,
            payment_date=date.today()
        )
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_invoice)
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="付款金額超過發票餘額"):
            await payment_service.record_payment(payment_data)
    
    @pytest.mark.asyncio
    async def test_verify_payment(self, payment_service, sample_payment):
        """Test verifying a pending payment"""
        # Arrange
        sample_payment.status = PaymentStatus.PENDING
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_payment)
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        payment_service.db.commit = AsyncMock()
        
        # Act
        result = await payment_service.verify_payment(1, verified_by=2)
        
        # Assert
        assert result is not None
        assert result.status == PaymentStatus.VERIFIED
        assert result.verified_at is not None
        assert result.verified_by == 2
        payment_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_payment_already_verified(self, payment_service, sample_payment):
        """Test verifying an already verified payment"""
        # Arrange
        sample_payment.status = PaymentStatus.VERIFIED
        sample_payment.verified_at = datetime.now()
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_payment)
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="付款已驗證"):
            await payment_service.verify_payment(1, verified_by=2)
    
    @pytest.mark.asyncio
    async def test_cancel_payment(self, payment_service, sample_payment):
        """Test cancelling a payment"""
        # Arrange
        sample_payment.status = PaymentStatus.PENDING
        invoice = Mock()
        invoice.paid_amount = Decimal("5000")
        sample_payment.invoice = invoice
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_payment)
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        payment_service.db.commit = AsyncMock()
        
        # Act
        result = await payment_service.cancel_payment(1, reason="客戶要求取消")
        
        # Assert
        assert result is not None
        assert result.status == PaymentStatus.CANCELLED
        assert result.cancelled_at is not None
        assert result.cancel_reason == "客戶要求取消"
        
        # Verify invoice amount update
        assert invoice.paid_amount == Decimal("0")  # 5000 - 5000
        payment_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_verified_payment(self, payment_service, sample_payment):
        """Test cancelling a verified payment should fail"""
        # Arrange
        sample_payment.status = PaymentStatus.VERIFIED
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_payment)
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act & Assert
        with pytest.raises(ValueError, match="已驗證的付款無法取消"):
            await payment_service.cancel_payment(1, reason="嘗試取消")
    
    @pytest.mark.asyncio
    async def test_get_payment_summary(self, payment_service):
        """Test getting payment summary for a date range"""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock aggregation results
        mock_results = [
            (PaymentMethod.CASH, PaymentStatus.VERIFIED, Decimal("50000"), 10),
            (PaymentMethod.BANK_TRANSFER, PaymentStatus.VERIFIED, Decimal("80000"), 15),
            (PaymentMethod.BANK_TRANSFER, PaymentStatus.PENDING, Decimal("20000"), 5),
            (PaymentMethod.CHECK, PaymentStatus.VERIFIED, Decimal("30000"), 5),
        ]
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_results)
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        summary = await payment_service.get_payment_summary(start_date, end_date)
        
        # Assert
        assert summary["total_verified"] == Decimal("160000")  # 50000 + 80000 + 30000
        assert summary["total_pending"] == Decimal("20000")
        assert summary["total_amount"] == Decimal("180000")
        assert summary["by_method"][PaymentMethod.CASH] == Decimal("50000")
        assert summary["by_method"][PaymentMethod.BANK_TRANSFER] == Decimal("100000")
        assert summary["by_method"][PaymentMethod.CHECK] == Decimal("30000")
        assert summary["count_by_status"][PaymentStatus.VERIFIED] == 30
        assert summary["count_by_status"][PaymentStatus.PENDING] == 5
    
    @pytest.mark.asyncio
    async def test_generate_payment_number(self, payment_service):
        """Test payment number generation"""
        # Arrange
        with patch('app.services.payment_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 26, 10, 30, 0)
            
            # Mock database query for last payment
            mock_result = Mock()
            mock_result.scalar_one_or_none = Mock(return_value=10)  # Last sequence is 10
            payment_service.db.execute = AsyncMock(return_value=mock_result)
            
            # Act
            payment_number = await payment_service._generate_payment_number()
            
            # Assert
            assert payment_number == "PAY202401260011"  # Next sequence is 11
    
    @pytest.mark.asyncio
    async def test_get_invoice_payments(self, payment_service):
        """Test getting all payments for an invoice"""
        # Arrange
        payments = [
            Payment(
                id=1,
                invoice_id=1,
                amount=Decimal("5000"),
                payment_method=PaymentMethod.CASH,
                status=PaymentStatus.VERIFIED
            ),
            Payment(
                id=2,
                invoice_id=1,
                amount=Decimal("3000"),
                payment_method=PaymentMethod.BANK_TRANSFER,
                status=PaymentStatus.PENDING
            )
        ]
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=payments)))
        payment_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await payment_service.get_invoice_payments(invoice_id=1)
        
        # Assert
        assert len(result) == 2
        assert result[0].amount == Decimal("5000")
        assert result[0].status == PaymentStatus.VERIFIED
        assert result[1].amount == Decimal("3000")
        assert result[1].status == PaymentStatus.PENDING