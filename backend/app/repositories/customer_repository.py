"""
Customer repository for data access operations
Implements customer-specific queries and operations
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.metrics import cache_operations_counter
from app.models.customer import Customer
from app.models.customer_inventory import CustomerInventory
from app.models.order import Order
from app.repositories.base import BaseRepository, CachedRepository

from datetime import timedelta

logger = logging.getLogger(__name__)


class CustomerRepository(CachedRepository[Customer]):
    """
    Repository for customer data operations
    Extends CachedRepository for customer-specific functionality
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session, cache_prefix="customer")

    async def get_with_inventory(self, customer_id: int) -> Optional[Customer]:
        """
        Get customer with inventory items loaded

        Args:
            customer_id: Customer ID

        Returns:
            Customer with inventory or None
        """
        query = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.inventory_items))
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_customers(
        self,
        area: Optional[str] = None,
        customer_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        """
        Get active customers with filtering and pagination

        Args:
            area: Filter by area
            customer_type: Filter by customer type
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (customers list, total count)
        """
        # Base query for active customers
        base_query = select(Customer).where(Customer.is_terminated == False)
        count_query = (
            select(func.count())
            .select_from(Customer)
            .where(Customer.is_terminated == False)
        )

        # Apply filters
        if area:
            base_query = base_query.where(Customer.area == area)
            count_query = count_query.where(Customer.area == area)

        if customer_type:
            base_query = base_query.where(Customer.customer_type == customer_type)
            count_query = count_query.where(Customer.customer_type == customer_type)

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = base_query.order_by(Customer.short_name).offset(skip).limit(limit)

        result = await self.session.execute(query)
        customers = result.scalars().all()

        return customers, total

    async def search_customers(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Customer], int]:
        """
        Search customers by code, name, or address

        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (customers list, total count)
        """
        search_pattern = f"%{search_term}%"

        # Search query
        search_filter = or_(
            Customer.customer_code.ilike(search_pattern),
            Customer.short_name.ilike(search_pattern),
            Customer.invoice_title.ilike(search_pattern),
            Customer.address.ilike(search_pattern),
        )

        # Count query
        count_query = select(func.count()).select_from(Customer).where(search_filter)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Main query with pagination
        query = (
            select(Customer)
            .where(search_filter)
            .order_by(Customer.short_name)
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        customers = result.scalars().all()

        # Track cache operation
        cache_operations_counter.labels(
            operation="search", status="success", api_type="general"
        ).inc()

        return customers, total

    async def get_customers_needing_delivery(
        self, date: date, area: Optional[str] = None
    ) -> List[Customer]:
        """
        Get customers that need delivery on a specific date
        Based on their consumption patterns and last delivery

        Args:
            date: Target delivery date
            area: Optional area filter

        Returns:
            List of customers needing delivery
        """
        # This is a complex query that would join with orders and predictions
        # For now, return customers with subscription or regular delivery
        query = select(Customer).where(
            and_(Customer.is_terminated == False, Customer.is_subscription == True)
        )

        if area:
            query = query.where(Customer.area == area)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_customer_with_recent_orders(
        self, customer_id: int, days: int = 30
    ) -> Optional[Customer]:
        """
        Get customer with recent orders loaded

        Args:
            customer_id: Customer ID
            days: Number of days to look back for orders

        Returns:
            Customer with recent orders or None
        """
        query = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(
                selectinload(Customer.orders).options(selectinload(Order.order_items))
            )
        )

        result = await self.session.execute(query)
        customer = result.scalar_one_or_none()

        if customer and customer.orders:
            # Filter orders in Python (simpler than complex SQL)
            cutoff_date = datetime.now() - timedelta(days=days)
            customer.orders = [
                order for order in customer.orders if order.created_at >= cutoff_date
            ]

        return customer

    async def update_cylinder_inventory(
        self, customer_id: int, cylinder_updates: Dict[str, int]
    ) -> bool:
        """
        Update customer cylinder inventory

        Args:
            customer_id: Customer ID
            cylinder_updates: Dict of cylinder size to quantity

        Returns:
            True if updated successfully
        """
        customer = await self.get(customer_id)
        if not customer:
            return False

        # Update cylinder counts
        for size, quantity in cylinder_updates.items():
            field_name = f"cylinders_{size}"
            if hasattr(customer, field_name):
                setattr(customer, field_name, quantity)

        await self.session.commit()
        await self.invalidate_cache(customer_id)

        return True

    async def get_customers_by_area(self) -> Dict[str, int]:
        """
        Get customer count by area

        Returns:
            Dictionary of area to customer count
        """
        query = (
            select(Customer.area, func.count(Customer.id))
            .where(Customer.is_terminated == False)
            .group_by(Customer.area)
        )

        result = await self.session.execute(query)
        area_counts = {area: count for area, count in result.all() if area}

        return area_counts

    async def get_high_value_customers(
        self, min_monthly_orders: int = 4, min_avg_order_value: float = 5000.0
    ) -> List[Customer]:
        """
        Get high-value customers based on order frequency and value

        Args:
            min_monthly_orders: Minimum orders per month
            min_avg_order_value: Minimum average order value

        Returns:
            List of high-value customers
        """
        # Complex query using window functions
        # This would analyze order history to identify VIP customers
        # For now, return customers with subscription
        query = (
            select(Customer)
            .where(
                and_(
                    Customer.is_terminated == False,
                    Customer.is_subscription == True,
                    Customer.customer_type == "commercial",
                )
            )
            .order_by(Customer.short_name)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_update_areas(self, area_updates: List[Dict[str, Any]]) -> int:
        """
        Bulk update customer areas for route optimization

        Args:
            area_updates: List of dicts with 'id' and 'area'

        Returns:
            Number of customers updated
        """
        if not area_updates:
            return 0

        # Use bulk update for efficiency
        stmt = Customer.__table__.update().where(
            Customer.id == func.any_([update["id"] for update in area_updates])
        )

        updated = 0
        for update in area_updates:
            await self.session.execute(
                stmt.where(Customer.id == update["id"]).values(area=update["area"])
            )
            await self.invalidate_cache(update["id"])
            updated += 1

        await self.session.commit()

        logger.info(f"Bulk updated {updated} customer areas")
        return updated
