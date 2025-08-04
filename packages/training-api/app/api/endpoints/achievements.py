from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.training import Achievement, UserAchievement
from app.models.user import User
from app.schemas.training import AchievementResponse, UserAchievementResponse, LeaderboardEntry
from app.api.deps import get_current_user
from app.core.cache import cache

router = APIRouter()

@router.get("/", response_model=List[AchievementResponse])
async def get_all_achievements(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available achievements."""
    query = select(Achievement).where(Achievement.is_active == True)
    
    if category:
        query = query.where(Achievement.category == category)
    
    query = query.order_by(Achievement.points_value)
    result = await db.execute(query)
    achievements = result.scalars().all()
    
    # Get user's achieved achievements
    user_achievement_query = select(UserAchievement).where(
        UserAchievement.user_id == current_user.id
    )
    user_achievement_result = await db.execute(user_achievement_query)
    user_achievements = {ua.achievement_id: ua for ua in user_achievement_result.scalars().all()}
    
    response = []
    for achievement in achievements:
        achievement_dict = achievement.__dict__.copy()
        user_achievement = user_achievements.get(achievement.achievement_id)
        achievement_dict['earned'] = user_achievement is not None
        achievement_dict['earned_at'] = user_achievement.earned_at if user_achievement else None
        response.append(AchievementResponse(**achievement_dict))
    
    return response

@router.get("/my-achievements", response_model=List[UserAchievementResponse])
async def get_my_achievements(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's earned achievements."""
    query = (
        select(UserAchievement, Achievement)
        .join(Achievement)
        .where(UserAchievement.user_id == current_user.id)
        .order_by(desc(UserAchievement.earned_at))
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    user_achievements = []
    
    for ua, achievement in result:
        ua_dict = ua.__dict__.copy()
        ua_dict['achievement'] = AchievementResponse.from_orm(achievement)
        user_achievements.append(UserAchievementResponse(**ua_dict))
    
    return user_achievements

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
@cache(expire=300)
async def get_leaderboard(
    timeframe: str = Query("all", regex="^(all|month|week)$"),
    department: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get leaderboard rankings."""
    # Build base query
    query = select(
        User.id,
        User.name,
        User.department,
        User.points,
        User.avatar_url
    ).where(User.is_active == True)
    
    # Filter by department if specified
    if department:
        query = query.where(User.department == department)
    
    # Filter by timeframe
    if timeframe != "all":
        if timeframe == "month":
            start_date = datetime.utcnow() - timedelta(days=30)
        else:  # week
            start_date = datetime.utcnow() - timedelta(days=7)
        
        # For timeframe filtering, we need to calculate points from user_achievements
        # This is a simplified version - in production, you might want a separate points_history table
        subquery = (
            select(
                UserAchievement.user_id,
                func.sum(Achievement.points_value).label("recent_points")
            )
            .join(Achievement)
            .where(UserAchievement.earned_at >= start_date)
            .group_by(UserAchievement.user_id)
            .subquery()
        )
        
        query = (
            select(
                User.id,
                User.name,
                User.department,
                subquery.c.recent_points.label("points"),
                User.avatar_url
            )
            .join(subquery, User.id == subquery.c.user_id)
            .where(User.is_active == True)
        )
    
    # Order by points and limit
    query = query.order_by(desc("points")).limit(limit)
    
    result = await db.execute(query)
    leaderboard = []
    
    for idx, row in enumerate(result):
        entry = LeaderboardEntry(
            rank=idx + 1,
            user_id=row.id,
            name=row.name,
            department=row.department,
            points=row.points or 0,
            avatar_url=row.avatar_url,
            is_current_user=row.id == current_user.id
        )
        leaderboard.append(entry)
    
    # If current user is not in top N, add their rank
    if not any(entry.is_current_user for entry in leaderboard):
        # Get current user's rank
        if timeframe == "all":
            rank_query = select(func.count(User.id)).where(
                User.points > current_user.points,
                User.is_active == True
            )
            if department:
                rank_query = rank_query.where(User.department == department)
            
            rank_result = await db.execute(rank_query)
            user_rank = rank_result.scalar() + 1
            
            current_user_entry = LeaderboardEntry(
                rank=user_rank,
                user_id=current_user.id,
                name=current_user.name,
                department=current_user.department,
                points=current_user.points or 0,
                avatar_url=current_user.avatar_url,
                is_current_user=True
            )
            leaderboard.append(current_user_entry)
    
    return leaderboard

@router.get("/stats", response_model=dict)
async def get_achievement_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get achievement statistics for current user."""
    # Total achievements
    total_query = select(func.count(Achievement.achievement_id)).where(
        Achievement.is_active == True
    )
    total_result = await db.execute(total_query)
    total_achievements = total_result.scalar()
    
    # User's achievements
    user_query = select(func.count(UserAchievement.id)).where(
        UserAchievement.user_id == current_user.id
    )
    user_result = await db.execute(user_query)
    user_achievements = user_result.scalar()
    
    # Recent achievements (last 30 days)
    recent_query = select(func.count(UserAchievement.id)).where(
        UserAchievement.user_id == current_user.id,
        UserAchievement.earned_at >= datetime.utcnow() - timedelta(days=30)
    )
    recent_result = await db.execute(recent_query)
    recent_achievements = recent_result.scalar()
    
    # Achievement breakdown by category
    category_query = (
        select(
            Achievement.category,
            func.count(UserAchievement.id).label("earned"),
            func.count(Achievement.achievement_id).label("total")
        )
        .outerjoin(
            UserAchievement,
            (Achievement.achievement_id == UserAchievement.achievement_id) &
            (UserAchievement.user_id == current_user.id)
        )
        .where(Achievement.is_active == True)
        .group_by(Achievement.category)
    )
    category_result = await db.execute(category_query)
    categories = {}
    for row in category_result:
        categories[row.category] = {
            "earned": row.earned or 0,
            "total": row.total,
            "percentage": (row.earned / row.total * 100) if row.total > 0 else 0
        }
    
    # Next achievable achievements
    next_achievements_query = (
        select(Achievement)
        .outerjoin(
            UserAchievement,
            (Achievement.achievement_id == UserAchievement.achievement_id) &
            (UserAchievement.user_id == current_user.id)
        )
        .where(
            Achievement.is_active == True,
            UserAchievement.id.is_(None)
        )
        .order_by(Achievement.points_value)
        .limit(3)
    )
    next_achievements_result = await db.execute(next_achievements_query)
    next_achievements = [
        AchievementResponse.from_orm(a) for a in next_achievements_result.scalars().all()
    ]
    
    return {
        "total_achievements": total_achievements,
        "earned_achievements": user_achievements,
        "completion_percentage": (user_achievements / total_achievements * 100) if total_achievements > 0 else 0,
        "recent_achievements": recent_achievements,
        "total_points": current_user.points or 0,
        "current_rank": await get_user_rank(db, current_user),
        "categories": categories,
        "next_achievements": next_achievements
    }

async def get_user_rank(db: AsyncSession, user: User) -> int:
    """Get user's overall rank."""
    rank_query = select(func.count(User.id)).where(
        User.points > (user.points or 0),
        User.is_active == True
    )
    rank_result = await db.execute(rank_query)
    return rank_result.scalar() + 1