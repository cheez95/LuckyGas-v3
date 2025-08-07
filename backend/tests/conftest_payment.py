"""
Pytest configuration for payment/invoice feature tests.

This module provides markers and fixtures for conditionally running
payment and invoice related tests based on feature flags.
"""

import pytest
from app.core.config import settings


# Custom markers for payment/invoice tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_payment: mark test as requiring payment features to be enabled"
    )
    config.addinivalue_line(
        "markers", "requires_invoice: mark test as requiring invoice features to be enabled"
    )
    config.addinivalue_line(
        "markers", "requires_banking: mark test as requiring banking features to be enabled"
    )
    config.addinivalue_line(
        "markers", "requires_financial: mark test as requiring financial reports to be enabled"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests based on feature flags."""
    skip_payment = pytest.mark.skip(reason="Payment system is disabled")
    skip_invoice = pytest.mark.skip(reason="Invoice system is disabled")
    skip_banking = pytest.mark.skip(reason="Banking system is disabled")
    skip_financial = pytest.mark.skip(reason="Financial reports are disabled")
    
    for item in items:
        # Skip payment tests if payment system is disabled
        if "requires_payment" in item.keywords and not settings.ENABLE_PAYMENT_SYSTEM:
            item.add_marker(skip_payment)
        
        # Skip invoice tests if invoice system is disabled
        if "requires_invoice" in item.keywords and not settings.ENABLE_INVOICE_SYSTEM:
            item.add_marker(skip_invoice)
        
        # Skip banking tests if banking system is disabled
        if "requires_banking" in item.keywords and not settings.ENABLE_BANKING_SYSTEM:
            item.add_marker(skip_banking)
        
        # Skip financial report tests if financial reports are disabled
        if "requires_financial" in item.keywords and not settings.ENABLE_FINANCIAL_REPORTS:
            item.add_marker(skip_financial)


# Decorators for conditional test execution
requires_payment = pytest.mark.requires_payment
requires_invoice = pytest.mark.requires_invoice
requires_banking = pytest.mark.requires_banking
requires_financial = pytest.mark.requires_financial


# Helper fixture to check if any payment feature is enabled
@pytest.fixture
def payment_features_enabled():
    """Check if any payment-related feature is enabled."""
    return any([
        settings.ENABLE_PAYMENT_SYSTEM,
        settings.ENABLE_INVOICE_SYSTEM,
        settings.ENABLE_BANKING_SYSTEM,
        settings.ENABLE_FINANCIAL_REPORTS
    ])


# Skip entire test modules based on feature flags
def pytest_ignore_collect(collection_path, config):
    """Ignore entire test files if features are disabled."""
    path_str = str(collection_path)
    
    # Skip payment test files
    if "test_payment" in path_str and not settings.ENABLE_PAYMENT_SYSTEM:
        return True
    
    # Skip invoice test files
    if "test_invoice" in path_str and not settings.ENABLE_INVOICE_SYSTEM:
        return True
    
    # Skip banking test files
    if "test_banking" in path_str and not settings.ENABLE_BANKING_SYSTEM:
        return True
    
    # Skip financial report test files
    if "test_financial" in path_str and not settings.ENABLE_FINANCIAL_REPORTS:
        return True
    
    return False