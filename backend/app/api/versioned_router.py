"""
Example of versioned API router implementation.

This demonstrates how to handle multiple API versions
with proper deprecation and feature flags.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.decorators import cache_response, rate_limit
from app.core.logging import get_logger
from app.core.versioning import (
    APIVersion,
    get_requested_version,
    get_version_features,
    requires_version,
    version_deprecated,
)

logger = get_logger(__name__)


def create_versioned_router(version: str) -> APIRouter:
    """
    Create a router for a specific API version.

    This allows for version-specific implementations while
    maintaining backward compatibility.
    """
    router = APIRouter()
    version_obj = APIVersion(version)

    # Get feature flags for this version
    features = get_version_features(version_obj)

    @router.get("/info")
    @cache_response(expire_seconds=3600)
    async def get_version_info(request: Request) -> Dict[str, Any]:
        """Get information about the current API version."""
        return {
            "version": str(version_obj),
            "features": features,
            "deprecated": version in ["v1.0", "v1.1"],  # Example deprecated versions
            "minimum_supported": "v1.0.0",
            "latest": "v1.2.0",
        }

    # Version 1.0 endpoints
    if version_obj.major == 1 and version_obj.minor == 0:

        @router.get("/customers")
        @version_deprecated(
            deprecated_in="v1.1",
            removed_in="v2.0",
            alternative="/api/v1/customers/list",
        )
        @rate_limit(100)
        async def get_customers_v1_0(
            request: Request, skip: int = 0, limit: int = 20
        ) -> Dict[str, Any]:
            """
            Legacy customer list endpoint.
            Deprecated in favor of /customers/list with better filtering.
            """
            logger.info(f"Legacy customers endpoint called (v{version_obj})")

            return {
                "customers": [],  # Placeholder
                "total": 0,
                "version": "1.0",
                "_deprecation_notice": "Use /api/v1/customers/list instead",
            }

    # Version 1.1+ endpoints
    if version_obj >= APIVersion("v1.1"):

        @router.get("/customers/list")
        @rate_limit(200)
        @cache_response(expire_seconds=300)
        async def get_customers_list(
            request: Request,
            skip: int = 0,
            limit: int = 50,
            filter_active: bool = True,
            search: str = None,
        ) -> Dict[str, Any]:
            """
            Enhanced customer list with filtering and search.
            Available from v1.1+
            """
            logger.info(f"Enhanced customers endpoint called (v{version_obj})")

            # Version-specific logic
            response = {
                "customers": [],  # Placeholder
                "total": 0,
                "version": str(version_obj),
                "filters_applied": {"active": filter_active, "search": search},
            }

            # Add extra fields for v1.2+
            if version_obj >= APIVersion("v1.2"):
                response["metadata"] = {
                    "last_updated": "2024-01-20T10:00:00Z",
                    "cache_status": "miss",
                }

            return response

    # Version 1.2+ exclusive features
    if version_obj >= APIVersion("v1.2"):

        @router.post("/customers/batch")
        @requires_version("v1.2")
        @rate_limit(10)
        async def create_customers_batch(
            request: Request, customers: list
        ) -> Dict[str, Any]:
            """
            Batch customer creation endpoint.
            Only available in v1.2+
            """
            if not features.get("batch_operations", False):
                raise HTTPException(
                    status_code=501,
                    detail="Batch operations not available in this version",
                )

            logger.info(f"Batch customer creation (v{version_obj})")

            return {
                "created": len(customers),
                "version": str(version_obj),
                "batch_id": "batch_123",
            }

        @router.get("/predictions/advanced")
        @requires_version("v1.2")
        @rate_limit(50)
        async def get_advanced_predictions(
            request: Request, model_type: str = "vertex_ai"
        ) -> Dict[str, Any]:
            """
            Advanced ML predictions using Google Vertex AI.
            Only available in v1.2+ with advanced_predictions feature.
            """
            if not features.get("advanced_predictions", False):
                raise HTTPException(
                    status_code=501, detail="Advanced predictions not available"
                )

            return {
                "predictions": [],
                "model": model_type,
                "version": str(version_obj),
                "accuracy": 0.95,
            }

    # WebSocket support (if enabled for version)
    if features.get("websocket_support", False):

        @router.websocket("/ws")
        async def websocket_endpoint(websocket):
            """WebSocket endpoint for real-time updates."""
            # This would be handled by Socket.IO in production
            pass

    return router


# Example usage in main app
def setup_versioned_apis(app):
    """
    Set up versioned API routers in the main application.

    This would be called from main.py to register all versions.
    """
    # Register v1.0 (deprecated but still supported)
    v1_0_router = create_versioned_router("v1.0")
    app.include_router(v1_0_router, prefix="/api/v1.0", tags=["v1.0 (deprecated)"])

    # Register v1.1
    v1_1_router = create_versioned_router("v1.1")
    app.include_router(v1_1_router, prefix="/api/v1.1", tags=["v1.1"])

    # Register v1.2 (current)
    v1_2_router = create_versioned_router("v1.2")
    app.include_router(v1_2_router, prefix="/api/v1.2", tags=["v1.2 (current)"])

    # Default v1 points to latest v1.x
    app.include_router(v1_2_router, prefix="/api/v1", tags=["v1 (latest)"])


# Version migration helpers
async def migrate_request_v1_0_to_v1_1(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate request data from v1.0 format to v1.1 format.

    This helps maintain backward compatibility when old clients
    call new endpoints.
    """
    migrated = request_data.copy()

    # Example: v1.0 used 'customer_name', v1.1 uses 'name'
    if "customer_name" in migrated:
        migrated["name"] = migrated.pop("customer_name")

    # Example: v1.0 used boolean 'active', v1.1 uses status enum
    if "active" in migrated:
        migrated["status"] = "active" if migrated.pop("active") else "inactive"

    return migrated


async def migrate_response_v1_1_to_v1_0(
    response_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Migrate response data from v1.1 format to v1.0 format.

    This helps when old clients expect v1.0 response format
    but the backend has moved to v1.1.
    """
    migrated = response_data.copy()

    # Example: v1.1 returns 'name', v1.0 expects 'customer_name'
    if "name" in migrated:
        migrated["customer_name"] = migrated.pop("name")

    # Example: v1.1 returns status enum, v1.0 expects boolean
    if "status" in migrated:
        migrated["active"] = migrated.pop("status") == "active"

    # Remove fields that don't exist in v1.0
    v1_0_fields = ["id", "customer_name", "active", "created_at"]
    migrated = {k: v for k, v in migrated.items() if k in v1_0_fields}

    return migrated
