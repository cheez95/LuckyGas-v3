"""SMS management API endpoints."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.core.config import settings
from app.models.notification import (
    NotificationStatus,
    ProviderConfig,
    SMSLog,
    SMSProvider,
    SMSTemplate,
)
from app.models.user import User
from app.schemas.sms import (
    ProviderConfigResponse,
    ProviderConfigUpdate,
    SMSLogResponse,
    SMSResendRequest,
    SMSSendRequest,
    SMSStatsResponse,
    SMSTemplateCreate,
    SMSTemplateResponse,
    SMSTemplateUpdate,
)
from app.services.sms_service import enhanced_sms_service

router = APIRouter()


@router.get("/sms/logs", response_model=List[SMSLogResponse])
async def get_sms_logs(
    start_date: datetime = Query(..., description="開始日期"),
    end_date: datetime = Query(..., description="結束日期"),
    status: Optional[str] = Query(None, description="狀態篩選"),
    provider: Optional[str] = Query(None, description="供應商篩選"),
    message_type: Optional[str] = Query(None, description="訊息類型篩選"),
    search: Optional[str] = Query(None, description="搜尋電話號碼"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SMS logs with filtering"""

    # Build query
    query = select(SMSLog).where(
        and_(SMSLog.created_at >= start_date, SMSLog.created_at <= end_date)
    )

    # Apply filters
    if status:
        query = query.where(SMSLog.status == status)
    if provider:
        query = query.where(SMSLog.provider == provider)
    if message_type:
        query = query.where(SMSLog.message_type == message_type)
    if search:
        query = query.where(SMSLog.recipient.contains(search))

    # Order by created_at desc
    query = query.order_by(SMSLog.created_at.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


@router.get("/sms/stats", response_model=SMSStatsResponse)
async def get_sms_stats(
    start_date: datetime = Query(..., description="開始日期"),
    end_date: datetime = Query(..., description="結束日期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SMS statistics"""

    # Get overall stats
    result = await db.execute(
        select(
            func.count(SMSLog.id).label("total"),
            func.sum(
                func.cast(SMSLog.status == NotificationStatus.DELIVERED, Integer)
            ).label("delivered"),
            func.sum(
                func.cast(SMSLog.status == NotificationStatus.FAILED, Integer)
            ).label("failed"),
            func.sum(
                func.cast(SMSLog.status == NotificationStatus.PENDING, Integer)
            ).label("pending"),
            func.sum(SMSLog.cost).label("total_cost"),
        ).where(and_(SMSLog.created_at >= start_date, SMSLog.created_at <= end_date))
    )

    stats = result.one()

    # Get provider-specific stats
    provider_result = await db.execute(
        select(
            SMSLog.provider,
            func.count(SMSLog.id).label("sent"),
            func.sum(
                func.cast(SMSLog.status == NotificationStatus.DELIVERED, Integer)
            ).label("delivered"),
            func.sum(
                func.cast(SMSLog.status == NotificationStatus.FAILED, Integer)
            ).label("failed"),
            func.sum(SMSLog.cost).label("cost"),
        )
        .where(and_(SMSLog.created_at >= start_date, SMSLog.created_at <= end_date))
        .group_by(SMSLog.provider)
    )

    provider_stats = {}
    for row in provider_result:
        provider_stats[row.provider] = {
            "sent": row.sent or 0,
            "delivered": row.delivered or 0,
            "failed": row.failed or 0,
            "cost": float(row.cost or 0),
        }

    # Calculate success rate
    total_sent = stats.total or 0
    total_delivered = stats.delivered or 0
    success_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0

    return {
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_failed": stats.failed or 0,
        "total_pending": stats.pending or 0,
        "total_cost": float(stats.total_cost or 0),
        "success_rate": success_rate,
        "provider_stats": provider_stats,
    }


@router.get("/sms/templates", response_model=List[SMSTemplateResponse])
async def get_sms_templates(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SMS templates"""

    query = select(SMSTemplate)

    if is_active is not None:
        query = query.where(SMSTemplate.is_active == is_active)

    query = query.order_by(SMSTemplate.code, SMSTemplate.variant)

    result = await db.execute(query)
    templates = result.scalars().all()

    return templates


@router.post("/sms/templates", response_model=SMSTemplateResponse)
async def create_sms_template(
    template: SMSTemplateCreate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Create new SMS template (superuser only)"""

    # Check if template code already exists
    result = await db.execute(
        select(SMSTemplate).where(
            and_(
                SMSTemplate.code == template.code,
                SMSTemplate.variant == template.variant,
            )
        )
    )

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Template {template.code} variant {template.variant} already exists",
        )

    db_template = SMSTemplate(**template.dict(), id=uuid.uuid4())

    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)

    return db_template


@router.put("/sms/templates/{template_id}", response_model=SMSTemplateResponse)
async def update_sms_template(
    template_id: str,
    template_update: SMSTemplateUpdate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Update SMS template (superuser only)"""

    result = await db.execute(select(SMSTemplate).where(SMSTemplate.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = template_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return template


@router.get("/sms/providers", response_model=List[ProviderConfigResponse])
async def get_sms_providers(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get SMS provider configurations"""

    result = await db.execute(
        select(ProviderConfig).order_by(ProviderConfig.priority.desc())
    )
    providers = result.scalars().all()

    # Add real-time health status
    for provider in providers:
        # This would check actual provider health
        provider.health_status = "healthy"  # Placeholder

    return providers


@router.put("/sms/providers/{provider}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider: SMSProvider,
    config_update: ProviderConfigUpdate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Update provider configuration (superuser only)"""

    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == provider)
    )
    config = result.scalar_one_or_none()

    if not config:
        # Create new config
        config = ProviderConfig(
            id=uuid.uuid4(),
            provider=provider,
            config={},  # Would be encrypted in production
            **config_update.dict(exclude_unset=True),
        )
        db.add(config)
    else:
        # Update existing
        update_data = config_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return config


@router.post("/sms/send")
async def send_sms(
    request: SMSSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send SMS message"""

    result = await enhanced_sms_service.send_sms(
        phone=request.phone,
        message=request.message,
        message_type=request.message_type,
        template_code=request.template_code,
        template_data=request.template_data,
        provider=request.provider,
        metadata=request.metadata,
        db=db,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "message_id": result["message_id"],
        "cost": result.get("cost", 0),
        "segments": result.get("segments", 1),
    }


@router.post("/sms/resend/{message_id}")
async def resend_sms(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resend failed SMS"""

    # Get original message
    result = await db.execute(select(SMSLog).where(SMSLog.id == message_id))
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Message not found")

    if original.status != NotificationStatus.FAILED:
        raise HTTPException(status_code=400, detail="Can only resend failed messages")

    # Send new message
    result = await enhanced_sms_service.send_sms(
        phone=original.recipient,
        message=original.message,
        message_type=original.message_type,
        metadata={"resend_of": str(original.id), **original.notification_metadata},
        db=db,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "message_id": result["message_id"],
        "original_id": str(original.id),
    }


@router.post("/sms/bulk-send")
async def send_bulk_sms(
    recipients: List[Dict[str, Any]] = Body(...),
    message_type: str = Body(...),
    template_code: Optional[str] = Body(None),
    provider: Optional[SMSProvider] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send bulk SMS to multiple recipients"""

    if len(recipients) > 1000:
        raise HTTPException(
            status_code=400, detail="Maximum 1000 recipients per request"
        )

    result = await enhanced_sms_service.send_bulk_sms(
        recipients=recipients,
        message_type=message_type,
        template_code=template_code,
        provider=provider,
    )

    return result


# Import required types
from sqlalchemy import Integer
