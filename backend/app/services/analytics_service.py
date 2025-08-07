"""Analytics service for generating dashboard metrics and reports."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage import StorageService
from app.models import (
    Customer,
    CustomerInventory,
    DeliveryHistory,
    GasProduct,
    Invoice,
    Order,
    OrderItem,
    Payment,
    Route,
    User,
)
from app.models.order import OrderStatus
from app.models.route import RouteStatus
from app.models.route_delivery import DeliveryStatus
from app.services.email_service import EmailService


class AnalyticsService:
    """Service for generating analytics and reports."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()
        self.storage_service = StorageService()

    async def get_revenue_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get revenue metrics for executive dashboard."""
        # Total revenue
        revenue_query = select(
            func.sum(Order.total_amount).label("total"),
            func.count(Order.id).label("order_count"),
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
            )
        )
        result = await self.db.execute(revenue_query)
        revenue_data = result.first()

        # Previous period comparison
        period_days = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_days)
        prev_end = start_date

        prev_query = select(func.sum(Order.total_amount).label("total")).where(
            and_(
                Order.created_at >= prev_start,
                Order.created_at < prev_end,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
            )
        )
        prev_result = await self.db.execute(prev_query)
        prev_revenue = prev_result.scalar() or 0

        current_revenue = revenue_data.total or 0
        growth = (
            ((current_revenue - prev_revenue) / prev_revenue * 100)
            if prev_revenue > 0
            else 0
        )

        # Daily revenue trend
        daily_query = (
            select(
                func.date(Order.created_at).label("date"),
                func.sum(Order.total_amount).label("amount"),
            )
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by(func.date(Order.created_at))
            .order_by("date")
        )

        daily_result = await self.db.execute(daily_query)
        daily_revenue = [
            {"date": row.date.isoformat(), "amount": float(row.amount or 0)}
            for row in daily_result
        ]

        # Revenue by product
        product_query = (
            select(
                GasProduct.name,
                func.sum(OrderItem.subtotal).label("amount"),
                func.sum(OrderItem.quantity).label("quantity"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .join(GasProduct, OrderItem.product_id == GasProduct.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by(GasProduct.id, GasProduct.name)
        )

        product_result = await self.db.execute(product_query)
        revenue_by_product = [
            {
                "product": row.name,
                "amount": float(row.amount or 0),
                "quantity": row.quantity or 0,
            }
            for row in product_result
        ]

        return {
            "total": float(current_revenue),
            "growth": round(growth, 2),
            "orderCount": revenue_data.order_count or 0,
            "averageOrderValue": (
                float(current_revenue / revenue_data.order_count)
                if revenue_data.order_count
                else 0
            ),
            "dailyTrend": daily_revenue,
            "byProduct": revenue_by_product,
            "previousPeriod": float(prev_revenue),
        }

    async def get_order_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get order metrics for dashboards."""
        # Order status breakdown
        status_query = (
            select(Order.status, func.count(Order.id).label("count"))
            .where(and_(Order.created_at >= start_date, Order.created_at <= end_date))
            .group_by(Order.status)
        )

        status_result = await self.db.execute(status_query)
        status_breakdown = {row.status: row.count for row in status_result}

        # Total orders
        total_orders = sum(status_breakdown.values())

        # Hourly distribution
        hourly_query = (
            select(
                func.extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("count"),
            )
            .where(and_(Order.created_at >= start_date, Order.created_at <= end_date))
            .group_by("hour")
            .order_by("hour")
        )

        hourly_result = await self.db.execute(hourly_query)
        hourly_distribution = [
            {"hour": int(row.hour), "count": row.count} for row in hourly_result
        ]

        # Order type distribution
        type_query = (
            select(Order.order_type, func.count(Order.id).label("count"))
            .where(and_(Order.created_at >= start_date, Order.created_at <= end_date))
            .group_by(Order.order_type)
        )

        type_result = await self.db.execute(type_query)
        order_types = {row.order_type: row.count for row in type_result}

        return {
            "total": total_orders,
            "statusBreakdown": status_breakdown,
            "completed": status_breakdown.get(OrderStatus.COMPLETED, 0),
            "pending": status_breakdown.get(OrderStatus.PENDING, 0),
            "cancelled": status_breakdown.get(OrderStatus.CANCELLED, 0),
            "hourlyDistribution": hourly_distribution,
            "orderTypes": order_types,
            "completionRate": round(
                (
                    (
                        status_breakdown.get(OrderStatus.COMPLETED, 0)
                        / total_orders
                        * 100
                    )
                    if total_orders > 0
                    else 0
                ),
                2,
            ),
        }

    async def get_customer_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get customer metrics for dashboards."""
        # Total customers
        total_query = select(func.count(Customer.id)).where(Customer.is_active)
        total_result = await self.db.execute(total_query)
        total_customers = total_result.scalar() or 0

        # New customers
        new_query = select(func.count(Customer.id)).where(
            and_(Customer.created_at >= start_date, Customer.created_at <= end_date)
        )
        new_result = await self.db.execute(new_query)
        new_customers = new_result.scalar() or 0

        # Active customers (with orders in period)
        active_query = select(func.count(func.distinct(Order.customer_id))).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        active_result = await self.db.execute(active_query)
        active_customers = active_result.scalar() or 0

        # Top customers by revenue
        top_customers_query = (
            select(
                Customer.id,
                Customer.name,
                Customer.business_name,
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("order_count"),
            )
            .select_from(Order)
            .join(Customer, Order.customer_id == Customer.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by(Customer.id, Customer.name, Customer.business_name)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(10)
        )

        top_result = await self.db.execute(top_customers_query)
        top_customers = [
            {
                "id": row.id,
                "name": row.business_name or row.name,
                "revenue": float(row.revenue or 0),
                "orderCount": row.order_count,
            }
            for row in top_result
        ]

        # Customer segments
        segment_query = (
            select(Customer.customer_type, func.count(Customer.id).label("count"))
            .where(Customer.is_active)
            .group_by(Customer.customer_type)
        )

        segment_result = await self.db.execute(segment_query)
        customer_segments = {row.customer_type: row.count for row in segment_result}

        # Retention rate (customers who ordered in both current and previous period)
        period_days = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_days)

        retention_query = text(
            """
            SELECT COUNT(DISTINCT current_period.customer_id) as retained
            FROM (
                SELECT DISTINCT customer_id
                FROM orders
                WHERE created_at >= :current_start
                AND created_at <= :current_end
                AND status IN ('completed', 'delivered')
            ) current_period
            INNER JOIN (
                SELECT DISTINCT customer_id
                FROM orders
                WHERE created_at >= :prev_start
                AND created_at < :current_start
                AND status IN ('completed', 'delivered')
            ) prev_period ON current_period.customer_id = prev_period.customer_id
        """
        )

        retention_result = await self.db.execute(
            retention_query,
            {
                "current_start": start_date,
                "current_end": end_date,
                "prev_start": prev_start,
            },
        )
        retained_customers = retention_result.scalar() or 0

        return {
            "total": total_customers,
            "new": new_customers,
            "active": active_customers,
            "topCustomers": top_customers,
            "segments": customer_segments,
            "retentionRate": round(
                (
                    (retained_customers / active_customers * 100)
                    if active_customers > 0
                    else 0
                ),
                2,
            ),
            "churnRate": round(
                (
                    100 - (retained_customers / active_customers * 100)
                    if active_customers > 0
                    else 0
                ),
                2,
            ),
        }

    async def get_cash_flow_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get cash flow metrics for financial dashboard."""
        # Cash inflows (payments received)
        inflow_query = (
            select(
                func.date(Payment.payment_date).label("date"),
                func.sum(Payment.amount).label("amount"),
            )
            .where(
                and_(
                    Payment.payment_date >= start_date,
                    Payment.payment_date <= end_date,
                    Payment.status == "completed",
                )
            )
            .group_by(func.date(Payment.payment_date))
        )

        inflow_result = await self.db.execute(inflow_query)
        daily_inflows = {
            row.date.isoformat(): float(row.amount or 0) for row in inflow_result
        }

        # Outstanding receivables
        receivables_query = select(
            func.sum(Invoice.total_amount - Invoice.paid_amount).label("outstanding")
        ).where(and_(Invoice.status != "paid", Invoice.due_date <= end_date))

        receivables_result = await self.db.execute(receivables_query)
        outstanding_receivables = receivables_result.scalar() or 0

        # Payment methods breakdown
        payment_method_query = (
            select(
                Payment.payment_method,
                func.sum(Payment.amount).label("amount"),
                func.count(Payment.id).label("count"),
            )
            .where(
                and_(
                    Payment.payment_date >= start_date,
                    Payment.payment_date <= end_date,
                    Payment.status == "completed",
                )
            )
            .group_by(Payment.payment_method)
        )

        method_result = await self.db.execute(payment_method_query)
        payment_methods = [
            {
                "method": row.payment_method,
                "amount": float(row.amount or 0),
                "count": row.count,
            }
            for row in method_result
        ]

        # Generate daily cash flow
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        cash_flow_trend = []
        cumulative_cash = 0

        for date in date_range:
            date_str = date.date().isoformat()
            daily_cash = daily_inflows.get(date_str, 0)
            cumulative_cash += daily_cash

            cash_flow_trend.append(
                {"date": date_str, "inflow": daily_cash, "cumulative": cumulative_cash}
            )

        total_inflow = sum(daily_inflows.values())

        return {
            "totalInflow": float(total_inflow),
            "outstandingReceivables": float(outstanding_receivables),
            "dailyTrend": cash_flow_trend,
            "paymentMethods": payment_methods,
            "collectionRate": round(
                (
                    (total_inflow / (total_inflow + outstanding_receivables) * 100)
                    if (total_inflow + outstanding_receivables) > 0
                    else 0
                ),
                2,
            ),
        }

    async def get_performance_comparison(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get month - over - month performance comparison."""
        # Current month metrics
        current_metrics = await self._get_period_metrics(start_date, end_date)

        # Previous month
        period_days = (end_date - start_date).days
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)
        prev_metrics = await self._get_period_metrics(prev_start, prev_end)

        # Year - over - year comparison
        year_ago_end = end_date - timedelta(days=365)
        year_ago_start = start_date - timedelta(days=365)
        year_ago_metrics = await self._get_period_metrics(year_ago_start, year_ago_end)

        def calculate_change(current, previous):
            if previous == 0:
                return 0
            return round((current - previous) / previous * 100, 2)

        return {
            "current": current_metrics,
            "previous": prev_metrics,
            "yearAgo": year_ago_metrics,
            "monthOverMonth": {
                "revenue": calculate_change(
                    current_metrics["revenue"], prev_metrics["revenue"]
                ),
                "orders": calculate_change(
                    current_metrics["orders"], prev_metrics["orders"]
                ),
                "customers": calculate_change(
                    current_metrics["activeCustomers"], prev_metrics["activeCustomers"]
                ),
            },
            "yearOverYear": {
                "revenue": calculate_change(
                    current_metrics["revenue"], year_ago_metrics["revenue"]
                ),
                "orders": calculate_change(
                    current_metrics["orders"], year_ago_metrics["orders"]
                ),
                "customers": calculate_change(
                    current_metrics["activeCustomers"],
                    year_ago_metrics["activeCustomers"],
                ),
            },
        }

    async def _get_period_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Helper to get metrics for a specific period."""
        # Revenue
        revenue_query = select(func.sum(Order.total_amount)).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
            )
        )
        revenue_result = await self.db.execute(revenue_query)
        revenue = revenue_result.scalar() or 0

        # Orders
        orders_query = select(func.count(Order.id)).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        orders_result = await self.db.execute(orders_query)
        orders = orders_result.scalar() or 0

        # Active customers
        customers_query = select(func.count(func.distinct(Order.customer_id))).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        customers_result = await self.db.execute(customers_query)
        active_customers = customers_result.scalar() or 0

        return {
            "revenue": float(revenue),
            "orders": orders,
            "activeCustomers": active_customers,
            "averageOrderValue": float(revenue / orders) if orders > 0 else 0,
        }

    async def get_top_performing_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get top performing routes, drivers, and products."""
        # Top routes by delivery count
        routes_query = (
            select(
                Route.name,
                func.count(DeliveryHistory.id).label("delivery_count"),
                func.avg(
                    func.extract(
                        "epoch",
                        DeliveryHistory.completed_at - DeliveryHistory.started_at,
                    )
                    / 60
                ).label("avg_time"),
            )
            .select_from(Route)
            .join(DeliveryHistory, Route.id == DeliveryHistory.route_id)
            .where(
                and_(
                    DeliveryHistory.completed_at >= start_date,
                    DeliveryHistory.completed_at <= end_date,
                    DeliveryHistory.status == DeliveryStatus.COMPLETED,
                )
            )
            .group_by(Route.id, Route.name)
            .order_by(func.count(DeliveryHistory.id).desc())
            .limit(5)
        )

        routes_result = await self.db.execute(routes_query)
        top_routes = [
            {
                "name": row.name,
                "deliveryCount": row.delivery_count,
                "avgDeliveryTime": round(row.avg_time or 0, 2),
            }
            for row in routes_result
        ]

        # Top drivers by efficiency
        drivers_query = (
            select(
                User.name,
                func.count(DeliveryHistory.id).label("delivery_count"),
                func.sum(
                    case(
                        (DeliveryHistory.status == DeliveryStatus.COMPLETED, 1), else_=0
                    )
                ).label("completed_count"),
            )
            .select_from(User)
            .join(DeliveryHistory, User.id == DeliveryHistory.driver_id)
            .where(
                and_(
                    DeliveryHistory.created_at >= start_date,
                    DeliveryHistory.created_at <= end_date,
                )
            )
            .group_by(User.id, User.name)
            .having(func.count(DeliveryHistory.id) > 0)
            .order_by(
                (
                    func.sum(
                        case(
                            (DeliveryHistory.status == DeliveryStatus.COMPLETED, 1),
                            else_=0,
                        )
                    )
                    / func.count(DeliveryHistory.id)
                ).desc()
            )
            .limit(5)
        )

        drivers_result = await self.db.execute(drivers_query)
        top_drivers = [
            {
                "name": row.name,
                "deliveryCount": row.delivery_count,
                "completionRate": round(
                    (
                        (row.completed_count / row.delivery_count * 100)
                        if row.delivery_count > 0
                        else 0
                    ),
                    2,
                ),
            }
            for row in drivers_result
        ]

        # Top products by revenue
        products_query = (
            select(
                GasProduct.name,
                func.sum(OrderItem.subtotal).label("revenue"),
                func.sum(OrderItem.quantity).label("quantity"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .join(GasProduct, OrderItem.product_id == GasProduct.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by(GasProduct.id, GasProduct.name)
            .order_by(func.sum(OrderItem.subtotal).desc())
            .limit(5)
        )

        products_result = await self.db.execute(products_query)
        top_products = [
            {
                "name": row.name,
                "revenue": float(row.revenue or 0),
                "quantity": row.quantity or 0,
            }
            for row in products_result
        ]

        return {"routes": top_routes, "drivers": top_drivers, "products": top_products}

    async def get_realtime_order_status(self, date: datetime) -> Dict[str, Any]:
        """Get real - time order status for operations dashboard."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Orders by status
        status_query = (
            select(
                Order.status,
                func.count(Order.id).label("count"),
                func.sum(Order.total_amount).label("amount"),
            )
            .where(
                and_(Order.created_at >= start_of_day, Order.created_at <= end_of_day)
            )
            .group_by(Order.status)
        )

        status_result = await self.db.execute(status_query)
        order_status = {
            row.status: {"count": row.count, "amount": float(row.amount or 0)}
            for row in status_result
        }

        # Recent orders (last 10)
        recent_query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(
                and_(Order.created_at >= start_of_day, Order.created_at <= end_of_day)
            )
            .order_by(Order.created_at.desc())
            .limit(10)
        )

        recent_result = await self.db.execute(recent_query)
        recent_orders = [
            {
                "id": order.id,
                "orderNumber": order.order_number,
                "customer": order.customer.business_name or order.customer.name,
                "status": order.status,
                "amount": float(order.total_amount),
                "createdAt": order.created_at.isoformat(),
                "items": [
                    {"product": item.product.name, "quantity": item.quantity}
                    for item in order.items
                ],
            }
            for order in recent_result.scalars()
        ]

        # Hourly order trend
        hourly_query = (
            select(
                func.extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("count"),
            )
            .where(
                and_(
                    Order.created_at >= start_of_day, Order.created_at <= datetime.now()
                )
            )
            .group_by("hour")
            .order_by("hour")
        )

        hourly_result = await self.db.execute(hourly_query)
        hourly_trend = [
            {"hour": int(row.hour), "count": row.count} for row in hourly_result
        ]

        return {
            "statusBreakdown": order_status,
            "recentOrders": recent_orders,
            "hourlyTrend": hourly_trend,
            "lastUpdated": datetime.now().isoformat(),
        }

    async def get_driver_utilization(self, date: datetime) -> Dict[str, Any]:
        """Get driver utilization metrics."""
        # Active drivers today
        active_drivers_query = select(func.count(func.distinct(Route.driver_id))).where(
            and_(Route.date == date.date(), Route.status != RouteStatus.CANCELLED)
        )
        active_result = await self.db.execute(active_drivers_query)
        active_drivers = active_result.scalar() or 0

        # Total drivers
        total_drivers_query = select(func.count(User.id)).where(
            and_(User.role == "driver", User.is_active)
        )
        total_result = await self.db.execute(total_drivers_query)
        total_drivers = total_result.scalar() or 0

        # Driver performance
        driver_stats_query = (
            select(
                User.id,
                User.name,
                Route.id.label("route_id"),
                Route.status,
                func.count(DeliveryHistory.id).label("delivery_count"),
                func.sum(
                    case(
                        (DeliveryHistory.status == DeliveryStatus.COMPLETED, 1), else_=0
                    )
                ).label("completed_count"),
            )
            .select_from(User)
            .join(Route, User.id == Route.driver_id)
            .outerjoin(DeliveryHistory, Route.id == DeliveryHistory.route_id)
            .where(and_(Route.date == date.date(), User.role == "driver"))
            .group_by(User.id, User.name, Route.id, Route.status)
        )

        driver_result = await self.db.execute(driver_stats_query)

        driver_performance = []
        driver_summary = {}

        for row in driver_result:
            if row.id not in driver_summary:
                driver_summary[row.id] = {
                    "name": row.name,
                    "routes": 0,
                    "deliveries": 0,
                    "completed": 0,
                    "status": "idle",
                }

            driver_summary[row.id]["routes"] += 1
            driver_summary[row.id]["deliveries"] += row.delivery_count or 0
            driver_summary[row.id]["completed"] += row.completed_count or 0

            if row.status == RouteStatus.IN_PROGRESS:
                driver_summary[row.id]["status"] = "active"
            elif (
                row.status == RouteStatus.COMPLETED
                and driver_summary[row.id]["status"] == "idle"
            ):
                driver_summary[row.id]["status"] = "completed"

        driver_performance = list(driver_summary.values())

        utilization_rate = round(
            (active_drivers / total_drivers * 100) if total_drivers > 0 else 0, 2
        )

        return {
            "totalDrivers": total_drivers,
            "activeDrivers": active_drivers,
            "utilizationRate": utilization_rate,
            "driverPerformance": driver_performance,
            "summary": {
                "idle": len([d for d in driver_performance if d["status"] == "idle"]),
                "active": len(
                    [d for d in driver_performance if d["status"] == "active"]
                ),
                "completed": len(
                    [d for d in driver_performance if d["status"] == "completed"]
                ),
            },
        }

    async def get_route_efficiency_metrics(self, date: datetime) -> Dict[str, Any]:
        """Get route efficiency metrics."""
        # Routes for the day
        routes_query = (
            select(
                Route.id,
                Route.name,
                Route.status,
                Route.planned_start_time,
                Route.actual_start_time,
                Route.planned_end_time,
                Route.actual_end_time,
                func.count(DeliveryHistory.id).label("delivery_count"),
                func.sum(
                    case(
                        (DeliveryHistory.status == DeliveryStatus.COMPLETED, 1), else_=0
                    )
                ).label("completed_count"),
            )
            .outerjoin(DeliveryHistory, Route.id == DeliveryHistory.route_id)
            .where(Route.date == date.date())
            .group_by(
                Route.id,
                Route.name,
                Route.status,
                Route.planned_start_time,
                Route.actual_start_time,
                Route.planned_end_time,
                Route.actual_end_time,
            )
        )

        routes_result = await self.db.execute(routes_query)

        routes = []
        total_routes = 0
        on_time_routes = 0
        total_deliveries = 0
        completed_deliveries = 0

        for row in routes_result:
            total_routes += 1
            total_deliveries += row.delivery_count or 0
            completed_deliveries += row.completed_count or 0

            # Calculate if route is on time
            on_time = True
            if row.actual_start_time and row.planned_start_time:
                start_delay = (
                    row.actual_start_time - row.planned_start_time
                ).total_seconds() / 60
                if start_delay > 15:  # 15 minutes tolerance
                    on_time = False

            if on_time and row.actual_end_time and row.planned_end_time:
                end_delay = (
                    row.actual_end_time - row.planned_end_time
                ).total_seconds() / 60
                if end_delay > 30:  # 30 minutes tolerance
                    on_time = False

            if on_time:
                on_time_routes += 1

            efficiency = round(
                (
                    (row.completed_count / row.delivery_count * 100)
                    if row.delivery_count > 0
                    else 0
                ),
                2,
            )

            routes.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "status": row.status,
                    "deliveryCount": row.delivery_count or 0,
                    "completedCount": row.completed_count or 0,
                    "efficiency": efficiency,
                    "onTime": on_time,
                }
            )

        overall_efficiency = round(
            (
                (completed_deliveries / total_deliveries * 100)
                if total_deliveries > 0
                else 0
            ),
            2,
        )

        on_time_rate = round(
            (on_time_routes / total_routes * 100) if total_routes > 0 else 0, 2
        )

        return {
            "totalRoutes": total_routes,
            "totalDeliveries": total_deliveries,
            "completedDeliveries": completed_deliveries,
            "overallEfficiency": overall_efficiency,
            "onTimeRate": on_time_rate,
            "routes": routes,
            "statusBreakdown": {
                "planned": len(
                    [r for r in routes if r["status"] == RouteStatus.PLANNED]
                ),
                "inProgress": len(
                    [r for r in routes if r["status"] == RouteStatus.IN_PROGRESS]
                ),
                "completed": len(
                    [r for r in routes if r["status"] == RouteStatus.COMPLETED]
                ),
                "cancelled": len(
                    [r for r in routes if r["status"] == RouteStatus.CANCELLED]
                ),
            },
        }

    async def get_delivery_success_metrics(self, date: datetime) -> Dict[str, Any]:
        """Get delivery success metrics."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Delivery status breakdown
        status_query = (
            select(
                DeliveryHistory.status, func.count(DeliveryHistory.id).label("count")
            )
            .where(
                and_(
                    DeliveryHistory.created_at >= start_of_day,
                    DeliveryHistory.created_at <= end_of_day,
                )
            )
            .group_by(DeliveryHistory.status)
        )

        status_result = await self.db.execute(status_query)
        status_breakdown = {row.status: row.count for row in status_result}

        total_deliveries = sum(status_breakdown.values())
        successful_deliveries = status_breakdown.get(DeliveryStatus.COMPLETED, 0)

        # Average delivery time
        time_query = select(
            func.avg(
                func.extract(
                    "epoch", DeliveryHistory.completed_at - DeliveryHistory.started_at
                )
                / 60
            ).label("avg_time")
        ).where(
            and_(
                DeliveryHistory.completed_at >= start_of_day,
                DeliveryHistory.completed_at <= end_of_day,
                DeliveryHistory.status == DeliveryStatus.COMPLETED,
            )
        )

        time_result = await self.db.execute(time_query)
        avg_delivery_time = time_result.scalar() or 0

        # Failure reasons
        failure_query = (
            select(DeliveryHistory.notes, func.count(DeliveryHistory.id).label("count"))
            .where(
                and_(
                    DeliveryHistory.created_at >= start_of_day,
                    DeliveryHistory.created_at <= end_of_day,
                    DeliveryHistory.status == DeliveryStatus.FAILED,
                )
            )
            .group_by(DeliveryHistory.notes)
            .limit(5)
        )

        failure_result = await self.db.execute(failure_query)
        failure_reasons = [
            {"reason": row.notes or "未指定原因", "count": row.count}
            for row in failure_result
        ]

        success_rate = round(
            (
                (successful_deliveries / total_deliveries * 100)
                if total_deliveries > 0
                else 0
            ),
            2,
        )

        return {
            "totalDeliveries": total_deliveries,
            "successfulDeliveries": successful_deliveries,
            "successRate": success_rate,
            "averageDeliveryTime": round(avg_delivery_time, 2),
            "statusBreakdown": status_breakdown,
            "failureReasons": failure_reasons,
        }

    async def get_equipment_inventory_status(self) -> Dict[str, Any]:
        """Get equipment inventory status."""
        # Gas cylinder inventory by type
        inventory_query = (
            select(
                GasProduct.name,
                GasProduct.size,
                func.sum(CustomerInventory.quantity).label("customer_inventory"),
                func.sum(CustomerInventory.empty_quantity).label("empty_cylinders"),
            )
            .select_from(GasProduct)
            .outerjoin(CustomerInventory, GasProduct.id == CustomerInventory.product_id)
            .group_by(GasProduct.id, GasProduct.name, GasProduct.size)
        )

        inventory_result = await self.db.execute(inventory_query)

        inventory_status = []
        total_cylinders = 0
        total_empty = 0

        for row in inventory_result:
            customer_inv = row.customer_inventory or 0
            empty = row.empty_cylinders or 0
            total = customer_inv + empty

            total_cylinders += total
            total_empty += empty

            inventory_status.append(
                {
                    "product": row.name,
                    "size": row.size,
                    "totalCylinders": total,
                    "inUse": customer_inv,
                    "empty": empty,
                    "utilizationRate": round(
                        (customer_inv / total * 100) if total > 0 else 0, 2
                    ),
                }
            )

        # Vehicle status (mock data for now)
        vehicle_status = {"total": 15, "active": 12, "maintenance": 2, "available": 1}

        return {
            "cylinders": {
                "total": total_cylinders,
                "inUse": total_cylinders - total_empty,
                "empty": total_empty,
                "byType": inventory_status,
            },
            "vehicles": vehicle_status,
            "alerts": [],  # Equipment alerts would go here
        }

    async def get_operational_alerts(self) -> List[Dict[str, Any]]:
        """Get operational alerts and warnings."""
        alerts = []

        # Check for delayed routes
        delayed_routes_query = select(func.count(Route.id)).where(
            and_(
                Route.date == datetime.now().date(),
                Route.status == RouteStatus.IN_PROGRESS,
                Route.planned_end_time < datetime.now(),
            )
        )

        delayed_result = await self.db.execute(delayed_routes_query)
        delayed_routes = delayed_result.scalar() or 0

        if delayed_routes > 0:
            alerts.append(
                {
                    "type": "warning",
                    "category": "route",
                    "message": f"{delayed_routes} 條路線延遲",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check for low inventory
        low_inventory_query = (
            select(GasProduct.name, func.sum(CustomerInventory.quantity).label("total"))
            .select_from(GasProduct)
            .outerjoin(CustomerInventory, GasProduct.id == CustomerInventory.product_id)
            .group_by(GasProduct.id, GasProduct.name)
            .having(func.sum(CustomerInventory.quantity) < 50)  # Threshold
        )

        low_inventory_result = await self.db.execute(low_inventory_query)

        for row in low_inventory_result:
            alerts.append(
                {
                    "type": "info",
                    "category": "inventory",
                    "message": f"{row.name} 庫存偏低 (剩餘 {row.total or 0} 個)",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check for failed deliveries today
        failed_deliveries_query = select(func.count(DeliveryHistory.id)).where(
            and_(
                func.date(DeliveryHistory.created_at) == datetime.now().date(),
                DeliveryHistory.status == DeliveryStatus.FAILED,
            )
        )

        failed_result = await self.db.execute(failed_deliveries_query)
        failed_deliveries = failed_result.scalar() or 0

        if failed_deliveries > 5:  # Threshold
            alerts.append(
                {
                    "type": "error",
                    "category": "delivery",
                    "message": f"今日有 {failed_deliveries} 筆配送失敗",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return alerts

    async def get_accounts_receivable_aging(self) -> Dict[str, Any]:
        """Get accounts receivable aging report."""
        today = datetime.now().date()

        # Aging buckets
        aging_query = (
            select(
                case(
                    (Invoice.due_date >= today, "current"),
                    (Invoice.due_date >= today - timedelta(days=30), "1 - 30"),
                    (Invoice.due_date >= today - timedelta(days=60), "31 - 60"),
                    (Invoice.due_date >= today - timedelta(days=90), "61 - 90"),
                    else_="over90",
                ).label("aging_bucket"),
                func.count(Invoice.id).label("count"),
                func.sum(Invoice.total_amount - Invoice.paid_amount).label("amount"),
            )
            .where(
                and_(
                    Invoice.status != "paid", Invoice.total_amount > Invoice.paid_amount
                )
            )
            .group_by("aging_bucket")
        )

        aging_result = await self.db.execute(aging_query)

        aging_breakdown = {
            "current": {"count": 0, "amount": 0},
            "1 - 30": {"count": 0, "amount": 0},
            "31 - 60": {"count": 0, "amount": 0},
            "61 - 90": {"count": 0, "amount": 0},
            "over90": {"count": 0, "amount": 0},
        }

        total_receivables = 0
        total_count = 0

        for row in aging_result:
            aging_breakdown[row.aging_bucket] = {
                "count": row.count,
                "amount": float(row.amount or 0),
            }
            total_receivables += row.amount or 0
            total_count += row.count

        # Top debtors
        debtors_query = (
            select(
                Customer.id,
                Customer.name,
                Customer.business_name,
                func.sum(Invoice.total_amount - Invoice.paid_amount).label("amount"),
                func.count(Invoice.id).label("invoice_count"),
            )
            .select_from(Invoice)
            .join(Customer, Invoice.customer_id == Customer.id)
            .where(
                and_(
                    Invoice.status != "paid", Invoice.total_amount > Invoice.paid_amount
                )
            )
            .group_by(Customer.id, Customer.name, Customer.business_name)
            .order_by(func.sum(Invoice.total_amount - Invoice.paid_amount).desc())
            .limit(10)
        )

        debtors_result = await self.db.execute(debtors_query)
        top_debtors = [
            {
                "id": row.id,
                "name": row.business_name or row.name,
                "amount": float(row.amount or 0),
                "invoiceCount": row.invoice_count,
            }
            for row in debtors_result
        ]

        return {
            "totalReceivables": float(total_receivables),
            "totalCount": total_count,
            "agingBreakdown": aging_breakdown,
            "topDebtors": top_debtors,
            "averageDaysOutstanding": 0,  # Would calculate based on invoice dates
        }

    async def get_payment_collection_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get payment collection metrics."""
        # Collection rate by period
        invoiced_query = select(func.sum(Invoice.total_amount).label("invoiced")).where(
            and_(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
        )

        invoiced_result = await self.db.execute(invoiced_query)
        total_invoiced = invoiced_result.scalar() or 0

        # Collected amount
        collected_query = select(func.sum(Payment.amount).label("collected")).where(
            and_(
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
                Payment.status == "completed",
            )
        )

        collected_result = await self.db.execute(collected_query)
        total_collected = collected_result.scalar() or 0

        collection_rate = round(
            (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0, 2
        )

        # Daily collection trend
        daily_collection_query = (
            select(
                func.date(Payment.payment_date).label("date"),
                func.sum(Payment.amount).label("amount"),
                func.count(Payment.id).label("count"),
            )
            .where(
                and_(
                    Payment.payment_date >= start_date,
                    Payment.payment_date <= end_date,
                    Payment.status == "completed",
                )
            )
            .group_by(func.date(Payment.payment_date))
            .order_by("date")
        )

        daily_result = await self.db.execute(daily_collection_query)
        daily_collections = [
            {
                "date": row.date.isoformat(),
                "amount": float(row.amount or 0),
                "count": row.count,
            }
            for row in daily_result
        ]

        # Payment methods
        method_query = (
            select(
                Payment.payment_method,
                func.sum(Payment.amount).label("amount"),
                func.count(Payment.id).label("count"),
            )
            .where(
                and_(
                    Payment.payment_date >= start_date,
                    Payment.payment_date <= end_date,
                    Payment.status == "completed",
                )
            )
            .group_by(Payment.payment_method)
        )

        method_result = await self.db.execute(method_query)
        payment_methods = [
            {
                "method": row.payment_method,
                "amount": float(row.amount or 0),
                "count": row.count,
                "percentage": round(
                    (row.amount / total_collected * 100) if total_collected > 0 else 0,
                    2,
                ),
            }
            for row in method_result
        ]

        return {
            "totalInvoiced": float(total_invoiced),
            "totalCollected": float(total_collected),
            "collectionRate": collection_rate,
            "dailyTrend": daily_collections,
            "paymentMethods": payment_methods,
            "outstanding": float(total_invoiced - total_collected),
        }

    async def get_outstanding_invoices(self) -> Dict[str, Any]:
        """Get outstanding invoices details."""
        # Outstanding invoices summary
        outstanding_query = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.customer_id,
                Customer.name,
                Customer.business_name,
                Invoice.total_amount,
                Invoice.paid_amount,
                Invoice.due_date,
                Invoice.invoice_date,
            )
            .select_from(Invoice)
            .join(Customer, Invoice.customer_id == Customer.id)
            .where(
                and_(
                    Invoice.status != "paid", Invoice.total_amount > Invoice.paid_amount
                )
            )
            .order_by(Invoice.due_date)
        )

        result = await self.db.execute(outstanding_query)

        outstanding_invoices = []
        total_outstanding = 0
        overdue_count = 0
        overdue_amount = 0
        today = datetime.now().date()

        for row in result:
            outstanding = row.total_amount - row.paid_amount
            total_outstanding += outstanding

            is_overdue = row.due_date < today
            if is_overdue:
                overdue_count += 1
                overdue_amount += outstanding

            days_overdue = (today - row.due_date).days if is_overdue else 0

            outstanding_invoices.append(
                {
                    "id": row.id,
                    "invoiceNumber": row.invoice_number,
                    "customer": row.business_name or row.name,
                    "amount": float(row.total_amount),
                    "paid": float(row.paid_amount),
                    "outstanding": float(outstanding),
                    "dueDate": row.due_date.isoformat(),
                    "invoiceDate": row.invoice_date.isoformat(),
                    "isOverdue": is_overdue,
                    "daysOverdue": days_overdue,
                }
            )

        return {
            "totalOutstanding": float(total_outstanding),
            "overdueCount": overdue_count,
            "overdueAmount": float(overdue_amount),
            "invoices": outstanding_invoices[:20],  # Limit to 20 for dashboard
            "summary": {
                "total": len(outstanding_invoices),
                "current": len(
                    [inv for inv in outstanding_invoices if not inv["isOverdue"]]
                ),
                "overdue": overdue_count,
            },
        }

    async def get_revenue_by_segment(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get revenue breakdown by customer segment."""
        # Revenue by customer type
        segment_query = (
            select(
                Customer.customer_type,
                func.count(func.distinct(Customer.id)).label("customer_count"),
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("order_count"),
            )
            .select_from(Order)
            .join(Customer, Order.customer_id == Customer.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by(Customer.customer_type)
        )

        segment_result = await self.db.execute(segment_query)

        segments = []
        total_revenue = 0

        for row in segment_result:
            revenue = row.revenue or 0
            total_revenue += revenue

            segments.append(
                {
                    "segment": row.customer_type or "其他",
                    "customerCount": row.customer_count,
                    "revenue": float(revenue),
                    "orderCount": row.order_count,
                    "averageOrderValue": (
                        float(revenue / row.order_count) if row.order_count > 0 else 0
                    ),
                }
            )

        # Add percentage to each segment
        for segment in segments:
            segment["percentage"] = round(
                (segment["revenue"] / total_revenue * 100) if total_revenue > 0 else 0,
                2,
            )

        # Sort by revenue
        segments.sort(key=lambda x: x["revenue"], reverse=True)

        # Top revenue areas
        area_query = (
            select(
                Customer.area,
                func.sum(Order.total_amount).label("revenue"),
                func.count(func.distinct(Customer.id)).label("customer_count"),
            )
            .select_from(Order)
            .join(Customer, Order.customer_id == Customer.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                    Customer.area.isnot(None),
                )
            )
            .group_by(Customer.area)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(10)
        )

        area_result = await self.db.execute(area_query)
        top_areas = [
            {
                "area": row.area,
                "revenue": float(row.revenue or 0),
                "customerCount": row.customer_count,
            }
            for row in area_result
        ]

        return {
            "segments": segments,
            "topAreas": top_areas,
            "totalRevenue": float(total_revenue),
        }

    async def get_profit_margin_analysis(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get profit margin analysis."""
        # Product - wise profit margins
        product_margin_query = (
            select(
                GasProduct.id,
                GasProduct.name,
                GasProduct.size,
                func.sum(OrderItem.quantity).label("quantity_sold"),
                func.sum(OrderItem.subtotal).label("revenue"),
                func.avg(OrderItem.unit_price).label("avg_price"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .join(GasProduct, OrderItem.product_id == GasProduct.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by(GasProduct.id, GasProduct.name, GasProduct.size)
        )

        product_result = await self.db.execute(product_margin_query)

        product_margins = []
        total_revenue = 0
        total_cost = 0

        for row in product_result:
            revenue = row.revenue or 0
            # Simplified cost calculation (70% of revenue as cost)
            # In production, this would come from actual cost data
            cost = revenue * 0.7
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else 0

            total_revenue += revenue
            total_cost += cost

            product_margins.append(
                {
                    "product": f"{row.name} ({row.size})",
                    "quantitySold": row.quantity_sold or 0,
                    "revenue": float(revenue),
                    "cost": float(cost),
                    "profit": float(profit),
                    "margin": round(margin, 2),
                    "avgPrice": float(row.avg_price or 0),
                }
            )

        total_profit = total_revenue - total_cost
        overall_margin = (
            (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        )

        # Monthly margin trend
        monthly_margin_query = (
            select(
                func.date_trunc("month", Order.created_at).label("month"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .where(
                and_(
                    Order.created_at >= start_date.replace(day=1) - timedelta(days=180),
                    Order.created_at <= end_date,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.DELIVERED]),
                )
            )
            .group_by("month")
            .order_by("month")
        )

        monthly_result = await self.db.execute(monthly_margin_query)

        monthly_margins = []
        for row in monthly_result:
            revenue = row.revenue or 0
            cost = revenue * 0.7  # Simplified
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else 0

            monthly_margins.append(
                {
                    "month": row.month.strftime("%Y-%m"),
                    "revenue": float(revenue),
                    "profit": float(profit),
                    "margin": round(margin, 2),
                }
            )

        return {
            "overallMargin": round(overall_margin, 2),
            "totalRevenue": float(total_revenue),
            "totalCost": float(total_cost),
            "totalProfit": float(total_profit),
            "productMargins": product_margins,
            "monthlyTrend": monthly_margins,
        }

    async def get_cash_position_trend(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get cash position trend analysis."""
        # Daily cash movements
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        cash_movements = []
        running_balance = 0  # Would start from actual opening balance

        for date in date_range:
            # Inflows (payments received)
            inflow_query = select(func.sum(Payment.amount)).where(
                and_(
                    func.date(Payment.payment_date) == date.date(),
                    Payment.status == "completed",
                )
            )
            inflow_result = await self.db.execute(inflow_query)
            daily_inflow = inflow_result.scalar() or 0

            # Outflows (simplified - would include expenses, purchases, etc.)
            daily_outflow = daily_inflow * 0.6  # Simplified calculation

            net_movement = daily_inflow - daily_outflow
            running_balance += net_movement

            cash_movements.append(
                {
                    "date": date.date().isoformat(),
                    "inflow": float(daily_inflow),
                    "outflow": float(daily_outflow),
                    "netMovement": float(net_movement),
                    "balance": float(running_balance),
                }
            )

        # Cash conversion cycle (simplified)
        # Days Sales Outstanding
        dso_query = (
            select(
                func.avg(
                    func.julianday(Payment.payment_date)
                    - func.julianday(Invoice.invoice_date)
                )
            )
            .select_from(Payment)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .where(
                and_(
                    Payment.payment_date >= start_date, Payment.payment_date <= end_date
                )
            )
        )

        dso_result = await self.db.execute(dso_query)
        days_sales_outstanding = dso_result.scalar() or 30

        return {
            "cashMovements": cash_movements,
            "currentBalance": float(running_balance),
            "averageDailyInflow": float(
                sum([m["inflow"] for m in cash_movements]) / len(cash_movements)
            ),
            "averageDailyOutflow": float(
                sum([m["outflow"] for m in cash_movements]) / len(cash_movements)
            ),
            "cashConversionCycle": {
                "daysSalesOutstanding": round(days_sales_outstanding, 1),
                "daysInventoryOutstanding": 7,  # Simplified
                "daysPayableOutstanding": 30,  # Simplified
            },
        }

    async def get_system_performance_metrics(
        self, start_time: datetime
    ) -> Dict[str, Any]:
        """Get system performance metrics."""
        # This would integrate with actual monitoring systems
        # For now, returning mock data

        time_buckets = []
        current = start_time

        while current <= datetime.now():
            time_buckets.append(
                {
                    "timestamp": current.isoformat(),
                    "responseTime": np.random.normal(150, 30),  # ms
                    "errorRate": max(0, np.random.normal(0.5, 0.2)),  # %
                    "throughput": np.random.normal(100, 20),  # requests / min
                    "cpuUsage": np.random.normal(40, 10),  # %
                    "memoryUsage": np.random.normal(60, 5),  # %
                }
            )
            current += timedelta(minutes=5)

        return {
            "timeSeries": time_buckets,
            "averages": {
                "responseTime": 150,
                "errorRate": 0.5,
                "throughput": 100,
                "cpuUsage": 40,
                "memoryUsage": 60,
            },
            "alerts": [],
        }

    async def get_api_usage_statistics(self, start_time: datetime) -> Dict[str, Any]:
        """Get API usage statistics."""
        # Mock data - would come from API monitoring
        endpoints = [
            {
                "endpoint": "/api / v1 / orders",
                "calls": 15234,
                "avgTime": 125,
                "errors": 23,
            },
            {
                "endpoint": "/api / v1 / customers",
                "calls": 8932,
                "avgTime": 98,
                "errors": 12,
            },
            {
                "endpoint": "/api / v1 / routes",
                "calls": 6543,
                "avgTime": 234,
                "errors": 8,
            },
            {
                "endpoint": "/api / v1 / deliveries",
                "calls": 12876,
                "avgTime": 156,
                "errors": 34,
            },
            {
                "endpoint": "/api / v1 / analytics",
                "calls": 2341,
                "avgTime": 456,
                "errors": 5,
            },
        ]

        total_calls = sum(e["calls"] for e in endpoints)
        total_errors = sum(e["errors"] for e in endpoints)

        return {
            "totalCalls": total_calls,
            "totalErrors": total_errors,
            "errorRate": (
                round(total_errors / total_calls * 100, 2) if total_calls > 0 else 0
            ),
            "endpoints": endpoints,
            "peakHours": [
                {"hour": 9, "calls": 2341},
                {"hour": 10, "calls": 3456},
                {"hour": 11, "calls": 3234},
                {"hour": 14, "calls": 3123},
                {"hour": 15, "calls": 2987},
            ],
        }

    async def get_error_rate_analysis(self, start_time: datetime) -> Dict[str, Any]:
        """Get error rate analysis."""
        # Mock data - would come from error monitoring
        error_types = [
            {"type": "ValidationError", "count": 234, "percentage": 45},
            {"type": "AuthenticationError", "count": 123, "percentage": 24},
            {"type": "DatabaseError", "count": 89, "percentage": 17},
            {"type": "NetworkError", "count": 45, "percentage": 9},
            {"type": "UnknownError", "count": 28, "percentage": 5},
        ]

        error_trends = []
        current = start_time

        while current <= datetime.now():
            error_trends.append(
                {
                    "timestamp": current.isoformat(),
                    "errorCount": int(np.random.poisson(5)),
                }
            )
            current += timedelta(hours=1)

        return {
            "errorTypes": error_types,
            "errorTrends": error_trends,
            "totalErrors": sum(e["count"] for e in error_types),
            "criticalErrors": 12,
            "resolvedErrors": 456,
        }

    async def get_user_activity_metrics(self, start_time: datetime) -> Dict[str, Any]:
        """Get user activity metrics."""
        # Active users by role
        active_users_query = (
            select(User.role, func.count(func.distinct(User.id)).label("count"))
            .where(and_(User.is_active, User.last_login >= start_time))
            .group_by(User.role)
        )

        active_result = await self.db.execute(active_users_query)
        active_by_role = {row.role: row.count for row in active_result}

        # User sessions (mock data)
        session_data = {
            "totalSessions": 1234,
            "averageSessionDuration": 1523,  # seconds
            "pageViews": 45678,
            "bounceRate": 12.5,
        }

        # Feature usage (mock data)
        feature_usage = [
            {"feature": "訂單管理", "usage": 3456, "users": 234},
            {"feature": "客戶管理", "usage": 2345, "users": 198},
            {"feature": "路線規劃", "usage": 1234, "users": 45},
            {"feature": "報表分析", "usage": 987, "users": 23},
            {"feature": "司機管理", "usage": 765, "users": 34},
        ]

        return {
            "activeUsersByRole": active_by_role,
            "totalActiveUsers": sum(active_by_role.values()),
            "sessionData": session_data,
            "featureUsage": feature_usage,
            "userGrowth": {"newUsers": 12, "returningUsers": 234, "churnedUsers": 5},
        }

    async def get_resource_utilization(self, start_time: datetime) -> Dict[str, Any]:
        """Get resource utilization metrics."""
        # Mock data - would come from infrastructure monitoring
        return {
            "database": {
                "connections": 45,
                "maxConnections": 100,
                "queryTime": 23.5,  # ms
                "slowQueries": 12,
                "diskUsage": 67.8,  # %
            },
            "redis": {
                "memoryUsage": 234.5,  # MB
                "hitRate": 89.5,  # %
                "evictions": 123,
                "connectedClients": 34,
            },
            "storage": {
                "used": 456.7,  # GB
                "total": 1000,  # GB
                "percentage": 45.7,
                "largestTables": [
                    {"table": "orders", "size": 123.4},
                    {"table": "delivery_history", "size": 89.2},
                    {"table": "invoices", "size": 67.8},
                ],
            },
            "api": {
                "requestsPerMinute": 234,
                "averageLatency": 156,  # ms
                "errorRate": 0.8,  # %
                "saturation": 45.6,  # %
            },
        }

    async def get_latest_order_updates(self) -> Dict[str, Any]:
        """Get latest order updates for real - time display."""
        # Recent order changes
        recent_orders_query = (
            select(Order)
            .options(selectinload(Order.customer))
            .order_by(Order.updated_at.desc())
            .limit(10)
        )

        result = await self.db.execute(recent_orders_query)
        recent_orders = result.scalars().all()

        updates = []
        for order in recent_orders:
            updates.append(
                {
                    "id": order.id,
                    "orderNumber": order.order_number,
                    "customer": order.customer.business_name or order.customer.name,
                    "status": order.status,
                    "amount": float(order.total_amount),
                    "updatedAt": order.updated_at.isoformat(),
                    "action": "status_change",  # Would determine actual action
                }
            )

        return {"updates": updates, "timestamp": datetime.now().isoformat()}

    async def get_custom_metrics(
        self,
        metrics: List[str],
        start_date: datetime,
        end_date: datetime,
        group_by: Optional[str],
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Get custom metrics based on user selection."""
        results = {}

        for metric in metrics:
            if metric == "revenue":
                results["revenue"] = await self.get_revenue_metrics(
                    start_date, end_date
                )
            elif metric == "orders":
                results["orders"] = await self.get_order_metrics(start_date, end_date)
            elif metric == "customers":
                results["customers"] = await self.get_customer_metrics(
                    start_date, end_date
                )
            # Add more metrics as needed

        return {
            "metrics": results,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "filters": filters,
            "groupBy": group_by,
        }

    async def generate_report(
        self,
        report_type: str,
        format: str,
        start_date: datetime,
        end_date: datetime,
        user_id: str,
    ) -> str:
        """Generate report and return URL."""
        # Fetch data based on report type
        data = {}

        if report_type == "executive":
            data = {
                "revenue": await self.get_revenue_metrics(start_date, end_date),
                "orders": await self.get_order_metrics(start_date, end_date),
                "customers": await self.get_customer_metrics(start_date, end_date),
                "performance": await self.get_performance_comparison(
                    start_date, end_date
                ),
            }
        elif report_type == "financial":
            data = {
                "receivables": await self.get_accounts_receivable_aging(),
                "collections": await self.get_payment_collection_metrics(
                    start_date, end_date
                ),
                "revenue": await self.get_revenue_by_segment(start_date, end_date),
                "margins": await self.get_profit_margin_analysis(start_date, end_date),
            }
        # Add more report types

        # Generate file based on format
        if format == "excel":
            file_path = await self._generate_excel_report(data, report_type)
        elif format == "pd":
            file_path = await self._generate_pdf_report(data, report_type)
        else:  # csv
            file_path = await self._generate_csv_report(data, report_type)

        # Upload to storage and return URL
        url = await self.storage_service.upload_file(file_path, f"reports/{user_id}/")

        return url

    async def generate_and_email_report(
        self,
        report_type: str,
        format: str,
        start_date: datetime,
        end_date: datetime,
        email: str,
        user_id: str,
    ):
        """Generate report and email to user."""
        # Generate report
        report_url = await self.generate_report(
            report_type, format, start_date, end_date, user_id
        )

        # Send email
        subject = f"LuckyGas {report_type.title()} Report - {start_date.date()} to {end_date.date()}"
        body = """
        您好，

        您要求的報表已經產生完成。

        報表類型: {report_type.title()}
        期間: {start_date.date()} 至 {end_date.date()}
        格式: {format.upper()}

        請點擊以下連結下載報表:
        {report_url}

        此連結將在 7 天後失效。

        謝謝，
        LuckyGas 系統
        """

        await self.email_service.send_email(email, subject, body)

    async def _generate_excel_report(
        self, data: Dict[str, Any], report_type: str
    ) -> str:
        """Generate Excel report."""
        # Implementation would use pandas / openpyxl to create Excel file
        # This is a placeholder
        return f"/tmp/{report_type}_report_{datetime.now().strftime('%Y % m % d_ % H % M % S')}.xlsx"

    async def _generate_pdf_report(self, data: Dict[str, Any], report_type: str) -> str:
        """Generate PDF report."""
        # Implementation would use reportlab or similar to create PDF
        # This is a placeholder
        return f"/tmp/{report_type}_report_{datetime.now().strftime('%Y % m % d_ % H % M % S')}.pd"

    async def _generate_csv_report(self, data: Dict[str, Any], report_type: str) -> str:
        """Generate CSV report."""
        # Implementation would use pandas to create CSV
        # This is a placeholder
        return f"/tmp/{report_type}_report_{datetime.now().strftime('%Y % m % d_ % H % M % S')}.csv"
