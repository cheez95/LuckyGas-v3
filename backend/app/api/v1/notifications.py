"""Notification and SMS API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.notification import (NotificationChannel, NotificationLog,
                                     NotificationStatus, ProviderConfig,
                                     SMSLog, SMSProvider, SMSTemplate)
from app.models.user import User, UserRole
from app.schemas.notification import (NotificationLogResponse,
                                      NotificationStatsResponse,
                                      ProviderConfigCreate,
                                      ProviderConfigResponse,
                                      ProviderConfigUpdate, SMSBulkSendRequest,
                                      SMSLogResponse, SMSSendRequest,
                                      SMSSendResponse, SMSStatusResponse,
                                      SMSTemplateCreate, SMSTemplateResponse,
                                      SMSTemplateUpdate)
from app.services.notification_service import notification_service
from app.services.sms_service import enhanced_sms_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send-sms", response_model=SMSSendResponse)
async def send_sms(
    request: SMSSendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send SMS notification"""
    # Check permissions
    if current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.MANAGER,
        UserRole.OFFICE_STAFF,
    ]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        result = await enhanced_sms_service.send_sms(
            phone=request.phone,
            message=request.message,
            message_type=request.message_type,
            template_code=request.template_code,
            template_data=request.template_data,
            provider=request.provider,
            metadata=(
                {
                    "sent_by": current_user.id,
                    "sent_by_name": current_user.full_name,
                    **request.metadata,
                }
                if request.metadata
                else {"sent_by": current_user.id}
            ),
            db=db,
        )

        return SMSSendResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sms-status/{message_id}", response_model=SMSStatusResponse)
async def get_sms_status(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check SMS delivery status"""
    result = await enhanced_sms_service.check_delivery_status(str(message_id), db)

    if not result["success"]:
        raise HTTPException(
            status_code=404, detail=result.get("error", "Message not found")
        )

    return SMSStatusResponse(**result)


@router.post("/send-bulk-sms", response_model=Dict[str, Any])
async def send_bulk_sms(
    request: SMSBulkSendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send bulk SMS to multiple recipients"""
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Prepare recipients
    recipients = []
    for recipient in request.recipients:
        recipients.append(
            {
                "phone": recipient.phone,
                "message": recipient.message or request.default_message,
                "data": recipient.template_data or {},
                "metadata": {
                    "bulk_send_id": request.batch_name,
                    "sent_by": current_user.id,
                    **(recipient.metadata or {}),
                },
            }
        )

    result = await enhanced_sms_service.send_bulk_sms(
        recipients=recipients,
        message_type=request.message_type,
        template_code=request.template_code,
        provider=request.provider,
        batch_size=request.batch_size or 100,
    )

    return result


# SMS Template Management
@router.post("/sms-templates", response_model=SMSTemplateResponse)
async def create_sms_template(
    template: SMSTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create SMS template"""
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check if template code already exists
    result = await db.execute(
        select(SMSTemplate).where(SMSTemplate.code == template.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Template code already exists")

    db_template = SMSTemplate(**template.dict())
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)

    return SMSTemplateResponse.from_orm(db_template)


@router.get("/sms-templates", response_model=List[SMSTemplateResponse])
async def list_sms_templates(
    is_active: Optional[bool] = None,
    language: Optional[str] = Query(None, description="Language code (e.g., zh-TW)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List SMS templates"""
    query = select(SMSTemplate)

    conditions = []
    if is_active is not None:
        conditions.append(SMSTemplate.is_active == is_active)
    if language:
        conditions.append(SMSTemplate.language == language)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(SMSTemplate.code, SMSTemplate.variant)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [SMSTemplateResponse.from_orm(t) for t in templates]


@router.put("/sms-templates/{template_id}", response_model=SMSTemplateResponse)
async def update_sms_template(
    template_id: UUID,
    template_update: SMSTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update SMS template"""
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(select(SMSTemplate).where(SMSTemplate.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in template_update.dict(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return SMSTemplateResponse.from_orm(template)


@router.delete("/sms-templates/{template_id}")
async def delete_sms_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete SMS template"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403, detail="Only super admin can delete templates"
        )

    result = await db.execute(select(SMSTemplate).where(SMSTemplate.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()

    return {"message": "Template deleted successfully"}


# Provider Configuration
@router.post("/providers", response_model=ProviderConfigResponse)
async def create_provider_config(
    config: ProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create provider configuration"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403, detail="Only super admin can manage providers"
        )

    # Check if provider already exists
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == config.provider)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Provider already configured")

    db_config = ProviderConfig(**config.dict())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)

    return ProviderConfigResponse.from_orm(db_config)


@router.get("/providers", response_model=List[ProviderConfigResponse])
async def list_provider_configs(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List provider configurations"""
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(ProviderConfig)
    if is_active is not None:
        query = query.where(ProviderConfig.is_active == is_active)
    query = query.order_by(ProviderConfig.priority.desc())

    result = await db.execute(query)
    configs = result.scalars().all()

    # Mask sensitive data for non-super-admin
    responses = []
    for config in configs:
        response = ProviderConfigResponse.from_orm(config)
        if current_user.role != UserRole.SUPER_ADMIN:
            # Mask sensitive config data
            response.config = {k: "***" for k in response.config.keys()}
        responses.append(response)

    return responses


@router.put("/providers/{provider}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider: SMSProvider,
    config_update: ProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update provider configuration"""
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403, detail="Only super admin can manage providers"
        )

    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == provider)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")

    for field, value in config_update.dict(exclude_unset=True).items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return ProviderConfigResponse.from_orm(config)


# SMS Logs and Analytics
@router.get("/sms-logs", response_model=List[SMSLogResponse])
async def list_sms_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[NotificationStatus] = None,
    provider: Optional[SMSProvider] = None,
    recipient: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List SMS logs with filtering"""
    query = select(SMSLog)

    conditions = []
    if start_date:
        conditions.append(SMSLog.created_at >= start_date)
    if end_date:
        conditions.append(SMSLog.created_at <= end_date)
    if status:
        conditions.append(SMSLog.status == status)
    if provider:
        conditions.append(SMSLog.provider == provider)
    if recipient:
        conditions.append(SMSLog.recipient.like(f"%{recipient}%"))

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(SMSLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [SMSLogResponse.from_orm(log) for log in logs]


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notification statistics"""
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # SMS statistics
    sms_query = select(
        func.count(SMSLog.id).label("total"),
        func.sum(func.cast(SMSLog.status == NotificationStatus.SENT, type_=int)).label(
            "sent"
        ),
        func.sum(
            func.cast(SMSLog.status == NotificationStatus.DELIVERED, type_=int)
        ).label("delivered"),
        func.sum(
            func.cast(SMSLog.status == NotificationStatus.FAILED, type_=int)
        ).label("failed"),
        func.sum(SMSLog.cost).label("total_cost"),
        func.sum(SMSLog.segments).label("total_segments"),
    ).where(and_(SMSLog.created_at >= start_date, SMSLog.created_at <= end_date))

    sms_result = await db.execute(sms_query)
    sms_stats = sms_result.one()

    # Provider breakdown
    provider_query = (
        select(
            SMSLog.provider,
            func.count(SMSLog.id).label("count"),
            func.sum(SMSLog.cost).label("cost"),
            func.sum(
                func.cast(SMSLog.status == NotificationStatus.DELIVERED, type_=int)
            ).label("delivered"),
        )
        .where(and_(SMSLog.created_at >= start_date, SMSLog.created_at <= end_date))
        .group_by(SMSLog.provider)
    )

    provider_result = await db.execute(provider_query)
    provider_stats = [
        {
            "provider": row.provider,
            "count": row.count,
            "cost": float(row.cost or 0),
            "delivered": row.delivered,
            "success_rate": (row.delivered / row.count * 100) if row.count > 0 else 0,
        }
        for row in provider_result
    ]

    return NotificationStatsResponse(
        start_date=start_date,
        end_date=end_date,
        sms_stats={
            "total": sms_stats.total or 0,
            "sent": sms_stats.sent or 0,
            "delivered": sms_stats.delivered or 0,
            "failed": sms_stats.failed or 0,
            "total_cost": float(sms_stats.total_cost or 0),
            "total_segments": sms_stats.total_segments or 0,
            "delivery_rate": (
                (sms_stats.delivered / sms_stats.total * 100) if sms_stats.total else 0
            ),
        },
        provider_breakdown=provider_stats,
    )
