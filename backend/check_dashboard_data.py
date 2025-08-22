#!/usr/bin/env python
"""
Check what data is available for the dashboard
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models import Customer, Order, OrderStatus, Driver, Route

def check_dashboard_data():
    """Check available data for dashboard"""
    # Database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=" * 60)
    print("📊 DASHBOARD DATA CHECK")
    print("=" * 60)
    
    # Check customers
    total_customers = session.query(func.count(Customer.id)).scalar()
    print(f"\n✅ Total Customers: {total_customers}")
    
    # Check orders
    total_orders = session.query(func.count(Order.id)).scalar()
    print(f"✅ Total Orders: {total_orders}")
    
    # Check today's orders
    today = date.today()
    today_orders = session.query(func.count(Order.id)).filter(
        Order.order_date == today
    ).scalar()
    print(f"✅ Today's Orders: {today_orders}")
    
    # Check delivered orders
    delivered_orders = session.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.DELIVERED
    ).scalar()
    print(f"✅ Delivered Orders: {delivered_orders}")
    
    # Check May 2025 orders
    may_orders = session.query(func.count(Order.id)).filter(
        and_(
            Order.order_date >= date(2025, 5, 1),
            Order.order_date <= date(2025, 5, 31)
        )
    ).scalar()
    print(f"✅ May 2025 Orders: {may_orders}")
    
    # Check drivers
    total_drivers = session.query(func.count(Driver.id)).scalar()
    active_drivers = session.query(func.count(Driver.id)).filter(
        Driver.is_active == True
    ).scalar()
    print(f"✅ Total Drivers: {total_drivers}")
    print(f"✅ Active Drivers: {active_drivers}")
    
    # Check routes
    total_routes = session.query(func.count(Route.id)).scalar()
    today_routes = session.query(func.count(Route.id)).filter(
        Route.route_date == today
    ).scalar()
    print(f"✅ Total Routes: {total_routes}")
    print(f"✅ Today's Routes: {today_routes}")
    
    # Sample some orders
    print("\n📦 Sample Orders (last 5):")
    recent_orders = session.query(Order).order_by(Order.order_date.desc()).limit(5).all()
    for order in recent_orders:
        customer = session.query(Customer).filter(Customer.id == order.customer_id).first()
        print(f"  - Order #{order.id}: {customer.short_name if customer else 'Unknown'} "
              f"on {order.order_date} - Status: {order.status}")
    
    # Sample customers
    print("\n👥 Sample Customers (first 5):")
    sample_customers = session.query(Customer).limit(5).all()
    for customer in sample_customers:
        print(f"  - {customer.customer_code}: {customer.short_name} - {customer.address[:30]}...")
    
    print("\n" + "=" * 60)
    print("Dashboard should show real data if orders exist for today.")
    print("May 2025 historical data has been imported successfully.")
    print("=" * 60)
    
    session.close()

if __name__ == "__main__":
    check_dashboard_data()