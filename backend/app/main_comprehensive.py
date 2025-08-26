"""
Lucky Gas Backend - Using Comprehensive Database Models
簡單而完整的後端應用程式，使用新的綜合資料庫模型
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import comprehensive models
from app.models_comprehensive import (
    Customer, CustomerCylinder, CustomerTimeAvailability,
    CustomerEquipment, CustomerUsageArea, CustomerUsageMetrics,
    CylinderType, CustomerType, PricingMethod, PaymentMethod
)
from app.core.database import get_db, SessionLocal, engine
from app.api.v1 import customers_comprehensive

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 Starting Lucky Gas Backend with Clients Database")
    logger.info(f"📁 Database: luckygas_clients.db")
    
    # Test database connection
    try:
        db = SessionLocal()
        customer_count = db.query(Customer).count()
        logger.info(f"✅ Database connected: {customer_count} customers loaded")
        db.close()
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
    
    yield
    
    logger.info("👋 Shutting down Lucky Gas Backend")


# Create FastAPI app
app = FastAPI(
    title="Lucky Gas Management System",
    description="幸福氣體管理系統 - Comprehensive Database API",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customers_comprehensive.router)

# ============================
# API ENDPOINTS
# ============================

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Lucky Gas API with Comprehensive Database",
        "version": "2.0.0",
        "database": "SQLite with 1017 customers",
        "tables": [
            "customers", "customer_cylinders", "customer_time_availability",
            "customer_equipment", "customer_usage_areas", "customer_usage_metrics"
        ]
    }


@app.get("/api/v1/stats")
def get_database_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    try:
        stats = {
            "customers": db.query(Customer).count(),
            "active_customers": db.query(Customer).filter(Customer.is_active == True).count(),
            "cylinders": db.query(CustomerCylinder).count(),
            "time_availability": db.query(CustomerTimeAvailability).count(),
            "equipment": db.query(CustomerEquipment).count(),
            "usage_areas": db.query(CustomerUsageArea).count(),
            "usage_metrics": db.query(CustomerUsageMetrics).count()
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Customer endpoints
@app.get("/api/v1/customers")
def list_customers(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    area: Optional[str] = None,
    customer_type: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """List customers with filters"""
    try:
        query = db.query(Customer)
        
        # Apply filters
        if search:
            query = query.filter(
                (Customer.short_name.ilike(f"%{search}%")) |
                (Customer.customer_code.ilike(f"%{search}%")) |
                (Customer.address.ilike(f"%{search}%"))
            )
        
        if area:
            query = query.filter(Customer.area == area)
        
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type)
        
        if is_active is not None:
            query = query.filter(Customer.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        customers = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": [
                {
                    "id": c.id,
                    "customer_code": c.customer_code,
                    "invoice_title": c.invoice_title,
                    "short_name": c.short_name,
                    "address": c.address,
                    "area": c.area,
                    "customer_type": c.customer_type.value if c.customer_type else None,
                    "is_active": c.is_active,
                    "is_subscription": c.is_subscription,
                    "pricing_method": c.pricing_method.value if c.pricing_method else None,
                    "payment_method": c.payment_method.value if c.payment_method else None
                }
                for c in customers
            ]
        }
    except Exception as e:
        logger.error(f"Error listing customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get customer details with all related data"""
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get related data
        cylinders = db.query(CustomerCylinder).filter(
            CustomerCylinder.customer_id == customer_id
        ).all()
        
        time_availability = db.query(CustomerTimeAvailability).filter(
            CustomerTimeAvailability.customer_id == customer_id
        ).first()
        
        equipment = db.query(CustomerEquipment).filter(
            CustomerEquipment.customer_id == customer_id
        ).first()
        
        usage_areas = db.query(CustomerUsageArea).filter(
            CustomerUsageArea.customer_id == customer_id
        ).order_by(CustomerUsageArea.area_sequence).all()
        
        usage_metrics = db.query(CustomerUsageMetrics).filter(
            CustomerUsageMetrics.customer_id == customer_id
        ).first()
        
        return {
            "customer": {
                "id": customer.id,
                "customer_code": customer.customer_code,
                "invoice_title": customer.invoice_title,
                "short_name": customer.short_name,
                "address": customer.address,
                "phone": customer.phone,
                "area": customer.area,
                "customer_type": customer.customer_type.value if customer.customer_type else None,
                "is_active": customer.is_active,
                "is_subscription": customer.is_subscription,
                "auto_report": customer.auto_report,
                "scheduled_patrol": customer.scheduled_patrol,
                "pricing_method": customer.pricing_method.value if customer.pricing_method else None,
                "payment_method": customer.payment_method.value if customer.payment_method else None,
                "same_day_delivery": customer.same_day_delivery,
                "vehicle_requirement": customer.vehicle_requirement.value if customer.vehicle_requirement else None
            },
            "cylinders": [
                {
                    "type": c.cylinder_type.value,
                    "quantity": c.quantity,
                    "is_spare": c.is_spare
                }
                for c in cylinders
            ],
            "time_availability": {
                "time_preference": time_availability.time_preference.value if time_availability and time_availability.time_preference else None,
                "available_0800_0900": time_availability.available_0800_0900 if time_availability else False,
                "available_0900_1000": time_availability.available_0900_1000 if time_availability else False,
                "available_1000_1100": time_availability.available_1000_1100 if time_availability else False,
                "available_1100_1200": time_availability.available_1100_1200 if time_availability else False,
                "available_1200_1300": time_availability.available_1200_1300 if time_availability else False,
                "available_1300_1400": time_availability.available_1300_1400 if time_availability else False,
                "available_1400_1500": time_availability.available_1400_1500 if time_availability else False,
                "available_1500_1600": time_availability.available_1500_1600 if time_availability else False,
                "available_1600_1700": time_availability.available_1600_1700 if time_availability else False,
                "available_1700_1800": time_availability.available_1700_1800 if time_availability else False,
                "available_1800_1900": time_availability.available_1800_1900 if time_availability else False,
                "available_1900_2000": time_availability.available_1900_2000 if time_availability else False,
                "rest_day": time_availability.rest_day.value if time_availability and time_availability.rest_day else None
            } if time_availability else None,
            "equipment": {
                "switch_model": equipment.switch_model if equipment else None,
                "has_flow_meter": equipment.has_flow_meter if equipment else False,
                "has_wired_flow_meter": equipment.has_wired_flow_meter if equipment else False,
                "has_switch": equipment.has_switch if equipment else False,
                "has_smart_scale": equipment.has_smart_scale if equipment else False
            } if equipment else None,
            "usage_areas": [
                {
                    "sequence": area.area_sequence,
                    "description": area.area_description,
                    "cylinder_config": area.cylinder_config,
                    "is_connected": area.is_connected
                }
                for area in usage_areas
            ],
            "usage_metrics": {
                "monthly_delivery_volume": usage_metrics.monthly_delivery_volume if usage_metrics else None,
                "gas_return_volume": usage_metrics.gas_return_volume if usage_metrics else None,
                "actual_purchase_kg": usage_metrics.actual_purchase_kg if usage_metrics else None,
                "gas_return_ratio": usage_metrics.gas_return_ratio if usage_metrics else None,
                "avg_daily_usage": usage_metrics.avg_daily_usage if usage_metrics else None
            } if usage_metrics else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cylinders/summary")
def get_cylinder_summary(db: Session = Depends(get_db)):
    """Get summary of all cylinder types and quantities"""
    try:
        cylinders = db.query(CustomerCylinder).all()
        
        # Aggregate by type
        summary = {}
        for cylinder in cylinders:
            cylinder_type = cylinder.cylinder_type.value
            if cylinder_type not in summary:
                summary[cylinder_type] = {
                    "total_quantity": 0,
                    "customer_count": set(),
                    "spare_count": 0
                }
            summary[cylinder_type]["total_quantity"] += cylinder.quantity
            summary[cylinder_type]["customer_count"].add(cylinder.customer_id)
            if cylinder.is_spare:
                summary[cylinder_type]["spare_count"] += 1
        
        # Convert sets to counts
        for cylinder_type in summary:
            summary[cylinder_type]["customer_count"] = len(summary[cylinder_type]["customer_count"])
        
        return {
            "total_types": len(summary),
            "total_cylinders": sum(s["total_quantity"] for s in summary.values()),
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error getting cylinder summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/areas")
def get_areas(db: Session = Depends(get_db)):
    """Get list of all areas"""
    try:
        areas = db.query(Customer.area).distinct().all()
        area_list = [area[0] for area in areas if area[0]]
        
        # Get customer count per area
        area_stats = []
        for area in area_list:
            count = db.query(Customer).filter(Customer.area == area).count()
            area_stats.append({
                "area": area,
                "customer_count": count
            })
        
        return {
            "total": len(area_list),
            "areas": sorted(area_stats, key=lambda x: x["customer_count"], reverse=True)
        }
    except Exception as e:
        logger.error(f"Error getting areas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = SessionLocal()
        db.query(Customer).first()
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Lucky Gas Backend with Comprehensive Database...")
    uvicorn.run(
        "app.main_comprehensive:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )