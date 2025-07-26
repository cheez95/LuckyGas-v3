"""
Credit limit management and validation service
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class CreditService:
    """Service for managing customer credit limits and validation"""
    
    @staticmethod
    async def check_credit_limit(
        db: AsyncSession,
        customer_id: int,
        order_amount: float,
        skip_check: bool = False
    ) -> Dict[str, Any]:
        """
        Check if customer has sufficient credit for new order
        
        Args:
            db: Database session
            customer_id: Customer ID
            order_amount: Amount of new order
            skip_check: Skip credit check (for manager override)
            
        Returns:
            Dict with validation result and details
        """
        # Get customer
        customer = await db.get(Customer, customer_id)
        if not customer:
            return {
                "approved": False,
                "reason": "Customer not found",
                "details": {}
            }
        
        # If credit check is skipped (manager override)
        if skip_check:
            logger.info(f"Credit check skipped for customer {customer_id}")
            return {
                "approved": True,
                "reason": "Manager override",
                "details": {
                    "credit_limit": customer.credit_limit,
                    "current_balance": customer.current_balance,
                    "available_credit": customer.credit_limit - customer.current_balance
                }
            }
        
        # If customer is credit blocked
        if customer.is_credit_blocked:
            return {
                "approved": False,
                "reason": "Customer credit is blocked",
                "details": {
                    "credit_limit": customer.credit_limit,
                    "current_balance": customer.current_balance,
                    "is_blocked": True
                }
            }
        
        # Calculate outstanding balance from unpaid orders
        outstanding_balance = await CreditService._calculate_outstanding_balance(
            db, customer_id
        )
        
        # Update current balance in customer record
        customer.current_balance = outstanding_balance
        
        # Calculate available credit
        available_credit = customer.credit_limit - outstanding_balance
        
        # Check if new order would exceed credit limit
        if order_amount > available_credit:
            return {
                "approved": False,
                "reason": "Credit limit exceeded",
                "details": {
                    "credit_limit": customer.credit_limit,
                    "current_balance": outstanding_balance,
                    "available_credit": available_credit,
                    "requested_amount": order_amount,
                    "exceeds_by": order_amount - available_credit
                }
            }
        
        return {
            "approved": True,
            "reason": "Within credit limit",
            "details": {
                "credit_limit": customer.credit_limit,
                "current_balance": outstanding_balance,
                "available_credit": available_credit,
                "requested_amount": order_amount,
                "remaining_credit": available_credit - order_amount
            }
        }
    
    @staticmethod
    async def _calculate_outstanding_balance(
        db: AsyncSession,
        customer_id: int
    ) -> float:
        """Calculate total outstanding balance from unpaid orders"""
        # Query for unpaid orders
        stmt = select(
            func.sum(Order.total_amount)
        ).where(
            Order.customer_id == customer_id,
            Order.payment_status.in_(['pending', 'partial']),
            Order.status != OrderStatus.CANCELLED
        )
        
        result = await db.execute(stmt)
        outstanding = result.scalar() or 0.0
        
        return outstanding
    
    @staticmethod
    async def update_customer_balance(
        db: AsyncSession,
        customer_id: int
    ) -> float:
        """Update customer's current balance based on unpaid orders"""
        customer = await db.get(Customer, customer_id)
        if not customer:
            return 0.0
        
        outstanding_balance = await CreditService._calculate_outstanding_balance(
            db, customer_id
        )
        
        customer.current_balance = outstanding_balance
        await db.commit()
        
        return outstanding_balance
    
    @staticmethod
    async def get_credit_summary(
        db: AsyncSession,
        customer_id: int
    ) -> Dict[str, Any]:
        """Get customer credit summary"""
        customer = await db.get(Customer, customer_id)
        if not customer:
            return {}
        
        outstanding_balance = await CreditService._calculate_outstanding_balance(
            db, customer_id
        )
        
        # Get overdue amount (orders older than 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stmt = select(
            func.sum(Order.total_amount)
        ).where(
            Order.customer_id == customer_id,
            Order.payment_status.in_(['pending', 'partial']),
            Order.status != OrderStatus.CANCELLED,
            Order.created_at < thirty_days_ago
        )
        
        result = await db.execute(stmt)
        overdue_amount = result.scalar() or 0.0
        
        return {
            "customer_id": customer_id,
            "customer_name": customer.short_name,
            "credit_limit": customer.credit_limit,
            "current_balance": outstanding_balance,
            "available_credit": customer.credit_limit - outstanding_balance,
            "overdue_amount": overdue_amount,
            "is_credit_blocked": customer.is_credit_blocked,
            "credit_utilization": (outstanding_balance / customer.credit_limit * 100) if customer.credit_limit > 0 else 0
        }
    
    @staticmethod
    async def block_customer_credit(
        db: AsyncSession,
        customer_id: int,
        reason: str
    ) -> bool:
        """Block customer credit"""
        customer = await db.get(Customer, customer_id)
        if not customer:
            return False
        
        customer.is_credit_blocked = True
        await db.commit()
        
        logger.info(f"Credit blocked for customer {customer_id}: {reason}")
        return True
    
    @staticmethod
    async def unblock_customer_credit(
        db: AsyncSession,
        customer_id: int,
        reason: str
    ) -> bool:
        """Unblock customer credit"""
        customer = await db.get(Customer, customer_id)
        if not customer:
            return False
        
        customer.is_credit_blocked = False
        await db.commit()
        
        logger.info(f"Credit unblocked for customer {customer_id}: {reason}")
        return True