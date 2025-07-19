from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.api.deps import get_db, get_current_user
from app.models.user import User as UserModel, UserRole
from app.models.customer import Customer as CustomerModel
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate, CustomerList

router = APIRouter()


@router.get("/", response_model=CustomerList)
async def get_customers(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    area: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Any:
    """
    Retrieve customers
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Build base query for filtering
    base_query = select(CustomerModel)
    
    # Apply filters
    if area:
        base_query = base_query.where(CustomerModel.area == area)
    
    if is_active is not None:
        base_query = base_query.where(CustomerModel.is_terminated == (not is_active))
    
    if search:
        search_filter = or_(
            CustomerModel.customer_code.ilike(f"%{search}%"),
            CustomerModel.short_name.ilike(f"%{search}%"),
            CustomerModel.invoice_title.ilike(f"%{search}%"),
            CustomerModel.address.ilike(f"%{search}%")
        )
        base_query = base_query.where(search_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(CustomerModel)
    # Apply the same filters to count query
    if area:
        count_query = count_query.where(CustomerModel.area == area)
    if is_active is not None:
        count_query = count_query.where(CustomerModel.is_terminated == (not is_active))
    if search:
        count_query = count_query.where(search_filter)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Apply pagination to main query
    query = base_query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return CustomerList(
        items=customers,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> Any:
    """
    Get customer by ID
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="權限不足")
    
    result = await db.execute(
        select(CustomerModel).where(CustomerModel.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    return customer


@router.post("/", response_model=Customer)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> Any:
    """
    Create new customer
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Check if customer code exists
    result = await db.execute(
        select(CustomerModel).where(CustomerModel.customer_code == customer_in.customer_code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="客戶代碼已存在")
    
    # Create customer
    db_customer = CustomerModel(**customer_in.model_dump())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    
    return db_customer


@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> Any:
    """
    Update customer
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get customer
    result = await db.execute(
        select(CustomerModel).where(CustomerModel.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Update customer
    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    await db.commit()
    await db.refresh(customer)
    
    return customer


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> Any:
    """
    Delete customer (soft delete by marking as terminated)
    """
    # Check permissions - only super admin can delete
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get customer
    result = await db.execute(
        select(CustomerModel).where(CustomerModel.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Soft delete
    customer.is_terminated = True
    await db.commit()
    
    return {"message": "客戶已停用"}