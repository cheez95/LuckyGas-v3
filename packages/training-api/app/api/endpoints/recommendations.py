from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.ai_recommendation_service import AIRecommendationService
from app.schemas.training import RecommendationResponse, LearningPathResponse

router = APIRouter()

@router.get("/courses", response_model=List[RecommendationResponse])
async def get_course_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of recommendations"),
    exclude_enrolled: bool = Query(True, description="Exclude already enrolled courses"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get personalized course recommendations for the current user."""
    recommendation_service = AIRecommendationService(db)
    
    recommendations = await recommendation_service.get_personalized_recommendations(
        user_id=str(current_user.id),
        limit=limit,
        exclude_enrolled=exclude_enrolled
    )
    
    return recommendations

@router.get("/next-module/{course_id}")
async def get_next_module_recommendation(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recommendation for the next module to study in a course."""
    recommendation_service = AIRecommendationService(db)
    
    recommendation = await recommendation_service.get_next_module_recommendation(
        user_id=str(current_user.id),
        course_id=course_id
    )
    
    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail="No module recommendation available. You may have completed all modules."
        )
    
    return recommendation

@router.get("/learning-path", response_model=List[LearningPathResponse])
async def get_learning_path(
    goal: str = Query(..., description="Learning goal (e.g., manager_training, safety_certification)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a personalized learning path towards a specific goal."""
    valid_goals = [
        "manager_training",
        "safety_certification",
        "customer_service_excellence",
        "technical_skills",
        "leadership_development",
        "compliance_training"
    ]
    
    if goal not in valid_goals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid goal. Must be one of: {', '.join(valid_goals)}"
        )
    
    recommendation_service = AIRecommendationService(db)
    
    learning_path = await recommendation_service.get_learning_path_recommendation(
        user_id=str(current_user.id),
        goal=goal
    )
    
    return learning_path

@router.post("/feedback/{course_id}")
async def submit_recommendation_feedback(
    course_id: str,
    helpful: bool,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback on a course recommendation."""
    # Store feedback for improving recommendations
    # This would typically update a feedback table
    
    return {
        "message": "Feedback received",
        "course_id": course_id,
        "helpful": helpful
    }

@router.get("/similar-learners")
async def get_similar_learners(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find learners with similar learning patterns (anonymized)."""
    recommendation_service = AIRecommendationService(db)
    
    # Get user profile
    user_profile = await recommendation_service._get_user_profile(str(current_user.id))
    if not user_profile:
        return []
    
    # Find similar users
    similar_users = await recommendation_service._find_similar_users(
        str(current_user.id),
        user_profile,
        limit=limit
    )
    
    # Return anonymized data
    return [
        {
            "similarity_score": score,
            "completed_courses": "Similar",
            "department": user_profile["department"],
            "learning_pace": "Similar"
        }
        for _, score in similar_users
    ]

@router.get("/trending-courses")
async def get_trending_courses(
    timeframe: str = Query("week", regex="^(week|month|all)$"),
    department: Optional[str] = None,
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trending courses based on enrollments and completions."""
    # This would analyze recent enrollment patterns
    # For now, return popular courses
    
    from app.models.training import Course, Enrollment
    from sqlalchemy import select, func, desc
    from datetime import datetime, timedelta
    
    # Calculate date filter
    if timeframe == "week":
        date_filter = datetime.utcnow() - timedelta(days=7)
    elif timeframe == "month":
        date_filter = datetime.utcnow() - timedelta(days=30)
    else:
        date_filter = None
    
    # Build query
    query = (
        select(
            Course,
            func.count(Enrollment.enrollment_id).label("enrollment_count")
        )
        .join(Enrollment)
        .where(Course.is_active == True)
        .group_by(Course.course_id)
    )
    
    if date_filter:
        query = query.where(Enrollment.enrolled_at >= date_filter)
    
    if department:
        query = query.where(
            or_(Course.department == department, Course.department == "all")
        )
    
    query = query.order_by(desc("enrollment_count")).limit(limit)
    
    result = await db.execute(query)
    trending = []
    
    for course, count in result:
        trending.append({
            "course_id": str(course.course_id),
            "title_zh": course.title_zh,
            "title_en": course.title_en,
            "department": course.department,
            "difficulty": course.difficulty,
            "enrollment_count": count,
            "trend": "rising"  # This would be calculated from historical data
        })
    
    return trending