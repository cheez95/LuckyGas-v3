"""
Logging middleware for request tracking
"""
import uuid
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import (
    request_id_context,
    user_id_context,
    client_ip_context,
    get_logger,
    log_api_request
)

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request tracking and structured logging
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add request context and log API requests
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Set context variables
        request_id_context.set(request_id)
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        client_ip_context.set(client_ip)
        
        # Extract user ID if authenticated (will be set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            user_id_context.set(user_id)
        
        # Start timer
        start_time = time.time()
        
        # Log request
        request_data = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent"),
            "request_id": request_id
        }
        
        log_api_request(logger, request_data)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"API Response: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": duration,
                    "request_id": request_id
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"API Error: {request.method} {request.url.path} - {type(e).__name__}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_seconds": duration,
                    "request_id": request_id
                },
                exc_info=True
            )
            
            # Re-raise exception
            raise
        
        finally:
            # Clear context variables
            request_id_context.set(None)
            user_id_context.set(None)
            client_ip_context.set(None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for distributed tracing
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Handle correlation ID propagation
        """
        # Check for existing correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Generate new one if not present
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response