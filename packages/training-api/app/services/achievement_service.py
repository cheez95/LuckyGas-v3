from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from app.models.training import Achievement, UserAchievement, Course, Module, Enrollment, Progress
from app.models.user import User
from app.core.notifications import send_achievement_notification

class AchievementService:
    """Service for managing achievements and gamification."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_enrollment_achievements(self, user_id: UUID):
        """Check for enrollment-based achievements."""
        # First Enrollment
        await self._check_achievement(user_id, "first_enrollment", {
            "type": "enrollment_count",
            "value": 1
        })
        
        # Learning Enthusiast (5 courses)
        await self._check_achievement(user_id, "learning_enthusiast", {
            "type": "enrollment_count",
            "value": 5
        })
        
        # Knowledge Seeker (10 courses)
        await self._check_achievement(user_id, "knowledge_seeker", {
            "type": "enrollment_count",
            "value": 10
        })
    
    async def check_module_achievements(self, user_id: UUID, module_id: UUID):
        """Check for module completion achievements."""
        # Get module info
        module_query = select(Module).where(Module.module_id == module_id)
        module_result = await self.db.execute(module_query)
        module = module_result.scalar_one_or_none()
        
        if not module:
            return
        
        # Quick Learner (complete module in < 30 minutes)
        progress_query = select(Progress).where(
            Progress.user_id == user_id,
            Progress.module_id == module_id
        )
        progress_result = await self.db.execute(progress_query)
        progress = progress_result.scalar_one_or_none()
        
        if progress and progress.time_spent_minutes < 30:
            await self._check_achievement(user_id, "quick_learner", {
                "type": "speed_completion",
                "module_id": module_id
            })
        
        # Perfect Score (100% on quiz)
        if progress and progress.quiz_score == 100:
            await self._check_achievement(user_id, "perfect_score", {
                "type": "quiz_perfection",
                "module_id": module_id
            })
        
        # Check total modules completed
        total_modules_query = select(func.count(Progress.progress_id)).where(
            Progress.user_id == user_id,
            Progress.completed_at.isnot(None)
        )
        total_modules_result = await self.db.execute(total_modules_query)
        total_modules = total_modules_result.scalar()
        
        # Module milestones
        milestones = {
            10: "module_master_10",
            25: "module_master_25",
            50: "module_master_50",
            100: "module_master_100"
        }
        
        for count, achievement_key in milestones.items():
            if total_modules >= count:
                await self._check_achievement(user_id, achievement_key, {
                    "type": "module_count",
                    "value": count
                })
    
    async def check_course_achievements(self, user_id: UUID, course_id: UUID):
        """Check for course completion achievements."""
        # Get course info
        course_query = select(Course).where(Course.course_id == course_id)
        course_result = await self.db.execute(course_query)
        course = course_result.scalar_one_or_none()
        
        if not course:
            return
        
        # First Course Completion
        await self._check_achievement(user_id, "first_course_complete", {
            "type": "course_completion",
            "course_id": course_id
        })
        
        # Department Specialist
        department_courses_query = select(func.count(Enrollment.enrollment_id)).where(
            Enrollment.user_id == user_id,
            Enrollment.status == "completed"
        ).join(Course).where(Course.department == course.department)
        department_courses_result = await self.db.execute(department_courses_query)
        department_courses = department_courses_result.scalar()
        
        if department_courses >= 5:
            await self._check_achievement(user_id, f"{course.department}_specialist", {
                "type": "department_mastery",
                "department": course.department,
                "count": department_courses
            })
        
        # Difficulty achievements
        if course.difficulty == "advanced":
            await self._check_achievement(user_id, "advanced_learner", {
                "type": "difficulty_completion",
                "difficulty": "advanced",
                "course_id": course_id
            })
        
        # Check total courses completed
        total_courses_query = select(func.count(Enrollment.enrollment_id)).where(
            Enrollment.user_id == user_id,
            Enrollment.status == "completed"
        )
        total_courses_result = await self.db.execute(total_courses_query)
        total_courses = total_courses_result.scalar()
        
        # Course milestones
        milestones = {
            5: "course_champion_5",
            10: "course_champion_10",
            25: "course_champion_25"
        }
        
        for count, achievement_key in milestones.items():
            if total_courses >= count:
                await self._check_achievement(user_id, achievement_key, {
                    "type": "course_count",
                    "value": count
                })
    
    async def check_streak_achievements(self, user_id: UUID):
        """Check for learning streak achievements."""
        # This would typically check daily login/activity streaks
        # For now, we'll check consecutive days with progress
        
        # Weekly Warrior (7 day streak)
        # Monthly Master (30 day streak)
        # Implementation would require tracking daily activity
        pass
    
    async def check_social_achievements(self, user_id: UUID):
        """Check for social/collaborative achievements."""
        # Team Player (complete team training)
        # Helpful Hero (help others in forums)
        # Knowledge Sharer (create user content)
        pass
    
    async def award_achievement(self, user_id: UUID, achievement_id: UUID) -> Optional[UserAchievement]:
        """Award an achievement to a user."""
        # Check if already earned
        existing_query = select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return None
        
        # Get achievement details
        achievement_query = select(Achievement).where(
            Achievement.achievement_id == achievement_id
        )
        achievement_result = await self.db.execute(achievement_query)
        achievement = achievement_result.scalar_one_or_none()
        
        if not achievement or not achievement.is_active:
            return None
        
        # Create user achievement
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            earned_at=datetime.utcnow()
        )
        self.db.add(user_achievement)
        
        # Update user points
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if user:
            user.points = (user.points or 0) + achievement.points_value
            
            # Send notification
            await send_achievement_notification(
                user,
                achievement,
                user_achievement
            )
        
        await self.db.commit()
        return user_achievement
    
    async def _check_achievement(self, user_id: UUID, achievement_key: str, metadata: dict):
        """Internal method to check and award achievement by key."""
        # Get achievement by key
        achievement_query = select(Achievement).where(
            Achievement.key == achievement_key,
            Achievement.is_active == True
        )
        achievement_result = await self.db.execute(achievement_query)
        achievement = achievement_result.scalar_one_or_none()
        
        if not achievement:
            return
        
        # Check if already earned
        existing_query = select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.achievement_id
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return
        
        # Check conditions based on achievement type
        should_award = await self._evaluate_achievement_conditions(
            user_id,
            achievement,
            metadata
        )
        
        if should_award:
            await self.award_achievement(user_id, achievement.achievement_id)
    
    async def _evaluate_achievement_conditions(
        self,
        user_id: UUID,
        achievement: Achievement,
        metadata: dict
    ) -> bool:
        """Evaluate if achievement conditions are met."""
        condition_type = metadata.get("type")
        
        if condition_type == "enrollment_count":
            count_query = select(func.count(Enrollment.enrollment_id)).where(
                Enrollment.user_id == user_id
            )
            count_result = await self.db.execute(count_query)
            count = count_result.scalar()
            return count >= metadata.get("value", 0)
        
        elif condition_type == "module_count":
            count_query = select(func.count(Progress.progress_id)).where(
                Progress.user_id == user_id,
                Progress.completed_at.isnot(None)
            )
            count_result = await self.db.execute(count_query)
            count = count_result.scalar()
            return count >= metadata.get("value", 0)
        
        elif condition_type == "course_count":
            count_query = select(func.count(Enrollment.enrollment_id)).where(
                Enrollment.user_id == user_id,
                Enrollment.status == "completed"
            )
            count_result = await self.db.execute(count_query)
            count = count_result.scalar()
            return count >= metadata.get("value", 0)
        
        elif condition_type in ["speed_completion", "quiz_perfection", "course_completion"]:
            # These are awarded immediately when the condition is met
            return True
        
        elif condition_type == "department_mastery":
            # Already checked in the calling method
            return True
        
        elif condition_type == "difficulty_completion":
            # Already checked in the calling method
            return True
        
        return False
    
    async def get_user_achievement_progress(self, user_id: UUID) -> dict:
        """Get user's progress towards various achievements."""
        progress = {}
        
        # Enrollment achievements
        enrollment_count_query = select(func.count(Enrollment.enrollment_id)).where(
            Enrollment.user_id == user_id
        )
        enrollment_count_result = await self.db.execute(enrollment_count_query)
        enrollment_count = enrollment_count_result.scalar()
        
        progress["enrollments"] = {
            "current": enrollment_count,
            "next_milestone": self._get_next_milestone(enrollment_count, [1, 5, 10])
        }
        
        # Module achievements
        module_count_query = select(func.count(Progress.progress_id)).where(
            Progress.user_id == user_id,
            Progress.completed_at.isnot(None)
        )
        module_count_result = await self.db.execute(module_count_query)
        module_count = module_count_result.scalar()
        
        progress["modules"] = {
            "current": module_count,
            "next_milestone": self._get_next_milestone(module_count, [10, 25, 50, 100])
        }
        
        # Course achievements
        course_count_query = select(func.count(Enrollment.enrollment_id)).where(
            Enrollment.user_id == user_id,
            Enrollment.status == "completed"
        )
        course_count_result = await self.db.execute(course_count_query)
        course_count = course_count_result.scalar()
        
        progress["courses"] = {
            "current": course_count,
            "next_milestone": self._get_next_milestone(course_count, [1, 5, 10, 25])
        }
        
        return progress
    
    def _get_next_milestone(self, current: int, milestones: List[int]) -> Optional[int]:
        """Get the next milestone to achieve."""
        for milestone in milestones:
            if current < milestone:
                return milestone
        return None