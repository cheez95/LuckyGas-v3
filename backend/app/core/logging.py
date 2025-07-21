"""
Structured logging configuration for Lucky Gas
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

from app.core.config import settings

# Context variables for request tracking
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[int]] = ContextVar('user_id', default=None)
client_ip_context: ContextVar[Optional[str]] = ContextVar('client_ip', default=None)


class ContextFilter(logging.Filter):
    """
    Add context information to log records
    """
    def filter(self, record):
        # Add context variables
        record.request_id = request_id_context.get()
        record.user_id = user_id_context.get()
        record.client_ip = client_ip_context.get()
        
        # Add application metadata
        record.environment = settings.ENVIRONMENT.value
        record.service = "lucky-gas-backend"
        record.version = "1.0.0"
        
        # Add timestamp in ISO format
        record.timestamp = datetime.utcnow().isoformat()
        
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields
    """
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add context fields
        if hasattr(record, 'request_id') and record.request_id:
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id') and record.user_id:
            log_record['user_id'] = record.user_id
        if hasattr(record, 'client_ip') and record.client_ip:
            log_record['client_ip'] = record.client_ip
        
        # Add application metadata
        if hasattr(record, 'environment'):
            log_record['environment'] = record.environment
        if hasattr(record, 'service'):
            log_record['service'] = record.service
        if hasattr(record, 'version'):
            log_record['version'] = record.version
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Remove redundant fields
        for field in ['message', 'msg', 'args', 'created', 'msecs', 'relativeCreated', 'exc_info', 'exc_text']:
            log_record.pop(field, None)


def setup_logging():
    """
    Configure structured logging for the application
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Set log level based on environment
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Add formatter based on environment
    if settings.is_development():
        # Use human-readable format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Use JSON format for production
        formatter = CustomJsonFormatter()
    
    console_handler.setFormatter(formatter)
    
    # Add context filter
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_app_loggers()
    
    # Suppress noisy loggers
    suppress_noisy_loggers()
    
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": settings.LOG_LEVEL,
            "environment": settings.ENVIRONMENT.value,
            "json_logging": not settings.is_development()
        }
    )


def configure_app_loggers():
    """
    Configure specific application loggers
    """
    # Application loggers
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.DEBUG if settings.is_development() else logging.INFO)
    
    # Database logger
    db_logger = logging.getLogger("app.database")
    db_logger.setLevel(logging.INFO)
    
    # API logger
    api_logger = logging.getLogger("app.api")
    api_logger.setLevel(logging.INFO)
    
    # Service logger
    service_logger = logging.getLogger("app.services")
    service_logger.setLevel(logging.INFO)


def suppress_noisy_loggers():
    """
    Suppress or reduce verbosity of third-party loggers
    """
    # Suppress SQLAlchemy logs unless in debug mode
    if not settings.is_development():
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Reduce verbosity of other libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    
    # Uvicorn access logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter to add context to all log messages
    """
    def process(self, msg, kwargs):
        # Add context from context variables
        extra = kwargs.get('extra', {})
        
        if request_id := request_id_context.get():
            extra['request_id'] = request_id
        if user_id := user_id_context.get():
            extra['user_id'] = user_id
        if client_ip := client_ip_context.get():
            extra['client_ip'] = client_ip
        
        kwargs['extra'] = extra
        return msg, kwargs


def log_error(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None):
    """
    Log an error with context information
    
    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context information
    """
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(context or {})
    }
    
    logger.error(
        f"Error occurred: {type(error).__name__}",
        extra=error_data,
        exc_info=True
    )


def log_api_request(logger: logging.Logger, request_data: Dict[str, Any]):
    """
    Log API request information
    
    Args:
        logger: Logger instance
        request_data: Request information to log
    """
    logger.info(
        f"API Request: {request_data.get('method')} {request_data.get('path')}",
        extra=request_data
    )


def log_db_query(logger: logging.Logger, query_data: Dict[str, Any]):
    """
    Log database query information
    
    Args:
        logger: Logger instance
        query_data: Query information to log
    """
    logger.debug(
        f"Database Query: {query_data.get('operation')} on {query_data.get('table')}",
        extra=query_data
    )