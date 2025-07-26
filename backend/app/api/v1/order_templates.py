from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.order_template import (
    OrderTemplate,
    OrderTemplateCreate,
    OrderTemplateUpdate,
    OrderTemplateList,
    CreateOrderFromTemplate
)
from app.schemas.order import OrderV2
from app.services.order_template_service import OrderTemplateService
from app.core.security import verify_user_role

router = APIRouter()


@router.post("/", response_model=OrderTemplate)
async def create_order_template(
    template_data: OrderTemplateCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    建立訂單模板
    
    - 需要 office_staff 以上權限
    - 每個客戶可以建立多個模板
    - 支援定期訂單設定
    """
    verify_user_role(current_user, ["super_admin", "manager", "office_staff"])
    
    try:
        template = await OrderTemplateService.create_template(db, template_data, current_user)
        return template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="建立模板失敗")


@router.get("/", response_model=OrderTemplateList)
async def list_order_templates(
    customer_id: Optional[int] = Query(None, description="客戶ID篩選"),
    is_active: Optional[bool] = Query(None, description="是否啟用"),
    is_recurring: Optional[bool] = Query(None, description="是否為定期訂單"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    取得訂單模板列表
    
    - 支援多種篩選條件
    - 按使用次數和建立時間排序
    """
    result = await OrderTemplateService.list_templates(
        db,
        current_user,
        customer_id=customer_id,
        is_active=is_active,
        is_recurring=is_recurring,
        skip=skip,
        limit=limit
    )
    return result


@router.get("/{template_id}", response_model=OrderTemplate)
async def get_order_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """取得特定訂單模板詳情"""
    template = await OrderTemplateService.get_template(db, template_id, current_user)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/{template_id}", response_model=OrderTemplate)
async def update_order_template(
    template_id: int,
    template_data: OrderTemplateUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    更新訂單模板
    
    - 需要 office_staff 以上權限
    - 記錄更新歷程
    """
    verify_user_role(current_user, ["super_admin", "manager", "office_staff"])
    
    template = await OrderTemplateService.update_template(db, template_id, template_data, current_user)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.delete("/{template_id}")
async def delete_order_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    刪除訂單模板
    
    - 需要 manager 以上權限
    - 軟刪除，保留歷史記錄
    """
    verify_user_role(current_user, ["super_admin", "manager"])
    
    success = await OrderTemplateService.delete_template(db, template_id, current_user)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return {"message": "模板已停用"}


@router.post("/create-order", response_model=OrderV2)
async def create_order_from_template(
    request: CreateOrderFromTemplate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    從模板建立訂單
    
    - 需要 office_staff 以上權限
    - 可覆寫模板中的部分設定
    - 自動更新模板使用次數
    """
    verify_user_role(current_user, ["super_admin", "manager", "office_staff"])
    
    try:
        order = await OrderTemplateService.create_order_from_template(db, request, current_user)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="建立訂單失敗")


@router.get("/customer/{customer_id}/templates", response_model=List[OrderTemplate])
async def get_customer_templates(
    customer_id: int,
    active_only: bool = Query(True, description="只顯示啟用的模板"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    取得特定客戶的所有模板
    
    - 用於訂單建立頁面的快速選擇
    - 預設只顯示啟用的模板
    """
    result = await OrderTemplateService.list_templates(
        db,
        current_user,
        customer_id=customer_id,
        is_active=active_only if active_only else None
    )
    return result["templates"]