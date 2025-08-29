"""
API decorators for common functionality like rate limiting, caching, and versioning.
"""

import hashlib
import json
from datetime import datetime
from functools import wraps
from typing import Optional, Callable, Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.cache import cache
from app.core.logging import get_logger
from app.middleware.rate_limiting import EndpointRateLimiter

logger = get_logger(__name__)


def rate_limit(requests_per_minute: int):
    """
    Decorator for endpoint - specific rate limiting.

    Usage:
        @router.get("/expensive - operation")
        @rate_limit(5)
        async def expensive_operation():
            ...
    """
    limiter = EndpointRateLimiter(requests_per_minute)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Check rate limit
            allowed = await limiter(request)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": "請求次數超過限制，請稍後再試",
                        "error": "rate_limit_exceeded",
                    },
                )

            # Execute function
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def cache_response(expire_seconds: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator for caching endpoint responses.

    Args:
        expire_seconds: Cache expiration time
        key_prefix: Optional prefix for cache key

    Usage:
        @router.get("/data")
        @cache_response(expire_seconds=600)
        async def get_data():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Generate cache key
            path = request.url.path
            query_params = str(sorted(request.query_params.items()))

            # Include user ID in cache key if authenticated
            user_id = getattr(request.state, "user_id", "anonymous")

            # Create cache key
            key_parts = [key_prefix or "api_cache", path, query_params, str(user_id)]
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # Try to get from cache
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {path}")
                # Return cached response
                data = json.loads(cached_data)
                response = JSONResponse(content=data)
                response.headers["X - Cache"] = "HIT"
                response.headers["X - Cache - Key"] = cache_key
                return response

            # Execute function
            result = await func(request, *args, **kwargs)

            # Cache the result if it's a successful response
            if isinstance(result, dict) or (
                hasattr(result, "status_code") and result.status_code < 400
            ):
                # Convert response to cacheable format
                if isinstance(result, dict):
                    cache_data = json.dumps(result)
                else:
                    # For Response objects, we need to extract the body
                    cache_data = (
                        result.body.decode()
                        if hasattr(result, "body")
                        else json.dumps(result)
                    )

                await cache.set(cache_key, cache_data, expire=expire_seconds)

                # Add cache headers
                if hasattr(result, "headers"):
                    result.headers["X - Cache"] = "MISS"
                    result.headers["X - Cache - Key"] = cache_key
                    result.headers["Cache - Control"] = (
                        f"private, max - age={expire_seconds}"
                    )

            return result

        return wrapper

    return decorator


def validate_taiwan_phone(phone_field: str = "phone"):
    """
    Decorator to validate Taiwan phone number format.

    Args:
        phone_field: Name of the field containing the phone number

    Usage:
        @router.post("/customer")
        @validate_taiwan_phone("phone_number")
        async def create_customer(data: CustomerCreate):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract the data object
            data = None
            for arg in args:
                if hasattr(arg, phone_field):
                    data = arg
                    break

            if data:
                phone = getattr(data, phone_field, None)
                if phone:
                    from app.core.config import settings

                    if not settings.validate_taiwan_phone(phone):
                        raise HTTPException(
                            status_code=422,
                            detail={
                                "message": "無效的電話號碼格式",
                                "field": phone_field,
                                "hint": "請使用台灣電話格式，例如：0912 - 345 - 678 或 02 - 1234 - 5678",
                            },
                        )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_taiwan_address(address_field: str = "address"):
    """
    Decorator to validate Taiwan address format.

    Args:
        address_field: Name of the field containing the address

    Usage:
        @router.post("/customer")
        @validate_taiwan_address("delivery_address")
        async def create_customer(data: CustomerCreate):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract the data object
            data = None
            for arg in args:
                if hasattr(arg, address_field):
                    data = arg
                    break

            if data:
                address = getattr(data, address_field, None)
                if address:
                    from app.core.config import settings

                    if not settings.validate_taiwan_address(address):
                        raise HTTPException(
                            status_code=422,
                            detail={
                                "message": "無效的地址格式",
                                "field": address_field,
                                "hint": "請包含縣市、區 / 鄉 / 鎮、路 / 街及門牌號碼",
                            },
                        )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(allowed_roles: list):
    """
    Decorator to check user role permissions.

    Args:
        allowed_roles: List of allowed roles

    Usage:
        @router.delete("/customer/{id}")
        @require_role(["manager", "super_admin"])
        async def delete_customer(id: int):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get user role from request state (set by auth middleware)
            user_role = getattr(request.state, "user_role", None)

            if not user_role or user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": "您沒有權限執行此操作",
                        "required_roles": allowed_roles,
                        "current_role": user_role,
                    },
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def track_performance(metric_name: str):
    """
    Decorator to track endpoint performance metrics.

    Args:
        metric_name: Name for the metric

    Usage:
        @router.get("/complex - calculation")
        @track_performance("complex_calculation")
        async def complex_calculation():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Calculate duration
                duration = (datetime.utcnow() - start_time).total_seconds()

                # Log performance
                logger.info(
                    f"Performance: {metric_name}",
                    extra={
                        "metric_name": metric_name,
                        "duration_seconds": duration,
                        "status": "success",
                    },
                )

                # Add performance header if it's a response
                if hasattr(result, "headers"):
                    result.headers["X - Performance - Ms"] = str(int(duration * 1000))

                return result

            except Exception as e:
                # Calculate duration even on error
                duration = (datetime.utcnow() - start_time).total_seconds()

                # Log performance with error
                logger.error(
                    f"Performance: {metric_name} failed",
                    extra={
                        "metric_name": metric_name,
                        "duration_seconds": duration,
                        "status": "error",
                        "error": str(e),
                    },
                )

                raise

        return wrapper

    return decorator


def paginate(default_limit: int = 20, max_limit: int = 100):
    """
    Decorator to add pagination parameters to endpoints.

    Args:
        default_limit: Default number of items per page
        max_limit: Maximum allowed items per page

    Usage:
        @router.get("/customers")
        @paginate(default_limit=50)
        async def list_customers(skip: int = 0, limit: int = None):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, skip: int = 0, limit: Optional[int] = None, **kwargs):
            # Apply defaults and limits
            if limit is None:
                limit = default_limit
            elif limit > max_limit:
                limit = max_limit
            elif limit < 1:
                limit = 1

            # Ensure skip is non - negative
            if skip < 0:
                skip = 0

            # Call function with pagination parameters
            result = await func(*args, skip=skip, limit=limit, **kwargs)

            # Add pagination headers if it's a response
            if hasattr(result, "headers"):
                result.headers["X - Pagination - Skip"] = str(skip)
                result.headers["X - Pagination - Limit"] = str(limit)

            return result

        return wrapper

    return decorator
