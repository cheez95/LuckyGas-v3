from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
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
def get_products(
    db: Session = Depends(get_db),
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
    query = db.query(GasProductModel)

    # Apply filters
    if delivery_method:
        query = query.filter(GasProductModel.delivery_method == delivery_method)

    if size_kg:
        query = query.filter(GasProductModel.size_kg == size_kg)

    if attribute:
        query = query.filter(GasProductModel.attribute == attribute)

    if is_available is not None:
        query = query.filter(GasProductModel.is_available == is_available)

    if is_active is not None:
        query = query.filter(GasProductModel.is_active == is_active)

    if search:
        search_filter = or_(
            GasProductModel.sku.ilike(f"%{search}%"),
            GasProductModel.name_zh.ilike(f"%{search}%"),
            GasProductModel.name_en.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    products = query.order_by(
        GasProductModel.delivery_method,
        GasProductModel.size_kg,
        GasProductModel.attribute,
    ).offset(skip).limit(limit).all()

    return GasProductList(items=products, total=total, skip=skip, limit=limit)


@router.get("/available", response_model=GasProductList)
def get_available_products(
    db: Session = Depends(get_db),
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
    query = db.query(GasProductModel).filter(
        GasProductModel.is_available == True,
        GasProductModel.is_active == True
    )

    # Apply filters
    if delivery_method:
        query = query.filter(GasProductModel.delivery_method == delivery_method)

    if size_kg:
        query = query.filter(GasProductModel.size_kg == size_kg)

    if attribute:
        query = query.filter(GasProductModel.attribute == attribute)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    products = query.order_by(
        GasProductModel.delivery_method,
        GasProductModel.size_kg,
        GasProductModel.attribute,
    ).offset(skip).limit(limit).all()

    return GasProductList(items=products, total=total, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=GasProduct)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Get specific product details
    """
    product = db.query(GasProductModel).filter(
        GasProductModel.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")

    return product


@router.post("/", response_model=GasProduct)
def create_product(
    product_in: GasProductCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Create new gas product (admin only)
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="權限不足")

    # Check if product combination exists
    existing = db.query(GasProductModel).filter(
        GasProductModel.delivery_method == product_in.delivery_method,
        GasProductModel.size_kg == product_in.size_kg,
        GasProductModel.attribute == product_in.attribute,
    ).first()
    
    if existing:
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
    db.commit()
    db.refresh(db_product)

    return db_product


@router.put("/{product_id}", response_model=GasProduct)
def update_product(
    product_id: int,
    product_in: GasProductUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Update gas product (admin only)
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="權限不足")

    # Get product
    product = db.query(GasProductModel).filter(
        GasProductModel.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")

    # Update product
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Soft delete gas product (admin only)
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_ADMIN and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="權限不足")

    # Get product
    product = db.query(GasProductModel).filter(
        GasProductModel.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")

    # Soft delete
    product.is_active = False
    product.is_available = False
    db.commit()

    return {"message": "產品已停用"}


# Include import/export routes
from app.api.v1.products_import import router as import_router
router.include_router(import_router)