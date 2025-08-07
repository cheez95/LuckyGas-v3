from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.gas_product import DeliveryMethod
from app.models.gas_product import GasProduct as GasProductModel
from app.models.gas_product import ProductAttribute
from app.models.user import User as UserModel
from app.models.user import UserRole
from app.schemas.gas_product import (
    GasProduct,
    GasProductCreate,
    GasProductList,
    GasProductUpdate,
)

router = APIRouter()


@router.get("/", response_model=GasProductList)
async def get_products(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    delivery_method: Optional[DeliveryMethod] = None,
    size_kg: Optional[int] = None,
    attribute: Optional[ProductAttribute] = None,
    is_available: Optional[bool] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
) -> Any:
    """
    Retrieve gas products with filtering options
    """
    # Build base query
    base_query = select(GasProductModel)

    # Apply filters
    if delivery_method:
        base_query = base_query.where(
            GasProductModel.delivery_method == delivery_method
        )

    if size_kg:
        base_query = base_query.where(GasProductModel.size_kg == size_kg)

    if attribute:
        base_query = base_query.where(GasProductModel.attribute == attribute)

    if is_available is not None:
        base_query = base_query.where(GasProductModel.is_available == is_available)

    if is_active is not None:
        base_query = base_query.where(GasProductModel.is_active == is_active)

    if search:
        search_filter = or_(
            GasProductModel.sku.ilike(f"%{search}%"),
            GasProductModel.name_zh.ilike(f"%{search}%"),
            GasProductModel.name_en.ilike(f"%{search}%"),
        )
        base_query = base_query.where(search_filter)

    # Get total count
    count_query = select(func.count()).select_from(GasProductModel)
    # Apply the same filters to count query
    if delivery_method:
        count_query = count_query.where(
            GasProductModel.delivery_method == delivery_method
        )
    if size_kg:
        count_query = count_query.where(GasProductModel.size_kg == size_kg)
    if attribute:
        count_query = count_query.where(GasProductModel.attribute == attribute)
    if is_available is not None:
        count_query = count_query.where(GasProductModel.is_available == is_available)
    if is_active is not None:
        count_query = count_query.where(GasProductModel.is_active == is_active)
    if search:
        count_query = count_query.where(search_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination and ordering
    query = (
        base_query.order_by(
            GasProductModel.delivery_method,
            GasProductModel.size_kg,
            GasProductModel.attribute,
        )
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    products = result.scalars().all()

    return GasProductList(items=products, total=total, skip=skip, limit=limit)


@router.get("/available", response_model=GasProductList)
async def get_available_products(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    delivery_method: Optional[DeliveryMethod] = None,
    size_kg: Optional[int] = None,
    attribute: Optional[ProductAttribute] = None,
) -> Any:
    """
    Get only available products for ordering
    """
    # Build query for available and active products
    base_query = select(GasProductModel).where(
        GasProductModel.is_available, GasProductModel.is_active
    )

    # Apply filters
    if delivery_method:
        base_query = base_query.where(
            GasProductModel.delivery_method == delivery_method
        )

    if size_kg:
        base_query = base_query.where(GasProductModel.size_kg == size_kg)

    if attribute:
        base_query = base_query.where(GasProductModel.attribute == attribute)

    # Get total count
    count_query = (
        select(func.count())
        .select_from(GasProductModel)
        .where(GasProductModel.is_available, GasProductModel.is_active)
    )
    if delivery_method:
        count_query = count_query.where(
            GasProductModel.delivery_method == delivery_method
        )
    if size_kg:
        count_query = count_query.where(GasProductModel.size_kg == size_kg)
    if attribute:
        count_query = count_query.where(GasProductModel.attribute == attribute)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination and ordering
    query = (
        base_query.order_by(
            GasProductModel.delivery_method,
            GasProductModel.size_kg,
            GasProductModel.attribute,
        )
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    products = result.scalars().all()

    return GasProductList(items=products, total=total, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=GasProduct)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Get specific product details
    """
    result = await db.execute(
        select(GasProductModel).where(GasProductModel.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")

    return product


@router.post("/", response_model=GasProduct)
async def create_product(
    product_in: GasProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Create new gas product (admin only)
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="權限不足")

    # Check if product combination exists
    result = await db.execute(
        select(GasProductModel).where(
            GasProductModel.delivery_method == product_in.delivery_method,
            GasProductModel.size_kg == product_in.size_kg,
            GasProductModel.attribute == product_in.attribute,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="產品組合已存在")

    # Create product
    db_product = GasProductModel(**product_in.model_dump())

    # Generate SKU if not provided
    if not db_product.sku:
        db_product.sku = db_product.generate_sku()

    # Generate display name if name_zh not provided
    if not db_product.name_zh:
        db_product.name_zh = db_product.display_name

    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.put("/{product_id}", response_model=GasProduct)
async def update_product(
    product_id: int,
    product_in: GasProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Update gas product (admin only)
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="權限不足")

    # Get product
    result = await db.execute(
        select(GasProductModel).where(GasProductModel.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")

    # Update product
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Soft delete gas product (admin only)
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="權限不足")

    # Get product
    result = await db.execute(
        select(GasProductModel).where(GasProductModel.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")

    # Soft delete
    product.is_active = False
    product.is_available = False
    await db.commit()

    return {"message": "產品已停用"}
