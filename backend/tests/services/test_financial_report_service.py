"""
Unit tests for financial report service
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.customer import Customer, CustomerType
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.services.financial_report_service import FinancialReportService


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def report_service(mock_db):
    """Create a financial report service instance with mock db"""
    return FinancialReportService(mock_db)


@pytest.fixture
def sample_invoices():
    """Create sample invoices for testing"""
    return [
        Invoice(
            id=1,
            invoice_number="INV202401010001",
            customer_id=1,
            customer_name="客戶A有限公司",
            customer_tax_id="12345678",
            invoice_type=InvoiceType.B2B,
            total_amount=Decimal("10000"),
            tax_amount=Decimal("500"),
            grand_total=Decimal("10500"),
            paid_amount=Decimal("10500"),
            status=InvoiceStatus.PAID,
            invoice_date=date(2024, 1, 1),
            paid_at=datetime(2024, 1, 5)
        ),
        Invoice(
            id=2,
            invoice_number="INV202401020001",
            customer_id=2,
            customer_name="客戶B股份有限公司",
            customer_tax_id="23456789",
            invoice_type=InvoiceType.B2B,
            total_amount=Decimal("20000"),
            tax_amount=Decimal("1000"),
            grand_total=Decimal("21000"),
            paid_amount=Decimal("0"),
            status=InvoiceStatus.ISSUED,
            invoice_date=date(2024, 1, 2)
        ),
        Invoice(
            id=3,
            invoice_number="INV202401030001",
            customer_id=3,
            customer_name="王小明",
            customer_tax_id=None,
            invoice_type=InvoiceType.B2C,
            total_amount=Decimal("5000"),
            tax_amount=Decimal("250"),
            grand_total=Decimal("5250"),
            paid_amount=Decimal("5250"),
            status=InvoiceStatus.PAID,
            invoice_date=date(2024, 1, 3),
            paid_at=datetime(2024, 1, 3)
        )
    ]


class TestFinancialReportService:
    """Test cases for financial report service"""
    
    @pytest.mark.asyncio
    async def test_get_revenue_summary(self, report_service, sample_invoices):
        """Test getting revenue summary for a period"""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_invoices)))
        report_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        summary = await report_service.get_revenue_summary(start_date, end_date)
        
        # Assert
        assert summary["period"]["start"] == start_date
        assert summary["period"]["end"] == end_date
        assert summary["total_revenue"] == Decimal("35000")  # 10000 + 20000 + 5000
        assert summary["total_tax"] == Decimal("1750")      # 500 + 1000 + 250
        assert summary["total_amount"] == Decimal("36750")  # 10500 + 21000 + 5250
        assert summary["paid_amount"] == Decimal("15750")   # 10500 + 5250
        assert summary["unpaid_amount"] == Decimal("21000") # 21000
        assert summary["invoice_count"] == 3
        assert summary["paid_count"] == 2
        assert summary["unpaid_count"] == 1
        
        # Check breakdown by type
        assert summary["by_type"]["B2B"]["revenue"] == Decimal("30000")
        assert summary["by_type"]["B2B"]["count"] == 2
        assert summary["by_type"]["B2C"]["revenue"] == Decimal("5000")
        assert summary["by_type"]["B2C"]["count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_accounts_receivable_aging(self, report_service):
        """Test getting accounts receivable aging report"""
        # Arrange
        as_of_date = date(2024, 1, 31)
        
        # Create invoices with different aging periods
        unpaid_invoices = [
            Invoice(
                id=1,
                customer_id=1,
                customer_name="客戶A",
                grand_total=Decimal("10000"),
                paid_amount=Decimal("0"),
                status=InvoiceStatus.ISSUED,
                invoice_date=date(2024, 1, 25),  # 6 days ago
                due_date=date(2024, 2, 24)       # Not due yet
            ),
            Invoice(
                id=2,
                customer_id=2,
                customer_name="客戶B",
                grand_total=Decimal("20000"),
                paid_amount=Decimal("5000"),
                status=InvoiceStatus.ISSUED,
                invoice_date=date(2023, 12, 1),   # 61 days ago
                due_date=date(2023, 12, 31)       # 31 days overdue
            ),
            Invoice(
                id=3,
                customer_id=3,
                customer_name="客戶C",
                grand_total=Decimal("30000"),
                paid_amount=Decimal("0"),
                status=InvoiceStatus.ISSUED,
                invoice_date=date(2023, 10, 1),   # 122 days ago
                due_date=date(2023, 10, 31)       # 92 days overdue
            )
        ]
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=unpaid_invoices)))
        report_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        aging_report = await report_service.get_accounts_receivable_aging(as_of_date)
        
        # Assert
        assert aging_report["as_of_date"] == as_of_date
        assert aging_report["total_receivable"] == Decimal("55000")  # 10000 + 15000 + 30000
        
        # Check aging buckets
        buckets = aging_report["aging_buckets"]
        assert buckets["current"]["amount"] == Decimal("10000")
        assert buckets["current"]["count"] == 1
        assert buckets["1-30"]["amount"] == Decimal("0")
        assert buckets["1-30"]["count"] == 0
        assert buckets["31-60"]["amount"] == Decimal("15000")  # 20000 - 5000
        assert buckets["31-60"]["count"] == 1
        assert buckets["61-90"]["amount"] == Decimal("0")
        assert buckets["61-90"]["count"] == 0
        assert buckets["over_90"]["amount"] == Decimal("30000")
        assert buckets["over_90"]["count"] == 1
        
        # Check by customer
        assert len(aging_report["by_customer"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_tax_report(self, report_service, sample_invoices):
        """Test getting tax report for government filing"""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_invoices)))
        report_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        tax_report = await report_service.get_tax_report(start_date, end_date)
        
        # Assert
        assert tax_report["period"]["start"] == start_date
        assert tax_report["period"]["end"] == end_date
        assert tax_report["total_sales"] == Decimal("35000")
        assert tax_report["total_tax"] == Decimal("1750")
        
        # Check B2B vs B2C breakdown
        assert tax_report["b2b"]["sales"] == Decimal("30000")
        assert tax_report["b2b"]["tax"] == Decimal("1500")
        assert tax_report["b2b"]["count"] == 2
        assert tax_report["b2c"]["sales"] == Decimal("5000")
        assert tax_report["b2c"]["tax"] == Decimal("250")
        assert tax_report["b2c"]["count"] == 1
        
        # Check invoice details
        assert len(tax_report["invoices"]) == 3
        assert tax_report["invoices"][0]["invoice_number"] == "INV202401010001"
    
    @pytest.mark.asyncio
    async def test_get_cash_flow_report(self, report_service):
        """Test getting cash flow report"""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)
        
        # Mock payment data
        mock_payments = [
            (date(2024, 1, 1), Decimal("10000")),
            (date(2024, 1, 3), Decimal("15000")),
            (date(2024, 1, 5), Decimal("8000")),
        ]
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_payments)
        report_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        cash_flow = await report_service.get_cash_flow_report(start_date, end_date)
        
        # Assert
        assert cash_flow["period"]["start"] == start_date
        assert cash_flow["period"]["end"] == end_date
        assert cash_flow["total_inflow"] == Decimal("33000")
        assert len(cash_flow["daily_flow"]) == 7  # 7 days
        
        # Check specific days
        assert cash_flow["daily_flow"][0]["date"] == date(2024, 1, 1)
        assert cash_flow["daily_flow"][0]["inflow"] == Decimal("10000")
        assert cash_flow["daily_flow"][2]["date"] == date(2024, 1, 3)
        assert cash_flow["daily_flow"][2]["inflow"] == Decimal("15000")
    
    @pytest.mark.asyncio
    async def test_get_customer_statement(self, report_service):
        """Test getting customer statement"""
        # Arrange
        customer_id = 1
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock customer
        customer = Customer(
            id=1,
            customer_code="C001",
            short_name="測試客戶",
            full_name="測試客戶有限公司",
            tax_id="12345678"
        )
        
        # Mock transactions
        invoices = [sample_invoices[0]]  # Only first invoice for this customer
        
        # Mock database queries
        mock_customer_result = Mock()
        mock_customer_result.scalar_one_or_none = Mock(return_value=customer)
        
        mock_invoice_result = Mock()
        mock_invoice_result.scalars = Mock(return_value=Mock(all=Mock(return_value=invoices)))
        
        report_service.db.execute = AsyncMock(side_effect=[
            mock_customer_result,
            mock_invoice_result
        ])
        
        # Act
        statement = await report_service.get_customer_statement(
            customer_id, start_date, end_date
        )
        
        # Assert
        assert statement["customer"]["id"] == 1
        assert statement["customer"]["name"] == "測試客戶有限公司"
        assert statement["period"]["start"] == start_date
        assert statement["period"]["end"] == end_date
        assert statement["summary"]["total_invoiced"] == Decimal("10500")
        assert statement["summary"]["total_paid"] == Decimal("10500")
        assert statement["summary"]["balance"] == Decimal("0")
        assert len(statement["transactions"]) == 1
    
    @pytest.mark.asyncio
    async def test_generate_401_file(self, report_service):
        """Test generating 401 file for tax reporting"""
        # Arrange
        year = 2024
        month = 1
        
        # Mock invoice data
        b2b_invoices = [sample_invoices[0], sample_invoices[1]]  # Only B2B invoices
        
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=b2b_invoices)))
        report_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        file_content = await report_service.generate_401_file(year, month)
        
        # Assert
        assert isinstance(file_content, bytes)
        
        # Parse the content
        lines = file_content.decode('big5').strip().split('\n')
        assert len(lines) == 2  # 2 B2B invoices
        
        # Check first line format
        first_line = lines[0]
        assert first_line.startswith("401")  # Format code
        assert "INV202401010001" in first_line
        assert "12345678" in first_line  # Tax ID
        assert "10000" in first_line     # Amount
        assert "500" in first_line       # Tax
    
    @pytest.mark.asyncio
    async def test_generate_403_file(self, report_service):
        """Test generating 403 file for B2C sales"""
        # Arrange
        year = 2024
        month = 1
        
        # Mock B2C summary data
        mock_result = Mock()
        mock_result.one = Mock(return_value=(Decimal("5000"), Decimal("250"), 1))
        report_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        file_content = await report_service.generate_403_file(year, month)
        
        # Assert
        assert isinstance(file_content, bytes)
        
        # Parse the content
        content = file_content.decode('big5').strip()
        assert content.startswith("403")  # Format code
        assert "202401" in content        # Year and month
        assert "5000" in content          # Total sales
        assert "250" in content           # Total tax
        assert "1" in content             # Number of invoices
    
    @pytest.mark.asyncio
    async def test_export_financial_report(self, report_service):
        """Test exporting financial report to Excel"""
        # Arrange
        report_data = {
            "summary": {
                "total_revenue": Decimal("100000"),
                "total_tax": Decimal("5000"),
                "total_paid": Decimal("80000")
            },
            "details": [
                {
                    "date": date(2024, 1, 1),
                    "customer": "客戶A",
                    "amount": Decimal("10000")
                }
            ]
        }
        
        # Act
        excel_file = await report_service.export_financial_report(
            report_data,
            "revenue_report"
        )
        
        # Assert
        assert isinstance(excel_file, BytesIO)
        assert excel_file.getvalue() != b''  # File has content