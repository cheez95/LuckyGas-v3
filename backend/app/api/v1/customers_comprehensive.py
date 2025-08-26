"""
Comprehensive Customer API Endpoints
完整的客戶資料 API 端點
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models_comprehensive import (
    Customer, CustomerCylinder, CustomerTimeAvailability,
    CustomerEquipment, CustomerUsageArea, CustomerUsageMetrics,
    CylinderType, CustomerType, PricingMethod, PaymentMethod, 
    WeekDay, TimeSlot
)
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])

# Pydantic models for API responses
class CylinderInfo(BaseModel):
    cylinder_type: str
    quantity: int
    
class TimeAvailabilityInfo(BaseModel):
    weekday: str
    time_slot: str
    is_available: bool
    
class EquipmentInfo(BaseModel):
    has_switch_valve: bool
    has_gas_meter: bool
    has_monitoring_device: bool
    has_safety_equipment: bool
    equipment_notes: Optional[str]
    
class UsageAreaInfo(BaseModel):
    area_number: int
    description: Optional[str]
    usage_type: Optional[str]
    
class UsageMetricsInfo(BaseModel):
    monthly_consumption: Optional[float]
    average_cylinder_count: Optional[int]
    refill_frequency_days: Optional[int]
    consumption_pattern: Optional[str]
    
class CustomerSummary(BaseModel):
    """Customer summary for list view"""
    id: int
    customer_code: str
    short_name: str
    customer_type: str
    district: str
    area: str
    address: str
    is_active: bool
    cylinder_summary: str  # e.g., "20kg:5, 50kg:2"
    pricing_method: str
    payment_method: str
    
class CustomerDetail(BaseModel):
    """Complete customer details"""
    # Basic info
    id: int
    customer_code: str
    short_name: str
    full_name: Optional[str]
    customer_type: str
    district: str
    area: str
    address: str
    phone: Optional[str]
    contact_person: Optional[str]
    
    # Pricing and payment
    pricing_method: str
    payment_method: str
    requires_invoice_file: bool
    
    # Status
    is_active: bool
    is_vip: bool
    has_contract: bool
    termination_date: Optional[datetime]
    
    # Notes
    notes: Optional[str]
    registration_number: Optional[str]
    order_note: Optional[str]
    address_note: Optional[str]
    
    # Related data
    cylinders: List[CylinderInfo]
    time_availability: List[TimeAvailabilityInfo]
    equipment: Optional[EquipmentInfo]
    usage_areas: List[UsageAreaInfo]
    usage_metrics: Optional[UsageMetricsInfo]
    
class PaginatedCustomers(BaseModel):
    """Paginated customer list response"""
    items: List[CustomerSummary]
    total: int
    page: int
    pages: int
    limit: int

class AnalyticsSummary(BaseModel):
    """Analytics dashboard summary"""
    total_customers: int
    active_customers: int
    customers_by_area: Dict[str, int]
    customers_by_type: Dict[str, int]
    cylinder_distribution: Dict[str, int]
    payment_methods: Dict[str, int]
    pricing_methods: Dict[str, int]
    time_preference_heatmap: List[Dict[str, Any]]
    equipment_adoption: Dict[str, int]


@router.get("", response_model=PaginatedCustomers)
def get_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    area: Optional[str] = None,
    district: Optional[str] = None,
    customer_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get paginated customer list with filters
    獲取分頁的客戶列表（含篩選功能）
    """
    query = db.query(Customer)
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Customer.short_name.ilike(search_pattern),
                Customer.full_name.ilike(search_pattern),
                Customer.customer_code.ilike(search_pattern),
                Customer.address.ilike(search_pattern),
                Customer.phone.ilike(search_pattern)
            )
        )
    
    if area:
        query = query.filter(Customer.area == area)
        
    if district:
        query = query.filter(Customer.district == district)
        
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
        
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # Get customers with eager loading
    customers = query.options(
        joinedload(Customer.cylinders)
    ).offset(offset).limit(limit).all()
    
    # Convert to response format
    items = []
    for customer in customers:
        # Create cylinder summary
        cylinder_counts = {}
        for cylinder in customer.cylinders:
            cylinder_type = cylinder.cylinder_type.value if hasattr(cylinder.cylinder_type, 'value') else str(cylinder.cylinder_type)
            # Simplify cylinder type display
            if 'STANDARD_' in cylinder_type:
                display_type = cylinder_type.replace('STANDARD_', '').replace('KG', 'kg')
            elif 'FLOW_' in cylinder_type:
                display_type = 'Flow ' + cylinder_type.replace('FLOW_', '').replace('KG', 'kg')
            else:
                display_type = cylinder_type.replace('_', ' ').title()
            
            cylinder_counts[display_type] = cylinder.quantity
        
        cylinder_summary = ", ".join([f"{k}:{v}" for k, v in cylinder_counts.items()]) if cylinder_counts else "無"
        
        items.append(CustomerSummary(
            id=customer.id,
            customer_code=customer.customer_code,
            short_name=customer.short_name,
            customer_type=customer.customer_type.value if customer.customer_type else "UNKNOWN",
            district=customer.district or "",
            area=customer.area or "",
            address=customer.address or "",
            is_active=customer.is_active,
            cylinder_summary=cylinder_summary,
            pricing_method=customer.pricing_method.value if customer.pricing_method else "BY_CYLINDER",
            payment_method=customer.payment_method.value if customer.payment_method else "CASH"
        ))
    
    return PaginatedCustomers(
        items=items,
        total=total,
        page=page,
        pages=pages,
        limit=limit
    )


@router.get("/{customer_id}/full", response_model=CustomerDetail)
def get_customer_full_details(customer_id: int, db: Session = Depends(get_db)):
    """
    Get complete customer details including all related data
    獲取完整的客戶詳細資料（包含所有相關資料）
    """
    # Get customer with all related data
    customer = db.query(Customer).options(
        joinedload(Customer.cylinders),
        joinedload(Customer.time_availability),
        joinedload(Customer.equipment),
        joinedload(Customer.usage_areas),
        joinedload(Customer.usage_metrics)
    ).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Prepare cylinder info
    cylinders = []
    for c in customer.cylinders:
        cylinders.append(CylinderInfo(
            cylinder_type=c.cylinder_type.value if hasattr(c.cylinder_type, 'value') else str(c.cylinder_type),
            quantity=c.quantity
        ))
    
    # Prepare time availability
    time_slots = []
    for t in customer.time_availability:
        time_slots.append(TimeAvailabilityInfo(
            weekday=t.weekday.value if hasattr(t.weekday, 'value') else str(t.weekday),
            time_slot=t.time_slot.value if hasattr(t.time_slot, 'value') else str(t.time_slot),
            is_available=t.is_available
        ))
    
    # Prepare equipment info
    equipment = None
    if customer.equipment:
        e = customer.equipment[0] if customer.equipment else None
        if e:
            equipment = EquipmentInfo(
                has_switch_valve=e.has_switch_valve,
                has_gas_meter=e.has_gas_meter,
                has_monitoring_device=e.has_monitoring_device,
                has_safety_equipment=e.has_safety_equipment,
                equipment_notes=e.equipment_notes
            )
    
    # Prepare usage areas
    usage_areas = []
    for u in customer.usage_areas:
        usage_areas.append(UsageAreaInfo(
            area_number=u.area_number,
            description=u.description,
            usage_type=u.usage_type
        ))
    
    # Prepare usage metrics
    usage_metrics = None
    if customer.usage_metrics:
        m = customer.usage_metrics[0] if customer.usage_metrics else None
        if m:
            usage_metrics = UsageMetricsInfo(
                monthly_consumption=m.monthly_consumption,
                average_cylinder_count=m.average_cylinder_count,
                refill_frequency_days=m.refill_frequency_days,
                consumption_pattern=m.consumption_pattern
            )
    
    return CustomerDetail(
        id=customer.id,
        customer_code=customer.customer_code,
        short_name=customer.short_name,
        full_name=customer.full_name,
        customer_type=customer.customer_type.value if customer.customer_type else "UNKNOWN",
        district=customer.district or "",
        area=customer.area or "",
        address=customer.address or "",
        phone=customer.phone,
        contact_person=customer.contact_person,
        pricing_method=customer.pricing_method.value if customer.pricing_method else "BY_CYLINDER",
        payment_method=customer.payment_method.value if customer.payment_method else "CASH",
        requires_invoice_file=customer.requires_invoice_file,
        is_active=customer.is_active,
        is_vip=customer.is_vip,
        has_contract=customer.has_contract,
        termination_date=customer.termination_date,
        notes=customer.notes,
        registration_number=customer.registration_number,
        order_note=customer.order_note,
        address_note=customer.address_note,
        cylinders=cylinders,
        time_availability=time_slots,
        equipment=equipment,
        usage_areas=usage_areas,
        usage_metrics=usage_metrics
    )


@router.get("/analytics/summary", response_model=AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    Get analytics dashboard summary data
    獲取分析儀表板摘要資料
    """
    # Basic counts
    total_customers = db.query(Customer).count()
    active_customers = db.query(Customer).filter(Customer.is_active == True).count()
    
    # Customers by area
    area_counts = db.query(
        Customer.area,
        func.count(Customer.id)
    ).group_by(Customer.area).all()
    customers_by_area = {area: count for area, count in area_counts if area}
    
    # Customers by type
    type_counts = db.query(
        Customer.customer_type,
        func.count(Customer.id)
    ).group_by(Customer.customer_type).all()
    customers_by_type = {
        (t.value if hasattr(t, 'value') else str(t)): count 
        for t, count in type_counts if t
    }
    
    # Cylinder distribution
    cylinder_counts = db.query(
        CustomerCylinder.cylinder_type,
        func.sum(CustomerCylinder.quantity)
    ).group_by(CustomerCylinder.cylinder_type).all()
    cylinder_distribution = {
        (c.value if hasattr(c, 'value') else str(c)): int(count) 
        for c, count in cylinder_counts if c
    }
    
    # Payment methods
    payment_counts = db.query(
        Customer.payment_method,
        func.count(Customer.id)
    ).group_by(Customer.payment_method).all()
    payment_methods = {
        (p.value if hasattr(p, 'value') else str(p)): count 
        for p, count in payment_counts if p
    }
    
    # Pricing methods
    pricing_counts = db.query(
        Customer.pricing_method,
        func.count(Customer.id)
    ).group_by(Customer.pricing_method).all()
    pricing_methods = {
        (p.value if hasattr(p, 'value') else str(p)): count 
        for p, count in pricing_counts if p
    }
    
    # Time preference heatmap
    time_availability = db.query(
        CustomerTimeAvailability.weekday,
        CustomerTimeAvailability.time_slot,
        func.sum(func.cast(CustomerTimeAvailability.is_available, type_=func.Integer))
    ).group_by(
        CustomerTimeAvailability.weekday,
        CustomerTimeAvailability.time_slot
    ).all()
    
    time_preference_heatmap = []
    for weekday, time_slot, count in time_availability:
        time_preference_heatmap.append({
            "weekday": weekday.value if hasattr(weekday, 'value') else str(weekday),
            "time_slot": time_slot.value if hasattr(time_slot, 'value') else str(time_slot),
            "count": int(count) if count else 0
        })
    
    # Equipment adoption
    equipment_stats = db.query(
        func.sum(func.cast(CustomerEquipment.has_switch_valve, type_=func.Integer)).label('switch_valve'),
        func.sum(func.cast(CustomerEquipment.has_gas_meter, type_=func.Integer)).label('gas_meter'),
        func.sum(func.cast(CustomerEquipment.has_monitoring_device, type_=func.Integer)).label('monitoring'),
        func.sum(func.cast(CustomerEquipment.has_safety_equipment, type_=func.Integer)).label('safety')
    ).first()
    
    equipment_adoption = {
        "switch_valve": int(equipment_stats.switch_valve) if equipment_stats.switch_valve else 0,
        "gas_meter": int(equipment_stats.gas_meter) if equipment_stats.gas_meter else 0,
        "monitoring_device": int(equipment_stats.monitoring) if equipment_stats.monitoring else 0,
        "safety_equipment": int(equipment_stats.safety) if equipment_stats.safety else 0
    }
    
    return AnalyticsSummary(
        total_customers=total_customers,
        active_customers=active_customers,
        customers_by_area=customers_by_area,
        customers_by_type=customers_by_type,
        cylinder_distribution=cylinder_distribution,
        payment_methods=payment_methods,
        pricing_methods=pricing_methods,
        time_preference_heatmap=time_preference_heatmap,
        equipment_adoption=equipment_adoption
    )


# Individual resource endpoints for specific needs

@router.get("/{customer_id}/cylinders")
def get_customer_cylinders(customer_id: int, db: Session = Depends(get_db)):
    """Get cylinders for a specific customer"""
    cylinders = db.query(CustomerCylinder).filter(
        CustomerCylinder.customer_id == customer_id
    ).all()
    
    return [{
        "cylinder_type": c.cylinder_type.value if hasattr(c.cylinder_type, 'value') else str(c.cylinder_type),
        "quantity": c.quantity
    } for c in cylinders]


@router.get("/{customer_id}/equipment")
def get_customer_equipment(customer_id: int, db: Session = Depends(get_db)):
    """Get equipment info for a specific customer"""
    equipment = db.query(CustomerEquipment).filter(
        CustomerEquipment.customer_id == customer_id
    ).first()
    
    if not equipment:
        return None
        
    return {
        "has_switch_valve": equipment.has_switch_valve,
        "has_gas_meter": equipment.has_gas_meter,
        "has_monitoring_device": equipment.has_monitoring_device,
        "has_safety_equipment": equipment.has_safety_equipment,
        "equipment_notes": equipment.equipment_notes
    }


@router.get("/{customer_id}/time-slots")
def get_customer_time_slots(customer_id: int, db: Session = Depends(get_db)):
    """Get time availability for a specific customer"""
    time_slots = db.query(CustomerTimeAvailability).filter(
        CustomerTimeAvailability.customer_id == customer_id
    ).all()
    
    return [{
        "weekday": t.weekday.value if hasattr(t.weekday, 'value') else str(t.weekday),
        "time_slot": t.time_slot.value if hasattr(t.time_slot, 'value') else str(t.time_slot),
        "is_available": t.is_available
    } for t in time_slots]


@router.get("/{customer_id}/usage-metrics")
def get_customer_usage_metrics(customer_id: int, db: Session = Depends(get_db)):
    """Get usage metrics for a specific customer"""
    metrics = db.query(CustomerUsageMetrics).filter(
        CustomerUsageMetrics.customer_id == customer_id
    ).first()
    
    if not metrics:
        return None
        
    return {
        "monthly_consumption": metrics.monthly_consumption,
        "average_cylinder_count": metrics.average_cylinder_count,
        "refill_frequency_days": metrics.refill_frequency_days,
        "consumption_pattern": metrics.consumption_pattern
    }


# Area and district listing endpoints
@router.get("/areas/list")
def get_areas_list(db: Session = Depends(get_db)):
    """Get list of all unique areas"""
    areas = db.query(Customer.area).distinct().filter(
        Customer.area != None
    ).order_by(Customer.area).all()
    
    return [area[0] for area in areas if area[0]]


@router.get("/districts/list")
def get_districts_list(db: Session = Depends(get_db)):
    """Get list of all unique districts"""
    districts = db.query(Customer.district).distinct().filter(
        Customer.district != None
    ).order_by(Customer.district).all()
    
    return [district[0] for district in districts if district[0]]