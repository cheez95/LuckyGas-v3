"""
Contract Testing Configuration for Lucky Gas API

This module provides configuration and utilities for contract testing
using Pact framework to ensure API stability and prevent breaking changes.
"""

import os
import pytest
from typing import Generator
from pact import Consumer, Provider
from pact.pact import Pact

# Contract testing configuration
PACT_BROKER_URL = os.environ.get("PACT_BROKER_URL", "http://localhost:9292")
PACT_BROKER_USERNAME = os.environ.get("PACT_BROKER_USERNAME", "")
PACT_BROKER_PASSWORD = os.environ.get("PACT_BROKER_PASSWORD", "")

# Application details
CONSUMER_NAME = "lucky-gas-frontend"
PROVIDER_NAME = "lucky-gas-backend"
PACT_DIR = os.path.join(os.path.dirname(__file__), "pacts")
PACT_FILE_WRITE_MODE = "overwrite"

# Mock server configuration
MOCK_HOST = "localhost"
MOCK_PORT = 8888


@pytest.fixture(scope="session")
def pact() -> Generator[Pact, None, None]:
    """
    Create a Pact instance for consumer contract testing.

    This fixture sets up a mock provider server that the consumer
    tests can interact with to generate contract specifications.
    """
    consumer = Consumer(CONSUMER_NAME)
    provider = Provider(PROVIDER_NAME)

    pact = consumer.has_pact_with(
        provider,
        host_name=MOCK_HOST,
        port=MOCK_PORT,
        pact_dir=PACT_DIR,
        file_write_mode=PACT_FILE_WRITE_MODE,
    )

    pact.start_service()

    yield pact

    pact.stop_service()


@pytest.fixture
def mock_provider_url() -> str:
    """Get the URL of the mock provider server."""
    return f"http://{MOCK_HOST}:{MOCK_PORT}"


@pytest.fixture
def auth_headers() -> dict:
    """Common authentication headers for API requests."""
    return {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


def publish_pact_to_broker(pact_file: str, version: str = "1.0.0") -> None:
    """
    Publish pact file to Pact Broker.

    Args:
        pact_file: Path to the pact file
        version: Consumer version
    """
    if not PACT_BROKER_URL:
        print("Pact Broker URL not configured, skipping publish")
        return

    import subprocess

    cmd = [
        "pact-broker",
        "publish",
        pact_file,
        "--consumer-app-version",
        version,
        "--broker-base-url",
        PACT_BROKER_URL,
    ]

    if PACT_BROKER_USERNAME and PACT_BROKER_PASSWORD:
        cmd.extend(
            [
                "--broker-username",
                PACT_BROKER_USERNAME,
                "--broker-password",
                PACT_BROKER_PASSWORD,
            ]
        )

    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully published pact to broker: {PACT_BROKER_URL}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to publish pact to broker: {e}")


def verify_pact_version_compatibility(
    consumer_version: str, provider_version: str
) -> bool:
    """
    Verify that consumer and provider versions are compatible.

    Args:
        consumer_version: Consumer application version
        provider_version: Provider application version

    Returns:
        True if versions are compatible
    """
    # In a real implementation, this would check with Pact Broker
    # or use version compatibility rules
    return True


# Test data generators for consistent contract testing
def generate_customer_data(customer_id: str = "CUST0001") -> dict:
    """Generate consistent customer data for contract tests."""
    return {
        "id": customer_id,
        "name": "測試客戶",
        "phone": "0912345678",
        "address": "台北市信義區測試路123號",
        "area": "信義區",
        "is_active": True,
        "created_at": "2024-01-20T00:00:00Z",
    }


def generate_order_data(order_id: int = 1) -> dict:
    """Generate consistent order data for contract tests."""
    return {
        "id": order_id,
        "customer_id": "CUST0001",
        "order_date": "2024-01-20T00:00:00Z",
        "status": "pending",
        "payment_status": "unpaid",
        "is_urgent": False,
        "items": [{"product_id": 1, "quantity": 2, "unit_price": 800.0}],
        "total_amount": 1600.0,
    }


def generate_auth_token_response() -> dict:
    """Generate consistent auth token response for contract tests."""
    return {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_type": "bearer",
        "expires_in": 3600,
    }


def generate_prediction_data() -> dict:
    """Generate consistent prediction data for contract tests."""
    return {
        "customer_id": "CUST0001",
        "prediction_date": "2024-01-21",
        "predicted_demand": 2,
        "confidence": 0.85,
        "factors": {
            "days_since_last_order": 25,
            "average_consumption": 2.1,
            "seasonal_factor": 1.05,
        },
    }
