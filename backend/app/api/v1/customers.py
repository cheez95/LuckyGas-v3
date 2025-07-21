from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from datetime import timedelta

from app.api.deps import get_db, get_current_user
from app.models.user import User as UserModel, UserRole
from app.models.customer import Customer as CustomerModel
from app.models.customer_inventory import CustomerInventory as CustomerInventoryModel
from app.models.gas_product import GasProduct as GasProductModel
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate, CustomerList
from app.schemas.customer_inventory import CustomerInventory, CustomerInventoryUpdate, CustomerInventoryList
from app.services.customer_service import CustomerService
from app.core.cache import cache_result, cache

router = APIRouter()


@router.get("/", response_model=CustomerList)
@cache_result("customers:list", expire=timedelta(minutes=15))
async def get_customers(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    area: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[str] = None
) -> Any:
    """
    Retrieve customers
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Initialize service
    customer_service = CustomerService(db)
    
    # Convert is_active string to boolean
    is_active_bool = True
    if is_active is not None:
        is_active_bool = is_active.lower() in ['true', '1', 'yes'] if isinstance(is_active, str) else bool(is_active)
    
    # Use service to search/list customers
    customers, total = await customer_service.search_customers(
        search_term=search,
        area=area,
        customer_type=None,
        is_active=is_active_bool,
        skip=skip,
        limit=limit
    )
    
    return CustomerList(
        items=customers,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{customer_id}", response_model=Customer)
@cache_result("customers:detail", expire=timedelta(hours=2))
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
    
    # Initialize service
    customer_service = CustomerService(db)
    
    # Get customer using service
    customer_details = await customer_service.get_customer_details(customer_id)
    
    if not customer_details:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    return customer_details["customer"]


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
    
    # Initialize service
    customer_service = CustomerService(db)
    
    try:
        # Create customer using service
        customer = await customer_service.create_customer(customer_in)
        
        # Clear customer-related cache
        await cache.invalidate("customers:*")
        
        return customer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    
    # Initialize service
    customer_service = CustomerService(db)
    
    # Update customer using service
    customer = await customer_service.update_customer(customer_id, customer_in)
    
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Clear customer-related cache after update
    await cache.invalidate("customers:*")
    
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
    
    # Initialize service
    customer_service = CustomerService(db)
    
    # Deactivate customer using service
    success = await customer_service.deactivate_customer(customer_id, reason="由管理員停用")
    
    if not success:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Clear customer-related cache after delete
    await cache.invalidate("customers:*")
    
    return {"message": "客戶已停用"}


# Customer Inventory Endpoints

@router.get("/{customer_id}/inventory", response_model=CustomerInventoryList)
@cache_result("customers:inventory", expire=timedelta(hours=1))
async def get_customer_inventory(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None
) -> Any:
    """
    Get customer's product inventory
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF, UserRole.DRIVER]
    if current_user.role not in allowed_roles:
        # Customers can only view their own inventory
        if current_user.role == UserRole.CUSTOMER:
            # TODO: Check if this customer belongs to the user
            pass
        else:
            raise HTTPException(status_code=403, detail="權限不足")
    
    # Check if customer exists
    customer_result = await db.execute(
        select(CustomerModel).where(CustomerModel.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Build query
    base_query = select(CustomerInventoryModel).options(
        selectinload(CustomerInventoryModel.gas_product)
    ).where(
        CustomerInventoryModel.customer_id == customer_id
    )
    
    # Apply filters
    if is_active is not None:
        base_query = base_query.where(CustomerInventoryModel.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(CustomerInventoryModel).where(
        CustomerInventoryModel.customer_id == customer_id
    )
    if is_active is not None:
        count_query = count_query.where(CustomerInventoryModel.is_active == is_active)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Apply pagination
    query = base_query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    inventory_items = result.scalars().all()
    
    return CustomerInventoryList(
        items=inventory_items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.put("/{customer_id}/inventory/{product_id}", response_model=CustomerInventory)
async def update_customer_inventory(
    customer_id: int,
    product_id: int,
    inventory_update: CustomerInventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> Any:
    """
    Update customer's inventory count for a specific product
    """
    # Check permissions
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Check if customer and product exist
    customer_result = await db.execute(
        select(CustomerModel).where(CustomerModel.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    product_result = await db.execute(
        select(GasProductModel).where(GasProductModel.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="產品不存在")
    
    # Get or create inventory record
    inventory_result = await db.execute(
        select(CustomerInventoryModel).where(
            CustomerInventoryModel.customer_id == customer_id,
            CustomerInventoryModel.gas_product_id == product_id
        )
    )
    inventory = inventory_result.scalar_one_or_none()
    
    if not inventory:
        # Create new inventory record
        inventory = CustomerInventoryModel(
            customer_id=customer_id,
            gas_product_id=product_id
        )
        db.add(inventory)
    
    # Update inventory
    update_data = inventory_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)
    
    # Update total if owned or rented changed
    if 'quantity_owned' in update_data or 'quantity_rented' in update_data:
        inventory.update_total()
    
    await db.commit()
    await db.refresh(inventory)
    
    # Load related data
    await db.refresh(inventory, ["gas_product"])
    
    # Clear customer inventory cache after update
    await cache.invalidate("customers:inventory:*")
    
    return inventory