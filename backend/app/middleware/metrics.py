"""
Metrics middleware for tracking API performance
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.metrics import (
    api_request_counter,
    api_request_duration_histogram,
    error_counter,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API request metrics
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Track API request metrics
        """
        # Start timer
        start_time = time.time()

        # Extract path for metrics (remove path parameters)
        path = request.url.path
        # Simplify path by removing IDs and UUIDs
        path_template = self._get_path_template(path)

        try:
            # Process request
            response = await call_next(request)

            # Track successful request
            api_request_counter.labels(
                method=request.method,
                endpoint=path_template,
                status_code=str(response.status_code),
            ).inc()

            # Track request duration
            duration = time.time() - start_time
            api_request_duration_histogram.labels(
                method=request.method, endpoint=path_template
            ).observe(duration)

            return response

        except Exception as e:
            # Track error
            error_counter.labels(
                error_type=type(e).__name__, severity="error", component="api"
            ).inc()

            # Track failed request
            api_request_counter.labels(
                method=request.method, endpoint=path_template, status_code="500"
            ).inc()

            # Re-raise exception
            raise

    def _get_path_template(self, path: str) -> str:
        """
        Convert path with IDs to template format
        e.g., /api/v1/customers/123 -> /api/v1/customers/{id}
        """
        parts = path.split("/")
        template_parts = []

        for i, part in enumerate(parts):
            # Check if part is numeric (likely an ID)
            if part.isdigit():
                template_parts.append("{id}")
            # Check if part looks like a UUID
            elif len(part) == 36 and part.count("-") == 4:
                template_parts.append("{uuid}")
            else:
                template_parts.append(part)

        return "/".join(template_parts)
