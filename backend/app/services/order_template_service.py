from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.customer import Customer
from app.models.gas_product import GasProduct
from app.models.order_template import OrderTemplate
from app.models.user import User
from app.schemas.order import OrderCreateV2
from app.schemas.order_template import (CreateOrderFromTemplate,
                                        OrderTemplateCreate,
                                        OrderTemplateUpdate)
from app.services.order_service import OrderService

logger = get_logger(__name__)


class OrderTemplateService:
    """Service for managing order templates"""

    @staticmethod
    async def create_template(
        db: AsyncSession, template_data: OrderTemplateCreate, current_user: User
    ) -> OrderTemplate:
        """Create a new order template"""
        # Verify customer exists
        customer = await db.get(Customer, template_data.customer_id)
        if not customer:
            raise ValueError(f"客戶 ID {template_data.customer_id} 不存在")

        # Generate template code if not provided
        if not template_data.template_code:
            template_count = await db.execute(
                select(func.count())
                .select_from(OrderTemplate)
                .where(OrderTemplate.customer_id == template_data.customer_id)
            )
            count = template_count.scalar() or 0
            template_data.template_code = (
                f"{customer.customer_code}_TPL_{count + 1:03d}"
            )

        # Create template
        template = OrderTemplate(
            template_name=template_data.template_name,
            template_code=template_data.template_code,
            description=template_data.description,
            customer_id=template_data.customer_id,
            products=template_data.products,
            delivery_notes=template_data.delivery_notes,
            priority=template_data.priority,
            payment_method=template_data.payment_method,
            is_recurring=template_data.is_recurring,
            recurrence_pattern=template_data.recurrence_pattern,
            recurrence_interval=template_data.recurrence_interval,
            recurrence_days=template_data.recurrence_days,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        # Calculate next scheduled date if recurring
        if template.is_recurring:
            template.next_scheduled_date = (
                OrderTemplateService._calculate_next_scheduled_date(
                    template.recurrence_pattern,
                    template.recurrence_interval,
                    template.recurrence_days,
                )
            )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        logger.info(
            f"Created order template {template.template_code} for customer {customer.customer_code}"
        )
        return template

    @staticmethod
    async def get_template(
        db: AsyncSession, template_id: int, current_user: User
    ) -> Optional[OrderTemplate]:
        """Get a specific order template"""
        query = (
            select(OrderTemplate)
            .options(
                selectinload(OrderTemplate.customer),
                selectinload(OrderTemplate.creator),
                selectinload(OrderTemplate.updater),
            )
            .where(OrderTemplate.id == template_id)
        )

        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            return None

        # Enrich with product details
        await OrderTemplateService._enrich_product_details(db, template)

        return template

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        current_user: User,
        customer_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_recurring: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List order templates with filters"""
        query = select(OrderTemplate).options(selectinload(OrderTemplate.customer))

        # Apply filters
        conditions = []
        if customer_id:
            conditions.append(OrderTemplate.customer_id == customer_id)
        if is_active is not None:
            conditions.append(OrderTemplate.is_active == is_active)
        if is_recurring is not None:
            conditions.append(OrderTemplate.is_recurring == is_recurring)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(OrderTemplate)
        if conditions:
            count_query = count_query.where(and_(*conditions))

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(
            OrderTemplate.times_used.desc(), OrderTemplate.created_at.desc()
        )
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        templates = result.scalars().all()

        # Enrich with product details
        for template in templates:
            await OrderTemplateService._enrich_product_details(db, template)

        return {"templates": templates, "total": total, "skip": skip, "limit": limit}

    @staticmethod
    async def update_template(
        db: AsyncSession,
        template_id: int,
        template_data: OrderTemplateUpdate,
        current_user: User,
    ) -> Optional[OrderTemplate]:
        """Update an order template"""
        template = await db.get(OrderTemplate, template_id)
        if not template:
            return None

        # Update fields
        update_data = template_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_by = current_user.id
        template.updated_at = datetime.utcnow()

        # Recalculate next scheduled date if recurring settings changed
        if "is_recurring" in update_data or "recurrence_pattern" in update_data:
            if template.is_recurring:
                template.next_scheduled_date = (
                    OrderTemplateService._calculate_next_scheduled_date(
                        template.recurrence_pattern,
                        template.recurrence_interval,
                        template.recurrence_days,
                    )
                )
            else:
                template.next_scheduled_date = None

        await db.commit()
        await db.refresh(template)

        logger.info(f"Updated order template {template.template_code}")
        return template

    @staticmethod
    async def delete_template(
        db: AsyncSession, template_id: int, current_user: User
    ) -> bool:
        """Delete an order template (soft delete by setting is_active=False)"""
        template = await db.get(OrderTemplate, template_id)
        if not template:
            return False

        template.is_active = False
        template.updated_by = current_user.id
        template.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Deactivated order template {template.template_code}")
        return True

    @staticmethod
    async def create_order_from_template(
        db: AsyncSession, request: CreateOrderFromTemplate, current_user: User
    ) -> Any:
        """Create an order from a template"""
        # Get template
        template = await db.get(OrderTemplate, request.template_id)
        if not template:
            raise ValueError(f"模板 ID {request.template_id} 不存在")

        if not template.is_active:
            raise ValueError("此模板已停用")

        # Prepare order data
        products = request.override_products or template.products

        # Convert template products to order items format
        order_items = []
        for product in products:
            order_items.append(
                {
                    "gas_product_id": product.gas_product_id,
                    "quantity": product.quantity,
                    "unit_price": product.unit_price,
                    "discount_percentage": product.discount_percentage or 0,
                    "is_exchange": product.is_exchange,
                    "empty_received": product.empty_received or 0,
                }
            )

        # Create order data
        order_data = OrderCreateV2(
            customer_id=template.customer_id,
            scheduled_date=request.scheduled_date,
            is_urgent=request.override_priority == "urgent"
            or template.priority == "urgent",
            payment_method=request.override_payment_method or template.payment_method,
            delivery_notes=request.delivery_notes or template.delivery_notes,
            order_items=order_items,
        )

        # Create order using OrderService
        order = await OrderService.create_order_v2(db, order_data, current_user)

        # Update template usage
        template.times_used += 1
        template.last_used_at = datetime.utcnow()

        # Update next scheduled date if recurring
        if template.is_recurring:
            template.next_scheduled_date = (
                OrderTemplateService._calculate_next_scheduled_date(
                    template.recurrence_pattern,
                    template.recurrence_interval,
                    template.recurrence_days,
                    base_date=template.next_scheduled_date,
                )
            )

        await db.commit()

        logger.info(
            f"Created order {order.order_number} from template {template.template_code}"
        )
        return order

    @staticmethod
    async def get_templates_for_scheduling(
        db: AsyncSession, date: datetime
    ) -> List[OrderTemplate]:
        """Get templates that need to be scheduled for a specific date"""
        query = select(OrderTemplate).where(
            and_(
                OrderTemplate.is_active == True,
                OrderTemplate.is_recurring == True,
                OrderTemplate.next_scheduled_date <= date,
            )
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    def _calculate_next_scheduled_date(
        pattern: str,
        interval: int,
        days: Optional[List[int]] = None,
        base_date: Optional[datetime] = None,
    ) -> datetime:
        """Calculate the next scheduled date for a recurring template"""
        base = base_date or datetime.now()

        if pattern == "daily":
            return base + timedelta(days=interval)

        elif pattern == "weekly":
            if days:
                # Find next occurrence based on specified days
                current_weekday = base.weekday() + 1  # 1-7 (Mon-Sun)
                next_days = [d for d in days if d > current_weekday]

                if next_days:
                    # Next occurrence is in the current week
                    days_ahead = next_days[0] - current_weekday
                else:
                    # Next occurrence is in the next week interval
                    days_ahead = (7 * interval) - current_weekday + days[0]

                return base + timedelta(days=days_ahead)
            else:
                # Same day of week, every N weeks
                return base + timedelta(weeks=interval)

        elif pattern == "monthly":
            # Same day of month, every N months
            month = base.month + interval
            year = base.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1

            # Handle day overflow (e.g., Jan 31 -> Feb 28)
            try:
                return base.replace(year=year, month=month)
            except ValueError:
                # Day doesn't exist in target month, use last day
                import calendar

                last_day = calendar.monthrange(year, month)[1]
                return base.replace(year=year, month=month, day=last_day)

        else:
            # Default to daily
            return base + timedelta(days=1)

    @staticmethod
    async def _enrich_product_details(db: AsyncSession, template: OrderTemplate):
        """Enrich template with product details"""
        product_details = []

        for item in template.products:
            product = await db.get(GasProduct, item["gas_product_id"])
            if product:
                product_details.append(
                    {
                        "gas_product_id": product.id,
                        "product_name": product.display_name,
                        "product_code": product.product_code,
                        "quantity": item["quantity"],
                        "unit_price": item.get("unit_price") or product.unit_price,
                        "discount_percentage": item.get("discount_percentage", 0),
                        "is_exchange": item.get("is_exchange", False),
                        "empty_received": item.get("empty_received", 0),
                    }
                )

        template.product_details = product_details
