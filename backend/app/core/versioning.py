"""
API versioning utilities for the Lucky Gas API.

This module provides utilities for API versioning including:
- Version negotiation via headers or URL
- Backward compatibility support
- Version deprecation notices
"""

import re
from functools import wraps

from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class APIVersion:
    """Represents an API version."""

    def __init__(self, version_string: str):
        """
        Initialize API version from string (e.g., "v1", "v1.2", "v2.0.1").
        """
        self.version_string = version_string
        self.major, self.minor, self.patch = self._parse_version(version_string)

    def _parse_version(self, version_string: str) -> tuple:
        """Parse version string into major, minor, patch numbers."""
        # Remove 'v' prefix if present
        version = version_string.lower().lstrip("v")

        # Split by dots
        parts = version.split(".")

        # Default values
        major = int(parts[0]) if parts else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return major, minor, patch

    def __str__(self):
        return f"v{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other):
        if not isinstance(other, APIVersion):
            return False
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )

    def __lt__(self, other):
        if not isinstance(other, APIVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other):
        return self == other or self < other

    def is_compatible_with(self, other: "APIVersion") -> bool:
        """Check if this version is compatible with another version."""
        # Same major version means compatible (following semver)
        return self.major == other.major


class VersionConfig:
    """Configuration for API versioning."""

    CURRENT_VERSION = APIVersion("v1.0.0")
    MINIMUM_VERSION = APIVersion("v1.0.0")
    DEPRECATED_VERSIONS = []  # List of APIVersion objects
    SUNSET_DATES = {}  # Dict of version string to sunset date

    # Version - specific feature flags
    FEATURES = {
        "v1": {
            "websocket_support": True,
            "batch_operations": True,
            "advanced_predictions": True,
            "google_api_integration": True,
        }
    }


def get_requested_version(
    request: Request,
    accept_version: Optional[str] = Header(None, alias="Accept - Version"),
    api_version: Optional[str] = Header(None, alias="API - Version"),
) -> APIVersion:
    """
    Get the requested API version from the request.

    Priority order:
    1. Accept - Version header
    2. API - Version header
    3. URL path (e.g., /api / v1/...)
    4. Default to current version
    """
    # Check headers first
    version_string = accept_version or api_version

    if not version_string:
        # Try to extract from URL path
        path_match = re.match(r"/api/(v\d+(?:\.\d+)?(?:\.\d+)?)", request.url.path)
        if path_match:
            version_string = path_match.group(1)

    if not version_string:
        # Default to current version
        return VersionConfig.CURRENT_VERSION

    try:
        requested_version = APIVersion(version_string)

        # Check if version is supported
        if requested_version < VersionConfig.MINIMUM_VERSION:
            raise HTTPException(
                status_code=400,
                detail=f"API version {requested_version} is no longer supported. Minimum version is {VersionConfig.MINIMUM_VERSION}",
            )

        # Check if version is deprecated
        if any(requested_version == v for v in VersionConfig.DEPRECATED_VERSIONS):
            sunset_date = VersionConfig.SUNSET_DATES.get(str(requested_version))
            logger.warning(
                f"Deprecated API version {requested_version} requested",
                extra={
                    "version": str(requested_version),
                    "sunset_date": sunset_date,
                    "client": request.client.host if request.client else "unknown",
                },
            )

        return requested_version

    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid API version format: {version_string}"
        )


def version_deprecated(
    deprecated_in: str,
    removed_in: Optional[str] = None,
    alternative: Optional[str] = None,
):
    """
    Decorator to mark an endpoint as deprecated.

    Args:
        deprecated_in: Version when the endpoint was deprecated
        removed_in: Version when the endpoint will be removed
        alternative: Alternative endpoint to use
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Add deprecation headers to response
            response = await func(*args, **kwargs)

            if isinstance(response, JSONResponse):
                response.headers["Deprecated"] = "true"
                response.headers["Deprecated - Since"] = deprecated_in

                if removed_in:
                    response.headers["Sunset"] = removed_in

                if alternative:
                    response.headers["Link"] = f'<{alternative}>; rel="alternate"'

                # Add deprecation notice to response body
                if hasattr(response, "body"):
                    import json

                    body = json.loads(response.body)
                    body["_deprecation"] = {
                        "deprecated": True,
                        "since": deprecated_in,
                        "sunset": removed_in,
                        "alternative": alternative,
                        "message": f"This endpoint is deprecated and will be removed in version {removed_in}",
                    }
                    response.body = json.dumps(body).encode()

            return response

        return wrapper

    return decorator


def requires_version(minimum_version: str):
    """
    Decorator to require a minimum API version for an endpoint.

    Args:
        minimum_version: Minimum version required (e.g., "v1.1")
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            requested_version = get_requested_version(request)
            required_version = APIVersion(minimum_version)

            if requested_version < required_version:
                raise HTTPException(
                    status_code=400,
                    detail=f"This endpoint requires API version {required_version} or higher. You requested {requested_version}",
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_version_features(version: APIVersion) -> Dict[str, bool]:
    """
    Get feature flags for a specific API version.

    Returns dict of feature name to enabled status.
    """
    version_key = f"v{version.major}"
    return VersionConfig.FEATURES.get(version_key, {})


def add_version_headers(response: JSONResponse, version: APIVersion) -> JSONResponse:
    """Add version - related headers to response."""
    response.headers["API - Version"] = str(version)
    response.headers["API - Version - Latest"] = str(VersionConfig.CURRENT_VERSION)

    # Add deprecation warning if using deprecated version
    if any(version == v for v in VersionConfig.DEPRECATED_VERSIONS):
        response.headers["Warning"] = f'299 - "API version {version} is deprecated"'

        sunset_date = VersionConfig.SUNSET_DATES.get(str(version))
        if sunset_date:
            response.headers["Sunset"] = sunset_date.isoformat()

    return response


# Version - specific route factories


def create_versioned_app(version: str):
    """
    Create a FastAPI app for a specific API version.

    This allows for completely different implementations per version.
    """
    from fastapi import FastAPI

    version_obj = APIVersion(version)

    app = FastAPI(
        title=f"Lucky Gas API {version}",
        version=str(version_obj),
        docs_url=f"/api/{version}/docs",
        redoc_url=f"/api/{version}/redoc",
        openapi_url=f"/api/{version}/openapi.json",
    )

    # Add version - specific middleware
    @app.middleware("http")
    async def add_version_headers(request: Request, call_next):
        response = await call_next(request)
        return add_version_headers(response, version_obj)

    return app
