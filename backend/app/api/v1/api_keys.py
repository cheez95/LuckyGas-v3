"""
API key management endpoints for rate limiting and access control.
"""

from app.core.logging import get_logger
from app.middleware.enhanced_rate_limiting import APIKeyManager
from app.models.user import User
from app.schemas.api_key import (

from app.api.auth_deps.security import get_current_user
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from typing import List

    APIKeyCreate,
    APIKeyListResponse,
    APIKeyResponse,
    APIKeyRevoke,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api-keys")

@router.post("/", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate, current_user: User = Depends(get_current_active_superuser)
) -> APIKeyResponse:
    """
    Create a new API key for the authenticated user.

    - **name**: Descriptive name for the API key
    - **tier**: Rate limiting tier (basic, standard, premium, enterprise)

    Returns the generated API key (only shown once).
    """
    try:
        # Validate tier
        if key_data.tier not in APIKeyManager.TIERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(APIKeyManager.TIERS.keys())}",
            )

        # Check if user can create keys of this tier
        if key_data.tier in ["premium", "enterprise"] and current_user.role not in [
            "super_admin",
            "admin",
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理員可以建立高級別 API 金鑰",
            )

        # Generate API key
        result = await APIKeyManager.generate_api_key(
            user_id=current_user.id, tier=key_data.tier, name=key_data.name
        )

        logger.info(
            f"API key created for user {current_user.id}",
            extra={
                "user_id": current_user.id,
                "tier": key_data.tier,
                "key_hash": result["key_hash"],
            },
        )

        return APIKeyResponse(
            api_key=result["api_key"],
            key_hash=result["key_hash"],
            name=key_data.name,
            tier=result["tier"],
            rate_limits=result["rate_limits"],
            message="請妥善保管此 API 金鑰，它將不會再次顯示",
        )

    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="建立 API 金鑰失敗",
        )

@router.get("/", response_model=List[APIKeyListResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
) -> List[APIKeyListResponse]:
    """
    List all API keys for the authenticated user.

    Returns a list of API key metadata (without the actual keys).
    """
    try:
        keys = await APIKeyManager.list_user_api_keys(current_user.id)

        return [
            APIKeyListResponse(
                key_hash=key["key_hash"],
                name=key.get("name", ""),
                tier=key["tier"],
                created_at=key["created_at"],
                last_used=key.get("last_used"),
                usage_count=key.get("usage_count", 0),
                active=key.get("active", True),
            )
            for key in keys
        ]

    except Exception as e:
        logger.error(f"Failed to list API keys: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取 API 金鑰列表失敗",
        )

@router.delete("/{key_hash}")
async def revoke_api_key(
    key_hash: str, current_user: User = Depends(get_current_user)
) -> dict:
    """
    Revoke an API key.

    - **key_hash**: The hash of the API key to revoke
    """
    try:
        success = await APIKeyManager.revoke_api_key(key_hash, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 金鑰不存在或您沒有權限撤銷它",
            )

        logger.info(
            f"API key revoked by user {current_user.id}",
            extra={"user_id": current_user.id, "key_hash": key_hash},
        )

        return {"message": "API 金鑰已成功撤銷"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤銷 API 金鑰失敗",
        )

@router.get("/tiers")
async def get_api_key_tiers(current_user: User = Depends(get_current_user)) -> dict:
    """
    Get available API key tiers and their rate limits.
    """
    # Filter tiers based on user role
    available_tiers = {}

    for tier, info in APIKeyManager.TIERS.items():
        if tier in ["premium", "enterprise"] and current_user.role not in [
            "super_admin",
            "admin",
        ]:
            continue
        available_tiers[tier] = info

    return {
        "tiers": available_tiers,
        "current_user_tier": "authenticated",
        "current_user_limits": {
            "rate_limit": (
                "200/hour"
                if current_user.role in ["admin", "super_admin"]
                else "100/hour"
            ),
            "burst_limit": (
                "40/minute"
                if current_user.role in ["admin", "super_admin"]
                else "20/minute"
            ),
        },
    }

@router.get("/usage/{key_hash}")
async def get_api_key_usage(
    key_hash: str, current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get usage statistics for a specific API key.

    - **key_hash**: The hash of the API key
    """
    try:
        # Get user's API keys
        keys = await APIKeyManager.list_user_api_keys(current_user.id)

        # Find the requested key
        key_info = None
        for key in keys:
            if key["key_hash"] == key_hash:
                key_info = key
                break

        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 金鑰不存在或您沒有權限查看它",
            )

        # Get current rate limit status from Redis
        from app.core.cache import cache

        # Calculate current usage (this is a simplified version)
        # In production, you would track actual usage in Redis
        current_hour_key = (
            f"rate_limit:api_key:{current_user.id}:{key_info['tier']}:hour"
        )
        current_minute_key = (
            f"rate_limit:api_key:{current_user.id}:{key_info['tier']}:minute"
        )

        hour_usage = await cache.get(current_hour_key) or "0"
        minute_usage = await cache.get(current_minute_key) or "0"

        tier_info = APIKeyManager.TIERS[key_info["tier"]]
        hour_limit = int(tier_info["rate_limit"].split("/")[0])
        minute_limit = int(tier_info["burst_limit"].split("/")[0])

        return {
            "key_hash": key_hash,
            "name": key_info.get("name", ""),
            "tier": key_info["tier"],
            "usage": {
                "current_hour": {
                    "used": int(hour_usage),
                    "limit": hour_limit,
                    "remaining": max(0, hour_limit - int(hour_usage)),
                },
                "current_minute": {
                    "used": int(minute_usage),
                    "limit": minute_limit,
                    "remaining": max(0, minute_limit - int(minute_usage)),
                },
                "total_requests": key_info.get("usage_count", 0),
                "last_used": key_info.get("last_used"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取 API 金鑰使用情況失敗",
        )
