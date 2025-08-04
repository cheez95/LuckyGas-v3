"""
Unit tests for invoice service
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.customer import Customer, CustomerType
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, InvoiceType
from app.models.order import Order, OrderStatus
from app.schemas.invoice import InvoiceCreate
from app.services.invoice_service import InvoiceService


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def invoice_service(mock_db):
    """Create an invoice service instance with mock db"""
    return InvoiceService(mock_db)


@pytest.fixture
def sample_customer():
    """Create a sample customer"""
    return Customer(
        id=1,
        customer_code="C001",
        short_name="測試客戶",
        full_name="測試客戶有限公司",
        tax_id="12345678",
        address="台北市信義區信義路100號",
        phone="0912345678",
        customer_type=CustomerType.COMMERCIAL,
        credit_limit=Decimal("100000"),
        payment_terms=30,
    )


@pytest.fixture
def sample_order(sample_customer):
    """Create a sample order"""
    return Order(
        id=1,
        order_number="ORD20240126001",
        customer_id=1,
        customer=sample_customer,
        order_date=datetime.now(),
        scheduled_date=date.today(),
        status=OrderStatus.DELIVERED,
        qty_50kg=2,
        qty_20kg=3,
        qty_16kg=0,
        qty_10kg=5,
        qty_4kg=0,
        unit_price_50kg=Decimal("1500"),
        unit_price_20kg=Decimal("600"),
        unit_price_16kg=Decimal("480"),
        unit_price_10kg=Decimal("300"),
        unit_price_4kg=Decimal("120"),
        total_amount=Decimal("6300"),  # (2*1500) + (3*600) + (5*300)
        is_taxable=True,
    )


class TestInvoiceService:
    """Test cases for invoice service"""

    @pytest.mark.asyncio
    async def test_create_invoice_from_order_b2b(self, invoice_service, sample_order):
        """Test creating B2B invoice from order"""
        # Arrange
        sample_order.customer.tax_id = "12345678"  # Has tax ID -> B2B

        # Mock the database add and commit
        invoice_service.db.add = Mock()
        invoice_service.db.commit = AsyncMock()
        invoice_service.db.refresh = AsyncMock()

        # Act
        result = await invoice_service.create_invoice_from_order(sample_order)

        # Assert
        assert result is not None
        assert result.invoice_type == InvoiceType.B2B
        assert result.customer_id == sample_order.customer_id
        assert result.customer_name == sample_order.customer.full_name
        assert result.customer_tax_id == sample_order.customer.tax_id
        assert result.total_amount == sample_order.total_amount
        assert result.tax_amount == sample_order.total_amount * Decimal(
            "0.05"
        )  # 5% tax
        assert result.grand_total == sample_order.total_amount * Decimal("1.05")
        assert len(result.items) == 3  # 50kg, 20kg, 10kg products

        # Verify database operations
        invoice_service.db.add.assert_called_once()
        invoice_service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_from_order_b2c(self, invoice_service, sample_order):
        """Test creating B2C invoice from order"""
        # Arrange
        sample_order.customer.tax_id = None  # No tax ID -> B2C

        # Mock the database operations
        invoice_service.db.add = Mock()
        invoice_service.db.commit = AsyncMock()
        invoice_service.db.refresh = AsyncMock()

        # Act
        result = await invoice_service.create_invoice_from_order(sample_order)

        # Assert
        assert result is not None
        assert result.invoice_type == InvoiceType.B2C
        assert result.customer_id == sample_order.customer_id
        assert result.customer_name == sample_order.customer.full_name
        assert result.customer_tax_id is None
        assert result.total_amount == sample_order.total_amount
        assert result.tax_amount == sample_order.total_amount * Decimal("0.05")
        assert result.grand_total == sample_order.total_amount * Decimal("1.05")

    @pytest.mark.asyncio
    async def test_generate_invoice_number(self, invoice_service):
        """Test invoice number generation"""
        # Arrange
        with patch("app.services.invoice_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 26, 10, 30, 0)

            # Mock database query for last invoice
            mock_result = Mock()
            mock_result.scalar_one_or_none = Mock(return_value=5)  # Last sequence is 5
            invoice_service.db.execute = AsyncMock(return_value=mock_result)

            # Act
            invoice_number = await invoice_service._generate_invoice_number()

            # Assert
            assert invoice_number == "INV202401260006"  # Next sequence is 6

    @pytest.mark.asyncio
    async def test_calculate_invoice_items(self, invoice_service, sample_order):
        """Test invoice items calculation"""
        # Act
        items = await invoice_service._calculate_invoice_items(sample_order)

        # Assert
        assert len(items) == 3  # Only non-zero quantities

        # Check 50kg item
        item_50kg = next(item for item in items if item.description == "瓦斯 50公斤")
        assert item_50kg.quantity == 2
        assert item_50kg.unit_price == Decimal("1500")
        assert item_50kg.amount == Decimal("3000")

        # Check 20kg item
        item_20kg = next(item for item in items if item.description == "瓦斯 20公斤")
        assert item_20kg.quantity == 3
        assert item_20kg.unit_price == Decimal("600")
        assert item_20kg.amount == Decimal("1800")

        # Check 10kg item
        item_10kg = next(item for item in items if item.description == "瓦斯 10公斤")
        assert item_10kg.quantity == 5
        assert item_10kg.unit_price == Decimal("300")
        assert item_10kg.amount == Decimal("1500")

    @pytest.mark.asyncio
    async def test_void_invoice(self, invoice_service):
        """Test voiding an invoice"""
        # Arrange
        invoice = Invoice(
            id=1,
            invoice_number="INV202401260001",
            status=InvoiceStatus.ISSUED,
            void_reason=None,
        )

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=invoice)
        invoice_service.db.execute = AsyncMock(return_value=mock_result)
        invoice_service.db.commit = AsyncMock()

        # Act
        result = await invoice_service.void_invoice(1, "客戶要求作廢")

        # Assert
        assert result is not None
        assert result.status == InvoiceStatus.VOIDED
        assert result.void_reason == "客戶要求作廢"
        assert result.voided_at is not None
        invoice_service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_void_invoice_already_voided(self, invoice_service):
        """Test voiding an already voided invoice"""
        # Arrange
        invoice = Invoice(
            id=1,
            invoice_number="INV202401260001",
            status=InvoiceStatus.VOIDED,
            void_reason="已作廢",
        )

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=invoice)
        invoice_service.db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError, match="發票已作廢"):
            await invoice_service.void_invoice(1, "再次作廢")

    @pytest.mark.asyncio
    async def test_update_invoice_payment_status(self, invoice_service):
        """Test updating invoice payment status"""
        # Arrange
        invoice = Invoice(
            id=1,
            invoice_number="INV202401260001",
            grand_total=Decimal("10000"),
            paid_amount=Decimal("0"),
            status=InvoiceStatus.ISSUED,
        )

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=invoice)
        invoice_service.db.execute = AsyncMock(return_value=mock_result)
        invoice_service.db.commit = AsyncMock()

        # Act - Partial payment
        result = await invoice_service.update_payment_status(1, Decimal("5000"))

        # Assert
        assert result.paid_amount == Decimal("5000")
        assert result.status == InvoiceStatus.ISSUED  # Still unpaid

        # Act - Full payment
        result = await invoice_service.update_payment_status(
            1, Decimal("5000")
        )  # Another 5000

        # Assert
        assert result.paid_amount == Decimal("10000")
        assert result.status == InvoiceStatus.PAID
        assert result.paid_at is not None

    @pytest.mark.asyncio
    async def test_get_invoice_by_number(self, invoice_service):
        """Test getting invoice by number"""
        # Arrange
        expected_invoice = Invoice(
            id=1, invoice_number="INV202401260001", status=InvoiceStatus.ISSUED
        )

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=expected_invoice)
        invoice_service.db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await invoice_service.get_by_invoice_number("INV202401260001")

        # Assert
        assert result is not None
        assert result.invoice_number == "INV202401260001"
        assert result.status == InvoiceStatus.ISSUED

    @pytest.mark.asyncio
    async def test_create_credit_note(self, invoice_service):
        """Test creating credit note for invoice"""
        # Arrange
        original_invoice = Invoice(
            id=1,
            invoice_number="INV202401260001",
            customer_id=1,
            customer_name="測試客戶有限公司",
            customer_tax_id="12345678",
            invoice_type=InvoiceType.B2B,
            total_amount=Decimal("10000"),
            tax_amount=Decimal("500"),
            grand_total=Decimal("10500"),
            status=InvoiceStatus.ISSUED,
        )

        # Mock database operations
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=original_invoice)
        invoice_service.db.execute = AsyncMock(return_value=mock_result)
        invoice_service.db.add = Mock()
        invoice_service.db.commit = AsyncMock()
        invoice_service.db.refresh = AsyncMock()

        # Act
        credit_note = await invoice_service.create_credit_note(
            invoice_id=1, amount=Decimal("2000"), reason="商品退貨"
        )

        # Assert
        assert credit_note is not None
        assert credit_note.original_invoice_id == 1
        assert credit_note.amount == Decimal("2000")
        assert credit_note.tax_amount == Decimal("100")  # 5% of 2000
        assert credit_note.total_amount == Decimal("2100")
        assert credit_note.reason == "商品退貨"
        invoice_service.db.add.assert_called_once()
        invoice_service.db.commit.assert_called_once()
