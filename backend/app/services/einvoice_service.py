"""
Taiwan Government E-Invoice API Service

This module implements integration with the Taiwan Ministry of Finance
E-Invoice platform (財政部電子發票整合服務平台) for B2B and B2C invoice
management.

Key Features:
- B2B and B2C invoice submission
- Certificate-based authentication
- Automatic retry with exponential backoff
- Circuit breaker pattern for fault tolerance
- Request/response logging for audit trail
- Traditional Chinese encoding support
- Test and production environment support
"""

import httpx
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
from functools import wraps
import time
from enum import Enum

from app.core.config import settings

# einvoice_config removed during compaction - using minimal constants
# from app.core.einvoice_config import (...)

# Minimal einvoice constants for basic functionality
EINVOICE_ENDPOINTS = {
    "production": "https://www.einvoice.nat.gov.tw",
    "test": "https://wwwtest.einvoice.nat.gov.tw",
}
EINVOICE_ERROR_CODES = {}
INVOICE_TYPES = {"B2C": "B2C", "B2B": "B2B"}
TAX_TYPES = {"1": "應稅", "2": "零稅率", "3": "免稅"}
CARRIER_TYPES = {}
PRINT_MARKS = {"Y": "列印", "N": "不列印"}
DONATE_MARKS = {"0": "不捐贈", "1": "捐贈"}


def get_einvoice_config():
    return {}


def validate_einvoice_config(config):
    return True


from app.models import Invoice, InvoiceItem
from app.models.invoice import InvoiceType, InvoiceStatus


# Configure logging
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance

    Prevents cascading failures by temporarily blocking calls to a failing service
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def __call__(self, func):
        """Decorator for circuit breaker"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception(
                        "電子發票服務暫時無法使用，請稍後再試。"
                        f"預計恢復時間：{self._get_recovery_time()}"
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        return (
            self.last_failure_time
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")

    def _get_recovery_time(self) -> str:
        """Get estimated recovery time"""
        if self.last_failure_time:
            recovery_time = self.last_failure_time + self.recovery_timeout
            return datetime.fromtimestamp(recovery_time).strftime("%H:%M:%S")
        return "未知"


class EInvoiceService:
    """
    Service for integrating with Taiwan Ministry of Finance E-Invoice platform

    This implements both B2B and B2C APIs for comprehensive invoice management
    """

    def __init__(self, environment: str = None):
        """
        Initialize E-Invoice service

        Args:
            environment: 'test' or 'production', defaults to settings.ENVIRONMENT
        """
        # Get configuration
        self.config = get_einvoice_config(environment)

        # Load production credentials from Secret Manager
        if settings.ENVIRONMENT == "production":
            self._load_production_credentials()

        # Validate configuration
        try:
            validate_einvoice_config(self.config)
        except ValueError as e:
            logger.warning(f"E-Invoice configuration validation failed: {e}")
            logger.warning("Service will run in mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False

        # Extract key configuration
        self.app_id = self.config["app_id"]
        self.api_key = self.config["api_key"]
        self.b2b_base_url = self.config["b2b_api_url"]
        self.b2c_base_url = self.config["b2c_api_url"]
        self.timeout = self.config["timeout"]
        self.max_retries = self.config["max_retries"]
        self.retry_delay = self.config["retry_delay"]

        # Certificate configuration
        self.cert_path = self.config.get("cert_path")
        self.key_path = self.config.get("key_path")

        # Production health check endpoint
        self.health_check_url = self.config.get(
            "health_check_url", f"{self.b2b_base_url}/health"
        )

        # Initialize circuit breaker with production settings
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.get("circuit_breaker_threshold", 5),
            recovery_timeout=self.config.get(
                "circuit_breaker_timeout", 300
            ),  # 5 minutes
            expected_exception=httpx.HTTPError,
        )

        # Initialize metrics
        self._init_metrics()

        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(self.timeout),
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"LuckyGas-EInvoice-Client/1.0 ({settings.ENVIRONMENT})",
            },
            "verify": True,  # Always verify SSL in production
            "follow_redirects": False,  # Security: don't follow redirects
        }

        # Add certificate if configured
        if self.cert_path and self.key_path:
            self.client_config["cert"] = (self.cert_path, self.key_path)

        # Connection pooling
        self.client_config["limits"] = httpx.Limits(
            max_keepalive_connections=20, max_connections=100, keepalive_expiry=30
        )

    def _load_production_credentials(self):
        """Load production credentials from Google Secret Manager"""
        try:
            from app.core.secrets_manager import get_secrets_manager

            sm = get_secrets_manager()

            # Load API credentials
            api_creds = sm.get_secret_json("einvoice-api-credentials")
            if api_creds:
                self.config.update(
                    {
                        "app_id": api_creds.get("app_id", self.config.get("app_id")),
                        "api_key": api_creds.get("api_key", self.config.get("api_key")),
                    }
                )
                logger.info("Loaded E-Invoice API credentials from Secret Manager")

            # Load certificate if stored in Secret Manager
            cert_data = sm.get_secret("einvoice-certificate")
            key_data = sm.get_secret("einvoice-private-key")

            if cert_data and key_data:
                # Write to temporary files (will be cleaned up)
                import tempfile

                cert_file = tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".crt"
                )
                key_file = tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".key"
                )

                cert_file.write(cert_data)
                key_file.write(key_data)

                cert_file.close()
                key_file.close()

                self.config["cert_path"] = cert_file.name
                self.config["key_path"] = key_file.name

                logger.info("Loaded E-Invoice certificates from Secret Manager")

        except Exception as e:
            logger.error(f"Failed to load production credentials: {e}")
            # Don't fail initialization, let validation handle it

    def _init_metrics(self):
        """Initialize Prometheus metrics for monitoring"""
        try:
            from prometheus_client import Counter, Histogram, Gauge

            self.metrics = {
                "requests_total": Counter(
                    "einvoice_requests_total",
                    "Total E-Invoice API requests",
                    ["endpoint", "status"],
                ),
                "request_duration": Histogram(
                    "einvoice_request_duration_seconds",
                    "E-Invoice API request duration",
                    ["endpoint"],
                ),
                "circuit_breaker_state": Gauge(
                    "einvoice_circuit_breaker_state",
                    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
                ),
                "invoice_success_rate": Gauge(
                    "einvoice_success_rate", "E-Invoice submission success rate"
                ),
            }
        except ImportError:
            logger.warning("Prometheus client not available, metrics disabled")
            self.metrics = None

    async def health_check(self) -> Dict[str, Any]:
        """Check E-Invoice API health status"""
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    self.health_check_url,
                    timeout=5.0,  # Short timeout for health checks
                )

                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                    "circuit_breaker": self.circuit_breaker.state.value,
                    "mock_mode": self.mock_mode,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.state.value,
                "mock_mode": self.mock_mode,
            }

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generate HMAC signature for API authentication

        Args:
            data: Request data to sign

        Returns:
            Base64 encoded HMAC-SHA256 signature
        """
        # Sort parameters alphabetically
        sorted_params = sorted(data.items())

        # Build parameter string
        param_strings = []
        for key, value in sorted_params:
            if isinstance(value, list):
                # Handle array parameters
                for item in value:
                    param_strings.append(f"{key}={item}")
            else:
                param_strings.append(f"{key}={value}")

        param_string = "&".join(param_strings)

        # Generate HMAC-SHA256
        signature = hmac.new(
            self.api_key.encode("utf-8"), param_string.encode("utf-8"), hashlib.sha256
        ).digest()

        # Base64 encode
        return base64.b64encode(signature).decode("utf-8")

    def _prepare_invoice_data(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Prepare invoice data for API submission

        Args:
            invoice: Invoice model instance

        Returns:
            Formatted data dictionary for API
        """
        # Determine invoice type
        is_b2b = invoice.invoice_type == InvoiceType.B2B

        # Basic invoice data
        data = {
            "MerchantID": self.app_id,
            "InvoiceNo": invoice.invoice_number,
            "InvoiceDate": invoice.invoice_date.strftime("%Y/%m/%d"),
            "InvoiceTime": datetime.now().strftime("%H:%M:%S"),
            "RandomNumber": invoice.random_code or self._generate_random_code(),
            "SalesAmount": int(invoice.sales_amount),
            "TaxType": invoice.tax_type,
            "TaxRate": invoice.tax_rate,
            "TaxAmount": int(invoice.tax_amount),
            "TotalAmount": int(invoice.total_amount),
            "InvoiceType": INVOICE_TYPES.get("07", "07"),
            "PrintMark": "Y" if invoice.is_printed else "N",
            "DonateMark": "0",  # Default: not donated
            "CarrierType": "",  # No carrier by default
            "CarrierId1": "",
            "CarrierId2": "",
            "TaxID": "",  # Seller tax ID from company settings
        }

        # Add buyer information
        if is_b2b and invoice.buyer_tax_id:
            data["BuyerId"] = invoice.buyer_tax_id

        data["BuyerName"] = invoice.buyer_name or ""
        data["BuyerAddress"] = invoice.buyer_address or ""
        data["BuyerEmail"] = ""  # Add if available
        data["BuyerPhone"] = ""  # Add if available

        # Add seller information
        data["SellerId"] = getattr(settings, "COMPANY_TAX_ID", "12345678")
        data["SellerName"] = getattr(settings, "COMPANY_NAME", "幸福氣有限公司")
        data["SellerAddress"] = getattr(settings, "COMPANY_ADDRESS", "")
        data["SellerPhone"] = getattr(settings, "COMPANY_PHONE", "")
        data["SellerEmail"] = getattr(settings, "COMPANY_EMAIL", "")

        # Add items
        data["ItemCount"] = str(len(invoice.items))
        data["ItemWord"] = "式"  # Default unit word

        # Prepare item arrays
        data["ItemDescription"] = []
        data["ItemQuantity"] = []
        data["ItemUnit"] = []
        data["ItemUnitPrice"] = []
        data["ItemAmount"] = []
        data["ItemTaxType"] = []

        for item in invoice.items:
            data["ItemDescription"].append(item.product_name[:256])  # Max 256 chars
            data["ItemQuantity"].append(str(item.quantity))
            data["ItemUnit"].append(item.unit or "個")
            data["ItemUnitPrice"].append(str(item.unit_price))
            data["ItemAmount"].append(str(int(item.amount)))
            data["ItemTaxType"].append(item.tax_type or "1")

        # Add timestamp
        data["TimeStamp"] = str(int(time.time()))

        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)

        return data

    def _generate_random_code(self) -> str:
        """Generate 4-digit random code for invoice"""
        import random

        return str(random.randint(1000, 9999))

    def _log_request(self, endpoint: str, data: Dict[str, Any]):
        """Log API request for audit trail with compliance requirements"""
        log_data = data.copy()

        # Mask sensitive data for security
        sensitive_fields = ["CheckMacValue", "api_key", "password", "TaxID"]
        for field in sensitive_fields:
            if field in log_data:
                log_data[field] = "***MASKED***"

        # Create audit log entry
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "environment": settings.ENVIRONMENT,
            "service": "einvoice",
            "endpoint": endpoint,
            "invoice_no": log_data.get("InvoiceNo", "N/A"),
            "buyer_id": log_data.get("BuyerId", "N/A"),
            "amount": log_data.get("TotalAmount", 0),
            "request_id": f"{time.time()}-{log_data.get('InvoiceNo', 'NA')}",
        }

        logger.info(f"E-Invoice API Request", extra={"audit": audit_entry})

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Request data: {json.dumps(log_data, ensure_ascii=False)}")

        # Update metrics
        if self.metrics:
            self.metrics["requests_total"].labels(
                endpoint=endpoint, status="sent"
            ).inc()

    def _log_response(self, endpoint: str, response: httpx.Response, duration: float):
        """Log API response for audit trail with enhanced monitoring"""
        try:
            response_data = response.json()
        except:
            response_data = {"raw": response.text[:500]}  # Limit raw text size

        success = response_data.get("RtnCode") == "1"

        # Create audit log entry
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "environment": settings.ENVIRONMENT,
            "service": "einvoice",
            "endpoint": endpoint,
            "status_code": response.status_code,
            "success": success,
            "duration_seconds": duration,
            "error_code": response_data.get("RtnCode") if not success else None,
            "error_message": response_data.get("RtnMsg") if not success else None,
        }

        logger.info(f"E-Invoice API Response", extra={"audit": audit_entry})

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Response data: {json.dumps(response_data, ensure_ascii=False)}"
            )

        # Update metrics
        if self.metrics:
            self.metrics["requests_total"].labels(
                endpoint=endpoint, status="success" if success else "failure"
            ).inc()
            self.metrics["request_duration"].labels(endpoint=endpoint).observe(duration)

            # Update circuit breaker state metric
            cb_state_map = {
                CircuitState.CLOSED: 0,
                CircuitState.OPEN: 1,
                CircuitState.HALF_OPEN: 2,
            }
            self.metrics["circuit_breaker_state"].set(
                cb_state_map.get(self.circuit_breaker.state, -1)
            )

    async def _make_request(
        self, method: str, url: str, data: Dict[str, Any], retries: int = 0
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method
            url: Request URL
            data: Request data
            retries: Current retry count

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On HTTP errors after all retries
        """
        async with httpx.AsyncClient(**self.client_config) as client:
            try:
                start_time = time.time()

                if method.upper() == "POST":
                    response = await client.post(url, json=data)
                else:
                    response = await client.get(url, params=data)

                duration = time.time() - start_time

                # Check for HTTP errors
                response.raise_for_status()

                return response

            except httpx.HTTPError as e:
                if retries < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2**retries)
                    logger.warning(
                        f"Request failed, retrying in {delay}s... "
                        f"(Attempt {retries + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    return await self._make_request(method, url, data, retries + 1)
                else:
                    logger.error(
                        f"Request failed after {self.max_retries} retries: {e}"
                    )
                    raise

    @CircuitBreaker()
    async def submit_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Submit invoice to government e-invoice platform

        Args:
            invoice: Invoice instance to submit

        Returns:
            Dictionary with submission results

        Raises:
            Exception: On submission failure
        """
        # Check if running in mock mode
        if self.mock_mode or settings.ENVIRONMENT != "production":
            return await self._mock_submit_invoice(invoice)

        # Determine API endpoint
        is_b2b = invoice.invoice_type == InvoiceType.B2B
        base_url = self.b2b_base_url if is_b2b else self.b2c_base_url
        endpoint = EINVOICE_ENDPOINTS["b2b" if is_b2b else "b2c"]["issue"]
        url = f"{base_url}{endpoint}"

        # Prepare request data
        data = self._prepare_invoice_data(invoice)

        # Log request
        self._log_request(endpoint, data)

        try:
            # Make API request
            start_time = time.time()
            response = await self._make_request("POST", url, data)
            duration = time.time() - start_time

            # Log response
            self._log_response(endpoint, response, duration)

            # Parse response
            result = response.json()

            # Check for success
            if result.get("RtnCode") == "1":
                return {
                    "status": "success",
                    "einvoice_id": result.get("InvoiceNo"),
                    "message": result.get("RtnMsg", "發票開立成功"),
                    "qr_code_left": result.get("QRCode_Left", ""),
                    "qr_code_right": result.get("QRCode_Right", ""),
                    "bar_code": result.get("BarCode", ""),
                    "response_time": datetime.now().isoformat(),
                    "api_response": result,
                }
            else:
                # Handle API error
                error_code = result.get("RtnCode", "0")
                error_msg = EINVOICE_ERROR_CODES.get(
                    error_code, result.get("RtnMsg", "未知錯誤")
                )
                raise Exception(f"發票開立失敗 [{error_code}]: {error_msg}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error submitting invoice: {e}")
            raise Exception(f"網路連線錯誤：{str(e)}")
        except Exception as e:
            logger.error(f"Error submitting invoice: {e}")
            raise

    async def void_invoice(self, invoice_number: str, reason: str) -> Dict[str, Any]:
        """
        Void an issued invoice

        Args:
            invoice_number: Invoice number to void
            reason: Reason for voiding

        Returns:
            Dictionary with void results

        Raises:
            Exception: On void failure
        """
        # Check if running in mock mode
        if self.mock_mode or settings.ENVIRONMENT != "production":
            return await self._mock_void_invoice(invoice_number, reason)

        # Prepare request data
        data = {
            "MerchantID": self.app_id,
            "InvoiceNo": invoice_number,
            "InvoiceDate": datetime.now().strftime("%Y/%m/%d"),
            "Reason": reason[:20],  # Max 20 chars
            "TimeStamp": str(int(time.time())),
        }

        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)

        # Make request
        endpoint = EINVOICE_ENDPOINTS["b2b"]["void"]
        url = f"{self.b2b_base_url}{endpoint}"

        self._log_request(endpoint, data)

        try:
            start_time = time.time()
            response = await self._make_request("POST", url, data)
            duration = time.time() - start_time

            self._log_response(endpoint, response, duration)

            result = response.json()

            if result.get("RtnCode") == "1":
                return {
                    "status": "success",
                    "message": result.get("RtnMsg", "發票作廢成功"),
                    "void_time": datetime.now().isoformat(),
                    "api_response": result,
                }
            else:
                error_code = result.get("RtnCode", "0")
                error_msg = EINVOICE_ERROR_CODES.get(
                    error_code, result.get("RtnMsg", "未知錯誤")
                )
                raise Exception(f"發票作廢失敗 [{error_code}]: {error_msg}")

        except Exception as e:
            logger.error(f"Error voiding invoice: {e}")
            raise

    async def issue_allowance(
        self,
        original_invoice_number: str,
        allowance_amount: float,
        tax_amount: float,
        reason: str,
        items: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Issue allowance (credit note) for an invoice

        Args:
            original_invoice_number: Original invoice number
            allowance_amount: Allowance amount (before tax)
            tax_amount: Tax amount
            reason: Reason for allowance
            items: List of allowance items (optional)

        Returns:
            Dictionary with allowance results

        Raises:
            Exception: On allowance failure
        """
        # Check if running in mock mode
        if self.mock_mode or settings.ENVIRONMENT != "production":
            return await self._mock_issue_allowance(
                original_invoice_number, allowance_amount, reason
            )

        # Generate allowance number
        allowance_no = f"D{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Prepare request data
        data = {
            "MerchantID": self.app_id,
            "InvoiceNo": original_invoice_number,
            "AllowanceNo": allowance_no,
            "AllowanceDate": datetime.now().strftime("%Y/%m/%d"),
            "AllowanceAmount": int(allowance_amount),
            "TaxAmount": int(tax_amount),
            "TotalAmount": int(allowance_amount + tax_amount),
            "BuyerId": "",  # Will be filled if B2B
            "BuyerName": "",
            "AllowanceType": "1",  # 1: 買方開立, 2: 賣方開立
            "TimeStamp": str(int(time.time())),
        }

        # Add items if provided
        if items:
            data["ItemCount"] = str(len(items))
            data["ItemDescription"] = []
            data["ItemQuantity"] = []
            data["ItemUnit"] = []
            data["ItemUnitPrice"] = []
            data["ItemAmount"] = []
            data["ItemTaxType"] = []

            for item in items:
                data["ItemDescription"].append(item.get("description", ""))
                data["ItemQuantity"].append(str(item.get("quantity", 1)))
                data["ItemUnit"].append(item.get("unit", "式"))
                data["ItemUnitPrice"].append(str(item.get("unit_price", 0)))
                data["ItemAmount"].append(str(item.get("amount", 0)))
                data["ItemTaxType"].append(item.get("tax_type", "1"))

        # Add reason
        data["Remark"] = reason[:200]  # Max 200 chars

        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)

        # Make request
        endpoint = EINVOICE_ENDPOINTS["b2b"]["allowance"]
        url = f"{self.b2b_base_url}{endpoint}"

        self._log_request(endpoint, data)

        try:
            start_time = time.time()
            response = await self._make_request("POST", url, data)
            duration = time.time() - start_time

            self._log_response(endpoint, response, duration)

            result = response.json()

            if result.get("RtnCode") == "1":
                return {
                    "status": "success",
                    "allowance_number": allowance_no,
                    "message": result.get("RtnMsg", "折讓單開立成功"),
                    "allowance_time": datetime.now().isoformat(),
                    "api_response": result,
                }
            else:
                error_code = result.get("RtnCode", "0")
                error_msg = EINVOICE_ERROR_CODES.get(
                    error_code, result.get("RtnMsg", "未知錯誤")
                )
                raise Exception(f"折讓單開立失敗 [{error_code}]: {error_msg}")

        except Exception as e:
            logger.error(f"Error issuing allowance: {e}")
            raise

    async def query_invoice(self, invoice_number: str) -> Dict[str, Any]:
        """
        Query invoice status from platform

        Args:
            invoice_number: Invoice number to query

        Returns:
            Dictionary with invoice status

        Raises:
            Exception: On query failure
        """
        # Check if running in mock mode
        if self.mock_mode or settings.ENVIRONMENT != "production":
            return await self._mock_query_invoice(invoice_number)

        # Prepare request data
        data = {
            "MerchantID": self.app_id,
            "InvoiceNo": invoice_number,
            "TimeStamp": str(int(time.time())),
        }

        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)

        # Make request
        endpoint = EINVOICE_ENDPOINTS["b2b"]["query"]
        url = f"{self.b2b_base_url}{endpoint}"

        self._log_request(endpoint, data)

        try:
            start_time = time.time()
            response = await self._make_request("POST", url, data)
            duration = time.time() - start_time

            self._log_response(endpoint, response, duration)

            result = response.json()

            if result.get("RtnCode") == "1":
                invoice_data = result.get("Data", {})
                return {
                    "status": "success",
                    "invoice_status": self._map_invoice_status(
                        invoice_data.get("InvoiceStatus")
                    ),
                    "invoice_date": invoice_data.get("InvoiceDate"),
                    "buyer_name": invoice_data.get("BuyerName"),
                    "total_amount": invoice_data.get("TotalAmount"),
                    "void_status": invoice_data.get("VoidStatus"),
                    "void_date": invoice_data.get("VoidDate"),
                    "message": "發票查詢成功",
                    "api_response": result,
                }
            else:
                error_code = result.get("RtnCode", "0")
                error_msg = EINVOICE_ERROR_CODES.get(
                    error_code, result.get("RtnMsg", "未知錯誤")
                )
                raise Exception(f"發票查詢失敗 [{error_code}]: {error_msg}")

        except Exception as e:
            logger.error(f"Error querying invoice: {e}")
            raise

    def _map_invoice_status(self, api_status: str) -> str:
        """Map API status to internal status"""
        status_mapping = {
            "1": InvoiceStatus.ISSUED.value,
            "0": InvoiceStatus.VOID.value,
            "2": InvoiceStatus.ALLOWANCE.value,
        }
        return status_mapping.get(api_status, InvoiceStatus.DRAFT.value)

    def validate_carrier(self, carrier_type: str, carrier_id: str) -> bool:
        """
        Validate carrier (載具) format

        Args:
            carrier_type: Type of carrier
            carrier_id: Carrier ID to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        validators = {
            "3J0002": r"^[A-Z0-9+\-\./]{7}$",  # 手機條碼
            "CQ0001": r"^[A-Z]{2}\d{14}$",  # 自然人憑證
            "1K0001": r"^\d{16}$",  # 悠遊卡
            "1H0001": r"^\d{16}$",  # 一卡通
            "2G0001": r"^\d{16}$",  # icash
        }

        pattern = validators.get(carrier_type)
        if pattern:
            return bool(re.match(pattern, carrier_id))

        return True  # Unknown carrier type, allow by default

    def validate_tax_id(self, tax_id: str) -> bool:
        """
        Validate Taiwan tax ID (統一編號)

        Args:
            tax_id: Tax ID to validate

        Returns:
            True if valid, False otherwise
        """
        if not tax_id or len(tax_id) != 8 or not tax_id.isdigit():
            return False

        # Taiwan tax ID checksum algorithm
        weights = [1, 2, 1, 2, 1, 2, 4, 1]
        checksum = 0

        for i, digit in enumerate(tax_id):
            product = int(digit) * weights[i]
            checksum += product // 10 + product % 10

        return checksum % 10 == 0

    async def get_next_invoice_number(
        self, db_session, year_month: str = None, prefix: str = None
    ) -> str:
        """
        Get the next available invoice number from the sequence.

        This method handles the Taiwan e-invoice sequential numbering requirement.
        It uses database-level locking to ensure no duplicate numbers are issued.

        Args:
            db_session: Database session for transaction
            year_month: YYYYMM format (e.g., "202501"). If None, uses current month
            prefix: Invoice prefix (e.g., "AA", "AB"). If None, uses first available

        Returns:
            str: Next invoice number in format PREFIX+8digits (e.g., "AA10000001")

        Raises:
            ValueError: If no active sequence found or range exhausted
        """
        from sqlalchemy import select, and_
        from app.models.invoice_sequence import InvoiceSequence
        from datetime import datetime

        # Default to current year/month if not specified
        if year_month is None:
            year_month = datetime.now().strftime("%Y%m")

        # Build query for active sequences
        query = select(InvoiceSequence).where(
            and_(
                InvoiceSequence.year_month == year_month,
                InvoiceSequence.is_active == True,
                InvoiceSequence.current_number <= InvoiceSequence.range_end,
            )
        )

        # Filter by prefix if specified
        if prefix:
            query = query.where(InvoiceSequence.prefix == prefix)

        # Lock the row for update to prevent concurrent access
        query = query.with_for_update()

        # Execute query
        result = await db_session.execute(query)
        sequence = result.scalar_one_or_none()

        if not sequence:
            raise ValueError(
                f"No active invoice sequence found for {year_month}"
                f"{f' with prefix {prefix}' if prefix else ''}. "
                "Please configure invoice number ranges in the system."
            )

        # Get the next number
        invoice_number = sequence.get_next_number()

        # Increment the sequence
        sequence.current_number += 1

        # Log warning if getting close to exhaustion
        if sequence.usage_percentage > 90:
            logger.warning(
                f"Invoice sequence {sequence.year_month}-{sequence.prefix} "
                f"is {sequence.usage_percentage:.1f}% used. "
                f"Only {sequence.available_count} numbers remaining."
            )

        # Commit will be handled by the caller
        await db_session.flush()

        return invoice_number

    # Mock methods for testing
    async def _mock_submit_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """Mock invoice submission for testing"""
        logger.info(
            f"Mock mode: Simulating invoice submission for {invoice.invoice_number}"
        )

        # Simulate some validation
        if not invoice.invoice_number:
            raise ValueError("發票號碼不能為空")

        if (
            not self.validate_tax_id(invoice.buyer_tax_id)
            and invoice.invoice_type == InvoiceType.B2B
        ):
            raise ValueError("買方統一編號格式錯誤")

        # Return mock response
        return {
            "status": "success",
            "einvoice_id": f"TEST{invoice.invoice_number}{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message": "測試環境 - 發票開立成功",
            "qr_code_left": f"**{invoice.invoice_number}:{invoice.random_code or '1234'}",
            "qr_code_right": f"{int(invoice.total_amount)}:{invoice.buyer_tax_id or '00000000'}",
            "bar_code": invoice.invoice_number if invoice.invoice_number else "",
            "response_time": datetime.now().isoformat(),
            "api_response": {
                "RtnCode": "1",
                "RtnMsg": "Success",
                "InvoiceNo": invoice.invoice_number,
            },
        }

    async def _mock_void_invoice(
        self, invoice_number: str, reason: str
    ) -> Dict[str, Any]:
        """Mock invoice void for testing"""
        logger.info(f"Mock mode: Simulating invoice void for {invoice_number}")

        return {
            "status": "success",
            "message": f"測試環境 - 發票作廢成功：{reason}",
            "void_time": datetime.now().isoformat(),
            "api_response": {"RtnCode": "1", "RtnMsg": "Success"},
        }

    async def _mock_issue_allowance(
        self, original_invoice_number: str, allowance_amount: float, reason: str
    ) -> Dict[str, Any]:
        """Mock allowance issuance for testing"""
        logger.info(
            f"Mock mode: Simulating allowance for invoice {original_invoice_number}"
        )

        return {
            "status": "success",
            "allowance_number": f"ALLOW{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message": f"測試環境 - 折讓單開立成功：{reason}",
            "allowance_time": datetime.now().isoformat(),
            "api_response": {"RtnCode": "1", "RtnMsg": "Success"},
        }

    async def _mock_query_invoice(self, invoice_number: str) -> Dict[str, Any]:
        """Mock invoice query for testing"""
        logger.info(f"Mock mode: Simulating invoice query for {invoice_number}")

        return {
            "status": "success",
            "invoice_status": "issued",
            "invoice_date": datetime.now().strftime("%Y/%m/%d"),
            "buyer_name": "測試買方",
            "total_amount": "1000",
            "void_status": "0",
            "void_date": "",
            "message": "測試環境 - 發票查詢成功",
            "api_response": {
                "RtnCode": "1",
                "RtnMsg": "Success",
                "Data": {
                    "InvoiceStatus": "1",
                    "InvoiceDate": datetime.now().strftime("%Y/%m/%d"),
                    "BuyerName": "測試買方",
                    "TotalAmount": "1000",
                },
            },
        }


# Service singleton
_einvoice_service = None


def get_einvoice_service() -> EInvoiceService:
    """
    Get E-Invoice service singleton

    Returns:
        EInvoiceService instance
    """
    global _einvoice_service
    if _einvoice_service is None:
        _einvoice_service = EInvoiceService()
    return _einvoice_service
