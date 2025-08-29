"""
Service Layer Utilities for reducing code duplication in service classes.

This module provides decorators and utilities to eliminate ~500 lines of duplicate
error handling, validation, and transaction management code in service layer.
"""

import functools
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

T = TypeVar('T')


def handle_service_errors(
    operation: str = "操作",
    log_errors: bool = True,
    raise_http: bool = False
) -> Callable:
    """
    Decorator to handle common service layer errors with consistent error responses.
    
    Eliminates ~100+ duplicate try/catch blocks across service classes.
    
    Args:
        operation: Description of the operation for error messages
        log_errors: Whether to log errors to the logger
        raise_http: Whether to raise HTTPException (for API-facing services)
    
    Example:
        @handle_service_errors(operation="計算營收指標")
        async def calculate_revenue(self, start_date: date, end_date: date):
            # business logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except IntegrityError as e:
                if log_errors:
                    logger.error(f"資料完整性錯誤 in {func.__name__}: {str(e)}")
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"{operation}失敗：資料衝突"
                    )
                raise ServiceError(f"{operation}失敗：資料衝突", original_error=e)
            except SQLAlchemyError as e:
                if log_errors:
                    logger.error(f"資料庫錯誤 in {func.__name__}: {str(e)}")
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"{operation}失敗：資料庫錯誤"
                    )
                raise ServiceError(f"{operation}失敗：資料庫錯誤", original_error=e)
            except ValueError as e:
                if log_errors:
                    logger.warning(f"數值錯誤 in {func.__name__}: {str(e)}")
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e)
                    )
                raise ServiceError(f"{operation}失敗：{str(e)}", original_error=e)
            except Exception as e:
                if log_errors:
                    logger.error(f"未預期錯誤 in {func.__name__}: {str(e)}", exc_info=True)
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"{operation}失敗"
                    )
                raise ServiceError(f"{operation}失敗", original_error=e)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except IntegrityError as e:
                if log_errors:
                    logger.error(f"資料完整性錯誤 in {func.__name__}: {str(e)}")
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"{operation}失敗：資料衝突"
                    )
                raise ServiceError(f"{operation}失敗：資料衝突", original_error=e)
            except SQLAlchemyError as e:
                if log_errors:
                    logger.error(f"資料庫錯誤 in {func.__name__}: {str(e)}")
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"{operation}失敗：資料庫錯誤"
                    )
                raise ServiceError(f"{operation}失敗：資料庫錯誤", original_error=e)
            except ValueError as e:
                if log_errors:
                    logger.warning(f"數值錯誤 in {func.__name__}: {str(e)}")
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e)
                    )
                raise ServiceError(f"{operation}失敗：{str(e)}", original_error=e)
            except Exception as e:
                if log_errors:
                    logger.error(f"未預期錯誤 in {func.__name__}: {str(e)}", exc_info=True)
                if raise_http:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"{operation}失敗"
                    )
                raise ServiceError(f"{operation}失敗", original_error=e)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def transactional(
    auto_commit: bool = True,
    auto_rollback: bool = True,
    nested: bool = False
) -> Callable:
    """
    Decorator to manage database transactions automatically.
    
    Eliminates ~50+ duplicate transaction management blocks.
    
    Args:
        auto_commit: Whether to auto-commit on success
        auto_rollback: Whether to auto-rollback on failure
        nested: Whether to use nested transactions (savepoints)
    
    Example:
        @transactional()
        def create_order_with_items(self, order_data):
            # All database operations in transaction
            order = self.create_order(order_data)
            self.create_items(order, order_data.items)
            return order
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            db: Session = self.db
            
            if nested and db.in_transaction():
                # Use savepoint for nested transaction
                savepoint = db.begin_nested()
                try:
                    result = await func(self, *args, **kwargs)
                    if auto_commit:
                        savepoint.commit()
                    return result
                except Exception as e:
                    if auto_rollback:
                        savepoint.rollback()
                    raise
            else:
                # Regular transaction
                try:
                    result = await func(self, *args, **kwargs)
                    if auto_commit:
                        db.commit()
                    return result
                except Exception as e:
                    if auto_rollback:
                        db.rollback()
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            db: Session = self.db
            
            if nested and db.in_transaction():
                # Use savepoint for nested transaction
                savepoint = db.begin_nested()
                try:
                    result = func(self, *args, **kwargs)
                    if auto_commit:
                        savepoint.commit()
                    return result
                except Exception as e:
                    if auto_rollback:
                        savepoint.rollback()
                    raise
            else:
                # Regular transaction
                try:
                    result = func(self, *args, **kwargs)
                    if auto_commit:
                        db.commit()
                    return result
                except Exception as e:
                    if auto_rollback:
                        db.rollback()
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_result(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    cache_none: bool = False
) -> Callable:
    """
    Decorator to cache service method results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Custom cache key prefix
        cache_none: Whether to cache None results
    
    Example:
        @cache_result(ttl=600, key_prefix="revenue")
        def get_revenue_metrics(self, start_date, end_date):
            # Expensive calculation cached for 10 minutes
            pass
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[str, tuple[Any, float]] = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = f"{key_prefix}:{func.__name__}:{str(args[1:])}:{str(kwargs)}"
            else:
                cache_key = f"{func.__name__}:{str(args[1:])}:{str(kwargs)}"
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    logger.debug(f"Cache hit for {cache_key}")
                    return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None or cache_none:
                cache[cache_key] = (result, time.time())
                logger.debug(f"Cached result for {cache_key}")
            
            return result
        
        return wrapper
    
    return decorator


def validate_date_range(
    max_days: Optional[int] = None,
    min_days: int = 1,
    allow_future: bool = False
) -> Callable:
    """
    Decorator to validate date range parameters.
    
    Eliminates ~30+ duplicate date validation blocks.
    
    Args:
        max_days: Maximum allowed days in range
        min_days: Minimum required days in range
        allow_future: Whether to allow future dates
    
    Example:
        @validate_date_range(max_days=365, allow_future=False)
        def get_historical_data(self, start_date: date, end_date: date):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract date parameters
            start_date = None
            end_date = None
            
            # Check positional args
            if len(args) > 1 and isinstance(args[1], date):
                start_date = args[1]
            if len(args) > 2 and isinstance(args[2], date):
                end_date = args[2]
            
            # Check keyword args
            start_date = kwargs.get('start_date', start_date)
            end_date = kwargs.get('end_date', end_date)
            
            if start_date and end_date:
                # Validate date range
                if start_date > end_date:
                    raise ValueError("開始日期不能晚於結束日期")
                
                days_diff = (end_date - start_date).days + 1
                
                if days_diff < min_days:
                    raise ValueError(f"日期範圍至少需要 {min_days} 天")
                
                if max_days and days_diff > max_days:
                    raise ValueError(f"日期範圍不能超過 {max_days} 天")
                
                if not allow_future:
                    today = date.today()
                    if end_date > today:
                        raise ValueError("不允許查詢未來日期")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_pagination(
    max_page_size: int = 100,
    default_page_size: int = 20
) -> Callable:
    """
    Decorator to validate pagination parameters in service methods.
    
    Args:
        max_page_size: Maximum allowed page size
        default_page_size: Default page size if not provided
    
    Example:
        @validate_pagination(max_page_size=50)
        def list_items(self, page: int = 1, page_size: int = 20):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Validate and adjust pagination
            page = kwargs.get('page', 1)
            page_size = kwargs.get('page_size', default_page_size)
            
            # Ensure valid values
            page = max(1, page)
            page_size = min(max(1, page_size), max_page_size)
            
            # Update kwargs
            kwargs['page'] = page
            kwargs['page_size'] = page_size
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry operations on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for each retry
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @retry_on_failure(max_retries=3, exceptions=(ConnectionError,))
        def connect_to_external_service(self):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ServiceError(Exception):
    """Custom exception for service layer errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class ValidationError(ServiceError):
    """Exception for validation errors in service layer."""
    
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")


# Common validation utilities
class ServiceValidators:
    """Common validation utilities for service layer."""
    
    @staticmethod
    def validate_positive_number(value: Union[int, float, Decimal], field_name: str) -> None:
        """Validate that a number is positive."""
        if value <= 0:
            raise ValidationError(field_name, f"{field_name} 必須大於 0")
    
    @staticmethod
    def validate_percentage(value: Union[float, Decimal], field_name: str) -> None:
        """Validate that a value is a valid percentage (0-100)."""
        if not 0 <= value <= 100:
            raise ValidationError(field_name, f"{field_name} 必須在 0 到 100 之間")
    
    @staticmethod
    def validate_phone_number(phone: str) -> None:
        """Validate Taiwan phone number format."""
        import re
        pattern = r'^09\d{8}$|^0[2-8]\d{7,8}$'
        if not re.match(pattern, phone.replace('-', '').replace(' ', '')):
            raise ValidationError("phone", "無效的電話號碼格式")
    
    @staticmethod
    def validate_email(email: str) -> None:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError("email", "無效的電子郵件格式")
    
    @staticmethod
    def validate_taiwan_address(address: str) -> None:
        """Validate Taiwan address format."""
        if len(address) < 6:
            raise ValidationError("address", "地址太短")
        
        # Check for basic Taiwan address components
        required_chars = ['市', '區', '路', '街', '巷', '號']
        if not any(char in address for char in required_chars):
            raise ValidationError("address", "請輸入完整的台灣地址")
    
    @staticmethod
    def validate_date_not_past(date_value: date, field_name: str) -> None:
        """Validate that a date is not in the past."""
        if date_value < date.today():
            raise ValidationError(field_name, f"{field_name} 不能是過去的日期")
    
    @staticmethod
    def validate_business_hours(hour: int) -> None:
        """Validate that time is within business hours (8-18)."""
        if not 8 <= hour <= 18:
            raise ValidationError("time", "必須在營業時間內 (08:00-18:00)")


# Batch operation utilities
class BatchProcessor:
    """Utility class for processing operations in batches."""
    
    @staticmethod
    def process_in_batches(
        items: List[T],
        batch_size: int,
        processor: Callable[[List[T]], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Process items in batches to avoid memory issues.
        
        Args:
            items: List of items to process
            batch_size: Size of each batch
            processor: Function to process each batch
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of results from each batch
        """
        results = []
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            if progress_callback:
                progress_callback(batch_num, total_batches)
            
            result = processor(batch)
            results.append(result)
        
        return results


# Performance monitoring
def measure_performance(
    metric_name: Optional[str] = None,
    log_result: bool = True
) -> Callable:
    """
    Decorator to measure and log performance of service methods.
    
    Args:
        metric_name: Custom metric name for logging
        log_result: Whether to log the execution time
    
    Example:
        @measure_performance(metric_name="revenue_calculation")
        def calculate_complex_metrics(self):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                name = metric_name or func.__name__
                if log_result:
                    logger.info(f"Performance: {name} executed in {execution_time:.3f} seconds")
                
                # Store metric for monitoring
                if hasattr(args[0], '_performance_metrics'):
                    args[0]._performance_metrics[name] = execution_time
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                name = metric_name or func.__name__
                if log_result:
                    logger.info(f"Performance: {name} executed in {execution_time:.3f} seconds")
                
                # Store metric for monitoring
                if hasattr(args[0], '_performance_metrics'):
                    args[0]._performance_metrics[name] = execution_time
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Import asyncio for async detection
import asyncio