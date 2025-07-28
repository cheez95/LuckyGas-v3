"""
API endpoints for feature flag management.

Provides REST API for managing feature flags with full audit trail.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_active_superuser
from app.models.user import User
from app.services.feature_flags_enhanced import (
    get_feature_flag_service,
    FeatureFlagCreate,
    FeatureFlagUpdate,
    EvaluationContext,
    VariantCreate
)
from app.models.feature_flag import FeatureFlagType, FeatureFlagStatus

router = APIRouter(prefix="/feature-flags", tags=["feature_flags"])


def get_evaluation_context(request: Request, current_user: Optional[User] = None) -> EvaluationContext:
    """Extract evaluation context from request."""
    return EvaluationContext(
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.headers.get("x-request-id")
    )


@router.post("/", response_model=Dict[str, str])
async def create_feature_flag(
    flag_data: FeatureFlagCreate,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Create a new feature flag.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    try:
        flag_id = await service.create_flag(
            flag_data,
            created_by=current_user.id,
            context=context
        )
        
        return {
            "flag_id": flag_id,
            "message": f"功能標誌 '{flag_data.name}' 已創建"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[Dict[str, Any]])
async def list_feature_flags(
    include_archived: bool = Query(False, description="Include archived flags"),
    current_user: User = Depends(get_current_user),
    service = Depends(get_feature_flag_service)
) -> List[Dict[str, Any]]:
    """
    List all feature flags.
    """
    flags = await service.get_all_flags(include_archived=include_archived)
    return flags


@router.get("/{flag_name}", response_model=Dict[str, Any])
async def get_feature_flag(
    flag_name: str,
    current_user: User = Depends(get_current_user),
    service = Depends(get_feature_flag_service)
) -> Dict[str, Any]:
    """
    Get a specific feature flag.
    """
    flag = await service.get_flag(flag_name)
    
    if not flag:
        raise HTTPException(status_code=404, detail="功能標誌不存在")
        
    return flag


@router.put("/{flag_name}", response_model=Dict[str, str])
async def update_feature_flag(
    flag_name: str,
    update_data: FeatureFlagUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Update a feature flag.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.update_flag(
        flag_name,
        update_data,
        updated_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="功能標誌不存在")
        
    return {
        "message": f"功能標誌 '{flag_name}' 已更新"
    }


@router.delete("/{flag_name}", response_model=Dict[str, str])
async def delete_feature_flag(
    flag_name: str,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Archive a feature flag (soft delete).
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.delete_flag(
        flag_name,
        deleted_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="功能標誌不存在")
        
    return {
        "message": f"功能標誌 '{flag_name}' 已封存"
    }


@router.get("/{flag_name}/evaluate", response_model=Dict[str, Any])
async def evaluate_feature_flag(
    flag_name: str,
    request: Request,
    customer_id: Optional[str] = Query(None, description="Customer ID for evaluation"),
    current_user: Optional[User] = Depends(get_current_user),
    service = Depends(get_feature_flag_service)
) -> Dict[str, Any]:
    """
    Evaluate a feature flag for a specific context.
    """
    context = EvaluationContext(
        customer_id=customer_id,
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.headers.get("x-request-id")
    )
    
    flag = await service.get_flag(flag_name)
    if not flag:
        raise HTTPException(status_code=404, detail="功能標誌不存在")
        
    result = {
        "flag_name": flag_name,
        "enabled": await service.is_enabled(flag_name, context),
        "type": flag["type"]
    }
    
    if flag["type"] == FeatureFlagType.VARIANT.value:
        result["variant"] = await service.get_variant(flag_name, context)
        
    return result


@router.post("/{flag_name}/customers/{customer_id}", response_model=Dict[str, str])
async def add_customer_to_flag(
    flag_name: str,
    customer_id: str,
    enabled: bool = Body(True, description="Whether to enable or disable for customer"),
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Add a customer to a feature flag.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.add_customer_to_flag(
        flag_name,
        customer_id,
        enabled,
        added_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="功能標誌不存在")
        
    action = "已啟用" if enabled else "已停用"
    return {
        "message": f"客戶 {customer_id} 的功能標誌 '{flag_name}' {action}"
    }


@router.delete("/{flag_name}/customers/{customer_id}", response_model=Dict[str, str])
async def remove_customer_from_flag(
    flag_name: str,
    customer_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Remove a customer from a feature flag.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.remove_customer_from_flag(
        flag_name,
        customer_id,
        removed_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="功能標誌不存在")
        
    return {
        "message": f"客戶 {customer_id} 已從功能標誌 '{flag_name}' 中移除"
    }


@router.get("/customer/{customer_id}/flags", response_model=Dict[str, Any])
async def get_customer_flags(
    customer_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    service = Depends(get_feature_flag_service)
) -> Dict[str, Any]:
    """
    Get all feature flags for a customer.
    """
    context = EvaluationContext(
        customer_id=customer_id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.headers.get("x-request-id")
    )
    
    flags = await service.get_customer_flags(customer_id, context)
    
    return {
        "customer_id": customer_id,
        "flags": flags,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{flag_name}/audit", response_model=List[Dict[str, Any]])
async def get_feature_flag_audit_trail(
    flag_name: str,
    limit: int = Query(100, description="Maximum number of audit entries"),
    offset: int = Query(0, description="Offset for pagination"),
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> List[Dict[str, Any]]:
    """
    Get audit trail for a feature flag.
    
    Requires admin privileges.
    """
    audits = await service.get_flag_audit_trail(flag_name, limit, offset)
    
    if not audits and offset == 0:
        # Check if flag exists
        flag = await service.get_flag(flag_name)
        if not flag:
            raise HTTPException(status_code=404, detail="功能標誌不存在")
            
    return audits


@router.get("/{flag_name}/analytics", response_model=Dict[str, Any])
async def get_feature_flag_analytics(
    flag_name: str,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    current_user: User = Depends(get_current_user),
    service = Depends(get_feature_flag_service)
) -> Dict[str, Any]:
    """
    Get analytics for a feature flag.
    """
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
        
    analytics = await service.get_flag_analytics(flag_name, start_date, end_date)
    
    if not analytics:
        # Check if flag exists
        flag = await service.get_flag(flag_name)
        if not flag:
            raise HTTPException(status_code=404, detail="功能標誌不存在")
            
    return analytics


# Pilot program specific endpoints

@router.get("/pilot/customers", response_model=Dict[str, Any])
async def get_pilot_customers(
    current_user: User = Depends(get_current_user),
    service = Depends(get_feature_flag_service)
) -> Dict[str, Any]:
    """
    Get all customers in the pilot program.
    """
    customers = await service.get_pilot_customers()
    
    return {
        "total": len(customers),
        "customer_ids": list(customers)
    }


@router.post("/pilot/customers/{customer_id}", response_model=Dict[str, str])
async def add_pilot_customer(
    customer_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Add a customer to the pilot program.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.add_pilot_customer(
        customer_id,
        added_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="無法將客戶加入試點計劃")
        
    return {
        "message": f"客戶 {customer_id} 已加入試點計劃"
    }


@router.delete("/pilot/customers/{customer_id}", response_model=Dict[str, str])
async def remove_pilot_customer(
    customer_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Remove a customer from the pilot program.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.remove_pilot_customer(
        customer_id,
        removed_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="無法從試點計劃中移除客戶")
        
    return {
        "message": f"客戶 {customer_id} 已從試點計劃中移除"
    }


# Percentage rollout endpoint

@router.put("/{flag_name}/percentage", response_model=Dict[str, str])
async def update_percentage_rollout(
    flag_name: str,
    percentage: float = Body(..., ge=0, le=100, description="Rollout percentage"),
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_feature_flag_service)
) -> Dict[str, str]:
    """
    Update the percentage rollout for a feature flag.
    
    Requires admin privileges.
    """
    context = get_evaluation_context(request, current_user)
    
    success = await service.update_percentage_rollout(
        flag_name,
        percentage,
        updated_by=current_user.id,
        context=context
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="功能標誌不存在或不是百分比類型")
        
    return {
        "message": f"功能標誌 '{flag_name}' 的推出百分比已更新為 {percentage}%"
    }