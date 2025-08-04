"""
Google API Error Handler with retry logic
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union

import aiohttp

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GoogleAPIError(Exception):
    """Base exception for Google API errors"""

    def __init__(
        self,
        message: str,
        status_code: int,
        details: Optional[Dict] = None,
        api_type: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}
        self.api_type = api_type
        self.endpoint = endpoint
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/reporting"""
        return {
            "message": str(self),
            "status_code": self.status_code,
            "details": self.details,
            "api_type": self.api_type,
            "endpoint": self.endpoint,
            "timestamp": self.timestamp.isoformat(),
        }


class APIErrorType(Enum):
    """Types of API errors for classification"""

    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_API_KEY = "invalid_api_key"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class GoogleAPIErrorHandler:
    """Comprehensive error handler for Google API calls with retry logic"""

    # Map status codes to error types
    ERROR_MAPPING = {
        400: APIErrorType.INVALID_REQUEST,
        401: APIErrorType.INVALID_API_KEY,
        403: APIErrorType.PERMISSION_DENIED,
        404: APIErrorType.NOT_FOUND,
        429: APIErrorType.RATE_LIMIT,
        500: APIErrorType.INTERNAL_ERROR,
        502: APIErrorType.SERVICE_UNAVAILABLE,
        503: APIErrorType.SERVICE_UNAVAILABLE,
        504: APIErrorType.TIMEOUT,
    }

    # Retry strategies for different error types
    RETRY_STRATEGIES = {
        APIErrorType.RATE_LIMIT: {
            "max_retries": 5,
            "base_delay": 1.0,
            "max_delay": 60.0,
            "exponential": True,
        },
        APIErrorType.SERVICE_UNAVAILABLE: {
            "max_retries": 3,
            "base_delay": 2.0,
            "max_delay": 30.0,
            "exponential": True,
        },
        APIErrorType.INTERNAL_ERROR: {
            "max_retries": 2,
            "base_delay": 1.0,
            "max_delay": 10.0,
            "exponential": True,
        },
        APIErrorType.NETWORK_ERROR: {
            "max_retries": 3,
            "base_delay": 0.5,
            "max_delay": 5.0,
            "exponential": True,
        },
        APIErrorType.TIMEOUT: {
            "max_retries": 2,
            "base_delay": 2.0,
            "max_delay": 10.0,
            "exponential": False,
        },
    }

    # Non-retryable error types
    NON_RETRYABLE = {
        APIErrorType.INVALID_API_KEY,
        APIErrorType.INVALID_REQUEST,
        APIErrorType.NOT_FOUND,
        APIErrorType.PERMISSION_DENIED,
        APIErrorType.QUOTA_EXCEEDED,
    }

    @classmethod
    def classify_error(
        cls,
        status_code: Optional[int] = None,
        error_body: Optional[Union[Dict, str]] = None,
        exception: Optional[Exception] = None,
    ) -> APIErrorType:
        """Classify the error type based on status code, response body, or exception"""

        # Handle network/connection errors
        if exception:
            if isinstance(exception, asyncio.TimeoutError):
                return APIErrorType.TIMEOUT
            elif isinstance(exception, (aiohttp.ClientError, ConnectionError)):
                return APIErrorType.NETWORK_ERROR

        # Handle status code classification
        if status_code and status_code in cls.ERROR_MAPPING:
            error_type = cls.ERROR_MAPPING[status_code]

            # Special handling for 403 - could be quota or permission
            if status_code == 403 and error_body:
                error_str = str(error_body).lower()
                if "quota" in error_str:
                    return APIErrorType.QUOTA_EXCEEDED

            return error_type

        # Parse error body for additional classification
        if error_body:
            if isinstance(error_body, str):
                try:
                    error_body = json.loads(error_body)
                except Exception:
                    pass

            error_message = ""
            if isinstance(error_body, dict):
                error_message = str(
                    error_body.get("error", {}).get("message", "")
                ).lower()
                error_message += str(error_body.get("message", "")).lower()
            else:
                error_message = str(error_body).lower()

            # Check for specific error patterns
            if "quota" in error_message:
                return APIErrorType.QUOTA_EXCEEDED
            elif "rate" in error_message and "limit" in error_message:
                return APIErrorType.RATE_LIMIT
            elif "invalid" in error_message and "key" in error_message:
                return APIErrorType.INVALID_API_KEY
            elif "permission" in error_message or "forbidden" in error_message:
                return APIErrorType.PERMISSION_DENIED

        return APIErrorType.UNKNOWN

    @classmethod
    def should_retry(cls, error_type: APIErrorType) -> bool:
        """Check if error type is retryable"""
        return error_type not in cls.NON_RETRYABLE

    @classmethod
    def get_retry_delay(
        cls, error_type: APIErrorType, attempt: int, retry_after: Optional[int] = None
    ) -> float:
        """Calculate retry delay based on error type and attempt number"""

        # Use Retry-After header if provided
        if retry_after and retry_after > 0:
            return float(retry_after)

        strategy = cls.RETRY_STRATEGIES.get(error_type)
        if not strategy:
            return 0.0

        base_delay = strategy["base_delay"]
        max_delay = strategy["max_delay"]

        if strategy.get("exponential", True):
            # Exponential backoff with jitter
            delay = min(base_delay * (2**attempt), max_delay)
            # Add jitter (±20%)
            import random

            jitter = delay * 0.2 * (2 * random.random() - 1)
            delay += jitter
        else:
            # Linear delay
            delay = min(base_delay * (attempt + 1), max_delay)

        return max(0.1, delay)  # Minimum 100ms

    @classmethod
    async def handle_with_retry(
        cls,
        func: Callable[..., Any],
        *args,
        api_type: str = "unknown",
        endpoint: str = "unknown",
        **kwargs,
    ) -> T:
        """
        Execute function with intelligent retry logic

        Args:
            func: Async function to execute
            api_type: Type of Google API being called
            endpoint: Specific endpoint being called
            *args, **kwargs: Arguments for the function

        Returns:
            Result from the function

        Raises:
            GoogleAPIError: If all retries are exhausted or error is non-retryable
        """
        last_error = None
        total_attempts = 0

        # Get max retries from strategies
        max_attempts = (
            max(
                strategy.get("max_retries", 0)
                for strategy in cls.RETRY_STRATEGIES.values()
            )
            + 1
        )  # +1 for initial attempt

        for attempt in range(max_attempts):
            total_attempts = attempt + 1

            try:
                # Execute the function
                result = await func(*args, **kwargs)

                # Log successful recovery if we had previous errors
                if attempt > 0:
                    logger.info(
                        f"API call recovered after {attempt} retries "
                        f"(api: {api_type}, endpoint: {endpoint})"
                    )

                return result

            except aiohttp.ClientResponseError as e:
                # Handle HTTP errors
                error_body = None
                try:
                    if hasattr(e, "message"):
                        error_body = e.message
                except Exception:
                    pass

                error_type = cls.classify_error(
                    status_code=e.status, error_body=error_body
                )

                last_error = GoogleAPIError(
                    message=str(e),
                    status_code=e.status,
                    details={"error_type": error_type.value, "attempt": total_attempts},
                    api_type=api_type,
                    endpoint=endpoint,
                )

                # Check if we should retry
                if not cls.should_retry(error_type):
                    logger.error(
                        f"Non-retryable API error {error_type.value}: {e} "
                        f"(api: {api_type}, endpoint: {endpoint})"
                    )
                    raise last_error

                # Check retry-after header
                retry_after = None
                if hasattr(e, "headers"):
                    retry_after = e.headers.get("Retry-After")
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except Exception:
                            retry_after = None

                # Calculate delay
                delay = cls.get_retry_delay(error_type, attempt, retry_after)

                # Check if we have more attempts
                strategy = cls.RETRY_STRATEGIES.get(error_type, {})
                if attempt >= strategy.get("max_retries", 0):
                    logger.error(
                        f"Max retries exceeded for {error_type.value} "
                        f"(api: {api_type}, endpoint: {endpoint}, attempts: {total_attempts})"
                    )
                    raise last_error

                logger.warning(
                    f"API error {error_type.value}, retrying in {delay:.2f}s "
                    f"(api: {api_type}, endpoint: {endpoint}, attempt: {total_attempts})"
                )

                await asyncio.sleep(delay)

            except (asyncio.TimeoutError, aiohttp.ClientError, ConnectionError) as e:
                # Handle network/timeout errors
                error_type = cls.classify_error(exception=e)

                last_error = GoogleAPIError(
                    message=str(e),
                    status_code=0,  # No HTTP status for network errors
                    details={"error_type": error_type.value, "attempt": total_attempts},
                    api_type=api_type,
                    endpoint=endpoint,
                )

                # Check if we should retry
                if not cls.should_retry(error_type):
                    logger.error(
                        f"Non-retryable network error: {e} "
                        f"(api: {api_type}, endpoint: {endpoint})"
                    )
                    raise last_error

                # Calculate delay
                delay = cls.get_retry_delay(error_type, attempt)

                # Check if we have more attempts
                strategy = cls.RETRY_STRATEGIES.get(error_type, {})
                if attempt >= strategy.get("max_retries", 0):
                    logger.error(
                        f"Max retries exceeded for network error "
                        f"(api: {api_type}, endpoint: {endpoint}, attempts: {total_attempts})"
                    )
                    raise last_error

                logger.warning(
                    f"Network error, retrying in {delay:.2f}s "
                    f"(api: {api_type}, endpoint: {endpoint}, attempt: {total_attempts})"
                )

                await asyncio.sleep(delay)

            except Exception as e:
                # Handle unexpected errors
                logger.error(
                    f"Unexpected error in API call: {e} "
                    f"(api: {api_type}, endpoint: {endpoint})"
                )

                last_error = GoogleAPIError(
                    message=f"Unexpected error: {str(e)}",
                    status_code=0,
                    details={
                        "error_type": APIErrorType.UNKNOWN.value,
                        "attempt": total_attempts,
                    },
                    api_type=api_type,
                    endpoint=endpoint,
                )
                raise last_error

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        else:
            raise GoogleAPIError(
                message="Unknown error after all retries",
                status_code=0,
                api_type=api_type,
                endpoint=endpoint,
            )

    @classmethod
    def extract_error_details(cls, response_text: str) -> Dict[str, Any]:
        """Extract structured error details from API response"""
        try:
            error_data = json.loads(response_text)

            # Google API error format
            if "error" in error_data:
                error = error_data["error"]
                return {
                    "code": error.get("code"),
                    "message": error.get("message"),
                    "status": error.get("status"),
                    "details": error.get("details", []),
                }

            return error_data

        except json.JSONDecodeError:
            # Return raw text if not JSON
            return {"message": response_text}
        except Exception as e:
            return {"message": str(e)}
