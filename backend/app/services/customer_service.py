"""
Customer service layer for business logic
Handles customer-related operations and coordinates with repositories
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.core.cache import invalidate_cache
from app.core.metrics import cache_operations_counter, orders_created_counter

# from app.api.v1.socketio_handler import send_notification  # Removed during compaction

logger = logging.getLogger(__name__)


class CustomerService:
    """
    Service layer for customer business logic
    Coordinates between API, repositories, and external services
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.order_repo = OrderRepository(session)

    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Create new customer with validation

        Args:
            customer_data: Customer creation data

        Returns:
            Created customer

        Raises:
            ValueError: If customer code already exists
        """
        # Check if customer code exists
        existing = await self.customer_repo.get_by(
            customer_code=customer_data.customer_code
        )
        if existing:
            raise ValueError(f"客戶代碼 {customer_data.customer_code} 已存在")

        # Create customer
        customer_dict = customer_data.model_dump()
        customer = await self.customer_repo.create(**customer_dict)

        logger.info(f"Created customer {customer.customer_code}")

        # Send notification to office staff
        # Notification removed during compaction
        # await send_notification(
        #     user_id=0,  # Broadcast to role
        #     title="新客戶建立",
        #     message=f"新客戶 {customer.short_name} 已建立",
        #     priority="normal",
        #     callback=False
        # )

        return customer

    async def update_customer(
        self, customer_id: int, customer_update: CustomerUpdate
    ) -> Optional[Customer]:
        """
        Update customer information

        Args:
            customer_id: Customer ID
            customer_update: Update data

        Returns:
            Updated customer or None
        """
        # Get existing customer
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            return None

        # Update only provided fields
        update_data = customer_update.model_dump(exclude_unset=True)

        # Update customer
        updated_customer = await self.customer_repo.update(customer_id, **update_data)

        # Invalidate cache
        await self.customer_repo.invalidate_cache(customer_id)

        logger.info(f"Updated customer {customer_id}")

        return updated_customer

    async def get_customer_details(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive customer details including orders and statistics

        Args:
            customer_id: Customer ID

        Returns:
            Customer details dictionary or None
        """
        # Get customer with inventory
        customer = await self.customer_repo.get_with_inventory(customer_id)
        if not customer:
            return None

        # Get recent orders
        recent_orders = await self.order_repo.get_customer_order_history(
            customer_id, days=30, limit=10
        )

        # Calculate statistics
        total_orders = len(recent_orders)
        total_spent = sum(order.final_amount for order in recent_orders)

        # Calculate average consumption
        cylinder_totals = {
            "50kg": sum(order.qty_50kg for order in recent_orders),
            "20kg": sum(order.qty_20kg for order in recent_orders),
            "16kg": sum(order.qty_16kg for order in recent_orders),
            "10kg": sum(order.qty_10kg for order in recent_orders),
            "4kg": sum(order.qty_4kg for order in recent_orders),
        }

        return {
            "customer": customer,
            "recent_orders": recent_orders,
            "statistics": {
                "total_orders_30d": total_orders,
                "total_spent_30d": float(total_spent),
                "average_order_value": (
                    float(total_spent / total_orders) if total_orders > 0 else 0
                ),
                "cylinder_consumption_30d": cylinder_totals,
            },
        }

    async def search_customers(
        self,
        search_term: Optional[str] = None,
        area: Optional[str] = None,
        customer_type: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Customer], int]:
        """
        Search customers with various filters

        Args:
            search_term: Search in code, name, address
            area: Filter by area
            customer_type: Filter by type
            is_active: Filter active/inactive
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (customers list, total count)
        """
        if search_term:
            # Use search functionality
            return await self.customer_repo.search_customers(search_term, skip, limit)
        else:
            # Use filtered listing
            customers, total = await self.customer_repo.get_active_customers(
                area=area, customer_type=customer_type, skip=skip, limit=limit
            )

            # Track cache operation
            cache_operations_counter.labels(
                operation="list", status="success", api_type="general"
            ).inc()

            return customers, total

    async def get_delivery_candidates(
        self, target_date: date, area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get customers that may need delivery on target date

        Args:
            target_date: Target delivery date
            area: Optional area filter

        Returns:
            List of customer delivery recommendations
        """
        # Get customers needing delivery
        customers = await self.customer_repo.get_customers_needing_delivery(
            target_date, area
        )

        recommendations = []
        for customer in customers:
            # Get last order
            last_orders = await self.order_repo.get_customer_order_history(
                customer.id, days=60, limit=1
            )

            last_order = last_orders[0] if last_orders else None
            days_since_last = (
                (target_date - last_order.scheduled_date.date()).days
                if last_order
                else 999
            )

            # Calculate recommendation score
            score = self._calculate_delivery_score(customer, days_since_last)

            recommendations.append(
                {
                    "customer": customer,
                    "last_order": last_order,
                    "days_since_last": days_since_last,
                    "recommendation_score": score,
                    "suggested_products": self._suggest_products(customer, last_order),
                }
            )

        # Sort by recommendation score
        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)

        return recommendations

    def _calculate_delivery_score(
        self, customer: Customer, days_since_last: int
    ) -> float:
        """
        Calculate delivery recommendation score

        Args:
            customer: Customer object
            days_since_last: Days since last order

        Returns:
            Score from 0-100
        """
        score = 0.0

        # Base score from days since last order
        if customer.max_cycle_days and days_since_last >= customer.max_cycle_days:
            score += 50
        elif customer.max_cycle_days:
            score += (days_since_last / customer.max_cycle_days) * 30

        # Subscription bonus
        if customer.is_subscription:
            score += 20

        # Customer type bonus
        if customer.customer_type == "commercial":
            score += 10

        # Consumption rate bonus
        if customer.avg_daily_usage and customer.avg_daily_usage > 5:
            score += 10

        return min(score, 100.0)

    def _suggest_products(
        self, customer: Customer, last_order: Optional[Any]
    ) -> Dict[str, int]:
        """
        Suggest products based on history

        Args:
            customer: Customer object
            last_order: Last order if available

        Returns:
            Suggested product quantities
        """
        if last_order:
            # Suggest same as last order
            return {
                "50kg": last_order.qty_50kg,
                "20kg": last_order.qty_20kg,
                "16kg": last_order.qty_16kg,
                "10kg": last_order.qty_10kg,
                "4kg": last_order.qty_4kg,
            }
        else:
            # Default suggestion based on customer type
            if customer.customer_type == "commercial":
                return {"50kg": 2, "20kg": 2, "16kg": 0, "10kg": 0, "4kg": 0}
            else:
                return {"50kg": 0, "20kg": 1, "16kg": 0, "10kg": 0, "4kg": 1}

    async def update_inventory(
        self, customer_id: int, cylinder_updates: Dict[str, int]
    ) -> bool:
        """
        Update customer cylinder inventory

        Args:
            customer_id: Customer ID
            cylinder_updates: Cylinder count updates

        Returns:
            Success status
        """
        success = await self.customer_repo.update_cylinder_inventory(
            customer_id, cylinder_updates
        )

        if success:
            logger.info(f"Updated inventory for customer {customer_id}")

        return success

    async def get_area_statistics(self) -> Dict[str, Any]:
        """
        Get customer statistics by area

        Returns:
            Area statistics
        """
        area_counts = await self.customer_repo.get_customers_by_area()

        # Get total active customers
        total_active = sum(area_counts.values())

        return {
            "total_active_customers": total_active,
            "area_breakdown": area_counts,
            "areas": list(area_counts.keys()),
        }

    async def identify_vip_customers(self) -> List[Customer]:
        """
        Identify VIP customers for special treatment

        Returns:
            List of VIP customers
        """
        vip_customers = await self.customer_repo.get_high_value_customers(
            min_monthly_orders=4, min_avg_order_value=5000.0
        )

        logger.info(f"Identified {len(vip_customers)} VIP customers")

        return vip_customers

    async def deactivate_customer(self, customer_id: int, reason: str = "") -> bool:
        """
        Deactivate (soft delete) a customer

        Args:
            customer_id: Customer ID
            reason: Deactivation reason

        Returns:
            Success status
        """
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            return False

        # Update termination status
        await self.customer_repo.update(
            customer_id, is_terminated=True, updated_at=datetime.utcnow()
        )

        # Log reason if provided
        if reason:
            logger.info(f"Deactivated customer {customer_id}: {reason}")

        # Invalidate cache
        await self.customer_repo.invalidate_cache(customer_id)

        return True
