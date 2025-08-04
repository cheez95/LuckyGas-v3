from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime, date
import io

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, require_role
from app.services.analytics_service import AnalyticsService
from app.core.cache import cache

router = APIRouter()

@router.get("/dashboard")
@cache(expire=300)
async def get_dashboard_metrics(
    department: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get dashboard metrics for training system."""
    # Check permissions
    if not current_user.is_admin and department != current_user.department:
        department = current_user.department
    
    analytics_service = AnalyticsService(db)
    metrics = await analytics_service.get_dashboard_metrics(department)
    
    return metrics

@router.get("/courses/{course_id}")
@require_role(["admin", "training_manager", "manager"])
async def get_course_analytics(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed analytics for a specific course."""
    analytics_service = AnalyticsService(db)
    analytics = await analytics_service.get_course_analytics(course_id)
    
    if not analytics:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return analytics

@router.get("/users/{user_id}")
async def get_user_analytics(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed analytics for a specific user."""
    # Users can view their own analytics, managers can view their department
    if not current_user.is_admin:
        if str(current_user.id) != user_id:
            if current_user.role not in ["manager", "training_manager"]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Check if user is in same department
            # TODO: Add department check
    
    analytics_service = AnalyticsService(db)
    analytics = await analytics_service.get_user_analytics(user_id)
    
    if not analytics:
        raise HTTPException(status_code=404, detail="User not found")
    
    return analytics

@router.get("/departments/{department}")
@require_role(["admin", "training_manager", "manager"])
async def get_department_analytics(
    department: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get analytics for a specific department."""
    # Managers can only view their own department
    if not current_user.is_admin and current_user.role == "manager":
        if department != current_user.department:
            raise HTTPException(status_code=403, detail="Access denied")
    
    analytics_service = AnalyticsService(db)
    analytics = await analytics_service.get_department_analytics(department)
    
    return analytics

@router.get("/trends")
@cache(expire=600)
async def get_learning_trends(
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    department: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get learning trends over time."""
    # Apply department filter for non-admins
    if not current_user.is_admin and department != current_user.department:
        department = current_user.department
    
    analytics_service = AnalyticsService(db)
    trends = await analytics_service.get_learning_trends(days)
    
    return trends

@router.get("/reports/{report_type}")
@require_role(["admin", "training_manager", "manager"])
async def generate_report(
    report_type: str,
    department: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate downloadable reports."""
    # Validate report type
    valid_reports = ["user_progress", "course_completion", "department_summary"]
    if report_type not in valid_reports:
        raise HTTPException(status_code=400, detail=f"Invalid report type. Must be one of: {valid_reports}")
    
    # Apply permissions
    filters = {}
    if not current_user.is_admin:
        if current_user.role == "manager":
            filters["department"] = current_user.department
        elif department and department != current_user.department:
            raise HTTPException(status_code=403, detail="Access denied")
    
    if department:
        filters["department"] = department
    if start_date:
        filters["start_date"] = datetime.combine(start_date, datetime.min.time())
    if end_date:
        filters["end_date"] = datetime.combine(end_date, datetime.max.time())
    
    analytics_service = AnalyticsService(db)
    
    try:
        report_data = await analytics_service.generate_report(report_type, filters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
    
    # Return as downloadable Excel file
    filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        io.BytesIO(report_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@router.get("/realtime/active-users")
async def get_active_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get currently active users (real-time)."""
    # This would connect to WebSocket manager to get online users
    from app.core.websocket import manager
    
    online_users = manager.get_online_users()
    online_count = manager.get_online_count()
    
    # Get user details for online users
    analytics_service = AnalyticsService(db)
    user_details = []
    
    for user_id in online_users[:20]:  # Limit to 20 for performance
        user_data = await analytics_service.get_user_analytics(user_id)
        if user_data:
            user_details.append({
                "user_id": user_id,
                "name": user_data["name"],
                "department": user_data["department"],
                "current_activity": "online"  # This could be enhanced with actual activity
            })
    
    return {
        "online_count": online_count,
        "active_users": user_details,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/insights/recommendations")
@require_role(["admin", "training_manager"])
async def get_training_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get AI-powered training recommendations and insights."""
    analytics_service = AnalyticsService(db)
    
    # Get overall metrics
    metrics = await analytics_service.get_dashboard_metrics()
    
    recommendations = []
    
    # Low engagement recommendation
    if metrics["engagement_rate"] < 50:
        recommendations.append({
            "type": "engagement",
            "priority": "high",
            "title": "低參與率警告",
            "description": f"目前參與率僅 {metrics['engagement_rate']:.1f}%，建議推出激勵活動",
            "actions": [
                "發送培訓提醒郵件",
                "舉辦學習競賽",
                "提供完成獎勵"
            ]
        })
    
    # Course completion recommendation
    if metrics["average_completion_rate"] < 70:
        recommendations.append({
            "type": "completion",
            "priority": "medium",
            "title": "課程完成率偏低",
            "description": f"平均完成率為 {metrics['average_completion_rate']:.1f}%",
            "actions": [
                "簡化課程內容",
                "增加互動元素",
                "提供更多支援"
            ]
        })
    
    # Learning trends
    trends = await analytics_service.get_learning_trends(7)
    
    # Check for declining activity
    if len(trends["active_users_by_date"]) >= 7:
        dates = sorted(trends["active_users_by_date"].keys())
        recent_avg = sum(trends["active_users_by_date"][d] for d in dates[-3:]) / 3
        previous_avg = sum(trends["active_users_by_date"][d] for d in dates[:3]) / 3
        
        if recent_avg < previous_avg * 0.8:
            recommendations.append({
                "type": "activity",
                "priority": "high",
                "title": "活動量下降",
                "description": "最近三天的活躍用戶數下降超過 20%",
                "actions": [
                    "檢查是否有技術問題",
                    "發送重新參與通知",
                    "推出新課程內容"
                ]
            })
    
    return {
        "recommendations": recommendations,
        "insights": {
            "top_performing_departments": [],  # TODO: Implement
            "struggling_learners": [],  # TODO: Implement
            "popular_topics": trends.get("popular_courses", [])[:5]
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/events/track")
async def track_analytics_event(
    event_type: str,
    event_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Track custom analytics events."""
    # This would typically send to an analytics service like Mixpanel or Google Analytics
    # For now, we'll just log it
    
    valid_events = [
        "video_play", "video_pause", "video_complete",
        "quiz_start", "quiz_submit", "quiz_retry",
        "download_resource", "share_achievement",
        "help_requested", "feedback_submitted"
    ]
    
    if event_type not in valid_events:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {valid_events}")
    
    # Add user context
    event_data["user_id"] = str(current_user.id)
    event_data["timestamp"] = datetime.utcnow().isoformat()
    event_data["department"] = current_user.department
    
    # TODO: Send to analytics service
    print(f"Analytics event: {event_type}", event_data)
    
    return {"status": "tracked"}