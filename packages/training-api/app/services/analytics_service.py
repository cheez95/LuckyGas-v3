from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import joinedload
import pandas as pd
from collections import defaultdict

from app.models.training import Course, Module, Enrollment, Progress, UserAchievement, Achievement
from app.models.user import User
from app.core.cache import cache


class AnalyticsService:
    """Service for training analytics and reporting."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @cache(expire=300)
    async def get_dashboard_metrics(self, department: Optional[str] = None) -> Dict[str, Any]:
        """Get high-level dashboard metrics."""
        base_filters = []
        if department:
            base_filters.append(User.department == department)
        
        # Total users
        user_query = select(func.count(User.id)).where(
            User.is_active == True,
            *base_filters
        )
        total_users = await self.db.scalar(user_query)
        
        # Active learners (last 30 days)
        active_date = datetime.utcnow() - timedelta(days=30)
        active_query = select(func.count(func.distinct(Enrollment.user_id))).where(
            Enrollment.last_accessed >= active_date
        )
        if department:
            active_query = active_query.join(User).where(User.department == department)
        active_learners = await self.db.scalar(active_query)
        
        # Total courses
        course_query = select(func.count(Course.course_id)).where(
            Course.is_active == True
        )
        if department:
            course_query = course_query.where(
                or_(Course.department == department, Course.department == 'all')
            )
        total_courses = await self.db.scalar(course_query)
        
        # Course completions
        completion_query = select(func.count(Enrollment.enrollment_id)).where(
            Enrollment.status == 'completed'
        )
        if department:
            completion_query = completion_query.join(User).where(User.department == department)
        total_completions = await self.db.scalar(completion_query)
        
        # Average completion rate
        avg_completion_query = select(func.avg(Enrollment.progress_percentage)).where(
            Enrollment.status == 'enrolled'
        )
        if department:
            avg_completion_query = avg_completion_query.join(User).where(User.department == department)
        avg_completion_rate = await self.db.scalar(avg_completion_query) or 0
        
        # Total learning hours
        learning_hours_query = select(func.sum(Progress.time_spent_minutes)).where(
            Progress.time_spent_minutes.isnot(None)
        )
        if department:
            learning_hours_query = learning_hours_query.join(User).where(User.department == department)
        total_minutes = await self.db.scalar(learning_hours_query) or 0
        total_learning_hours = total_minutes / 60
        
        return {
            "total_users": total_users,
            "active_learners": active_learners,
            "engagement_rate": (active_learners / total_users * 100) if total_users > 0 else 0,
            "total_courses": total_courses,
            "total_completions": total_completions,
            "average_completion_rate": float(avg_completion_rate),
            "total_learning_hours": round(total_learning_hours, 1),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def get_course_analytics(self, course_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific course."""
        # Basic course info
        course_query = select(Course).where(Course.course_id == course_id)
        course = await self.db.scalar(course_query)
        
        if not course:
            return {}
        
        # Enrollment stats
        enrollment_stats = await self.db.execute(
            select(
                func.count(Enrollment.enrollment_id).label('total_enrollments'),
                func.count(case((Enrollment.status == 'completed', 1))).label('completions'),
                func.avg(Enrollment.progress_percentage).label('avg_progress'),
                func.avg(
                    case(
                        (Enrollment.completed_at.isnot(None), 
                         func.extract('epoch', Enrollment.completed_at - Enrollment.enrolled_at) / 86400)
                    )
                ).label('avg_completion_days')
            ).where(Enrollment.course_id == course_id)
        )
        stats = enrollment_stats.one()
        
        # Module completion rates
        module_query = select(
            Module.module_id,
            Module.title_zh,
            Module.order_index,
            func.count(Progress.progress_id).label('attempts'),
            func.count(case((Progress.completed_at.isnot(None), 1))).label('completions'),
            func.avg(Progress.time_spent_minutes).label('avg_time'),
            func.avg(Progress.quiz_score).label('avg_quiz_score')
        ).outerjoin(Progress).where(
            Module.course_id == course_id
        ).group_by(Module.module_id, Module.title_zh, Module.order_index).order_by(Module.order_index)
        
        module_results = await self.db.execute(module_query)
        modules = []
        for row in module_results:
            modules.append({
                "module_id": str(row.module_id),
                "title": row.title_zh,
                "order": row.order_index,
                "attempts": row.attempts,
                "completions": row.completions,
                "completion_rate": (row.completions / row.attempts * 100) if row.attempts > 0 else 0,
                "avg_time_minutes": round(row.avg_time or 0, 1),
                "avg_quiz_score": round(row.avg_quiz_score or 0, 1) if row.avg_quiz_score else None
            })
        
        # User feedback/ratings (if implemented)
        # rating_query = select(func.avg(CourseRating.rating)).where(CourseRating.course_id == course_id)
        # avg_rating = await self.db.scalar(rating_query) or 0
        
        # Completion funnel
        funnel = await self._get_course_completion_funnel(course_id)
        
        return {
            "course_id": str(course.course_id),
            "title": course.title_zh,
            "department": course.department,
            "difficulty": course.difficulty,
            "duration_hours": course.duration_hours,
            "total_enrollments": stats.total_enrollments,
            "completions": stats.completions,
            "completion_rate": (stats.completions / stats.total_enrollments * 100) if stats.total_enrollments > 0 else 0,
            "average_progress": float(stats.avg_progress or 0),
            "average_completion_days": float(stats.avg_completion_days or 0),
            "modules": modules,
            "completion_funnel": funnel,
            # "average_rating": avg_rating,
            "is_required": course.is_required,
            "created_at": course.created_at.isoformat()
        }
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific user."""
        # User info
        user_query = select(User).where(User.id == user_id)
        user = await self.db.scalar(user_query)
        
        if not user:
            return {}
        
        # Learning stats
        learning_stats = await self.db.execute(
            select(
                func.count(Enrollment.enrollment_id).label('total_enrollments'),
                func.count(case((Enrollment.status == 'completed', 1))).label('completed_courses'),
                func.sum(Progress.time_spent_minutes).label('total_minutes'),
                func.avg(Progress.quiz_score).label('avg_quiz_score')
            ).outerjoin(Progress, Progress.user_id == user_id)
            .where(Enrollment.user_id == user_id)
        )
        stats = learning_stats.one()
        
        # Achievement stats
        achievement_count = await self.db.scalar(
            select(func.count(UserAchievement.id)).where(UserAchievement.user_id == user_id)
        )
        
        # Recent activity
        recent_activity = await self._get_user_recent_activity(user_id)
        
        # Learning streak
        streak = await self._calculate_learning_streak(user_id)
        
        # Skill progress (based on course categories)
        skill_progress = await self._get_user_skill_progress(user_id)
        
        return {
            "user_id": str(user.id),
            "name": user.name,
            "department": user.department,
            "role": user.role,
            "total_enrollments": stats.total_enrollments,
            "completed_courses": stats.completed_courses,
            "completion_rate": (stats.completed_courses / stats.total_enrollments * 100) if stats.total_enrollments > 0 else 0,
            "total_learning_hours": round((stats.total_minutes or 0) / 60, 1),
            "average_quiz_score": round(stats.avg_quiz_score or 0, 1) if stats.avg_quiz_score else None,
            "total_points": user.points or 0,
            "achievements_earned": achievement_count,
            "current_streak_days": streak,
            "recent_activity": recent_activity,
            "skill_progress": skill_progress,
            "member_since": user.created_at.isoformat()
        }
    
    async def get_department_analytics(self, department: str) -> Dict[str, Any]:
        """Get analytics for a specific department."""
        # Department users
        user_count = await self.db.scalar(
            select(func.count(User.id)).where(
                User.department == department,
                User.is_active == True
            )
        )
        
        # Department-wide metrics
        metrics = await self.get_dashboard_metrics(department)
        
        # Top performers
        top_performers_query = select(
            User.id,
            User.name,
            User.points,
            func.count(Enrollment.enrollment_id).label('completed_courses')
        ).join(Enrollment).where(
            User.department == department,
            Enrollment.status == 'completed'
        ).group_by(User.id, User.name, User.points).order_by(
            func.desc(User.points)
        ).limit(10)
        
        top_performers_result = await self.db.execute(top_performers_query)
        top_performers = []
        for row in top_performers_result:
            top_performers.append({
                "user_id": str(row.id),
                "name": row.name,
                "points": row.points or 0,
                "completed_courses": row.completed_courses
            })
        
        # Course completion by category
        category_stats = await self._get_department_category_stats(department)
        
        # Compliance status (required courses)
        compliance = await self._get_department_compliance(department)
        
        return {
            "department": department,
            "total_users": user_count,
            "metrics": metrics,
            "top_performers": top_performers,
            "category_completion": category_stats,
            "compliance_status": compliance,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def get_learning_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get learning trends over time."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily enrollments
        daily_enrollments = await self.db.execute(
            select(
                func.date(Enrollment.enrolled_at).label('date'),
                func.count(Enrollment.enrollment_id).label('count')
            ).where(
                Enrollment.enrolled_at >= start_date
            ).group_by(func.date(Enrollment.enrolled_at))
            .order_by(func.date(Enrollment.enrolled_at))
        )
        
        enrollments_by_date = {
            row.date.isoformat(): row.count 
            for row in daily_enrollments
        }
        
        # Daily completions
        daily_completions = await self.db.execute(
            select(
                func.date(Enrollment.completed_at).label('date'),
                func.count(Enrollment.enrollment_id).label('count')
            ).where(
                Enrollment.completed_at >= start_date
            ).group_by(func.date(Enrollment.completed_at))
            .order_by(func.date(Enrollment.completed_at))
        )
        
        completions_by_date = {
            row.date.isoformat(): row.count 
            for row in daily_completions
        }
        
        # Daily active users
        daily_active = await self.db.execute(
            select(
                func.date(Progress.last_accessed).label('date'),
                func.count(func.distinct(Progress.user_id)).label('count')
            ).where(
                Progress.last_accessed >= start_date
            ).group_by(func.date(Progress.last_accessed))
            .order_by(func.date(Progress.last_accessed))
        )
        
        active_by_date = {
            row.date.isoformat(): row.count 
            for row in daily_active
        }
        
        # Popular courses
        popular_courses = await self.db.execute(
            select(
                Course.course_id,
                Course.title_zh,
                func.count(Enrollment.enrollment_id).label('enrollments')
            ).join(Enrollment).where(
                Enrollment.enrolled_at >= start_date
            ).group_by(Course.course_id, Course.title_zh)
            .order_by(func.desc('enrollments'))
            .limit(10)
        )
        
        popular = []
        for row in popular_courses:
            popular.append({
                "course_id": str(row.course_id),
                "title": row.title_zh,
                "enrollments": row.enrollments
            })
        
        return {
            "period_days": days,
            "enrollments_by_date": enrollments_by_date,
            "completions_by_date": completions_by_date,
            "active_users_by_date": active_by_date,
            "popular_courses": popular,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
    
    async def generate_report(self, report_type: str, filters: Dict[str, Any]) -> bytes:
        """Generate downloadable reports in Excel format."""
        if report_type == "user_progress":
            df = await self._generate_user_progress_report(filters)
        elif report_type == "course_completion":
            df = await self._generate_course_completion_report(filters)
        elif report_type == "department_summary":
            df = await self._generate_department_summary_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # Convert to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Report']
            for column in df:
                column_width = max(df[column].astype(str).map(len).max(), len(column)) + 2
                col_idx = df.columns.get_loc(column)
                worksheet.column_dimensions[worksheet.cell(1, col_idx + 1).column_letter].width = column_width
        
        output.seek(0)
        return output.read()
    
    # Helper methods
    
    async def _get_course_completion_funnel(self, course_id: str) -> List[Dict[str, Any]]:
        """Get completion funnel for a course."""
        modules = await self.db.execute(
            select(Module).where(
                Module.course_id == course_id
            ).order_by(Module.order_index)
        )
        
        funnel = []
        for module in modules.scalars():
            started = await self.db.scalar(
                select(func.count(func.distinct(Progress.user_id))).where(
                    Progress.module_id == module.module_id
                )
            )
            
            completed = await self.db.scalar(
                select(func.count(func.distinct(Progress.user_id))).where(
                    Progress.module_id == module.module_id,
                    Progress.completed_at.isnot(None)
                )
            )
            
            funnel.append({
                "module": module.title_zh,
                "order": module.order_index,
                "started": started,
                "completed": completed,
                "dropout_rate": ((started - completed) / started * 100) if started > 0 else 0
            })
        
        return funnel
    
    async def _get_user_recent_activity(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent learning activity."""
        activities = await self.db.execute(
            select(
                Progress.last_accessed,
                Module.title_zh.label('module_title'),
                Course.title_zh.label('course_title'),
                Progress.progress_percentage
            ).join(Module).join(Course).where(
                Progress.user_id == user_id
            ).order_by(Progress.last_accessed.desc()).limit(limit)
        )
        
        return [
            {
                "timestamp": row.last_accessed.isoformat(),
                "module": row.module_title,
                "course": row.course_title,
                "progress": row.progress_percentage
            }
            for row in activities
        ]
    
    async def _calculate_learning_streak(self, user_id: str) -> int:
        """Calculate user's current learning streak in days."""
        # Get distinct dates with activity
        activity_dates = await self.db.execute(
            select(func.distinct(func.date(Progress.last_accessed))).where(
                Progress.user_id == user_id
            ).order_by(func.desc(func.date(Progress.last_accessed)))
        )
        
        dates = [row[0] for row in activity_dates]
        if not dates:
            return 0
        
        # Calculate streak
        streak = 1
        current_date = dates[0]
        
        for i in range(1, len(dates)):
            if (current_date - dates[i]).days == 1:
                streak += 1
                current_date = dates[i]
            else:
                break
        
        # Check if streak is current
        if (datetime.utcnow().date() - dates[0]).days > 1:
            return 0
        
        return streak
    
    async def _get_user_skill_progress(self, user_id: str) -> Dict[str, Any]:
        """Get user's progress by skill/category."""
        skill_query = await self.db.execute(
            select(
                Course.category,
                func.count(Enrollment.enrollment_id).label('total'),
                func.count(case((Enrollment.status == 'completed', 1))).label('completed')
            ).join(Enrollment).where(
                Enrollment.user_id == user_id
            ).group_by(Course.category)
        )
        
        skills = {}
        for row in skill_query:
            skills[row.category] = {
                "total_courses": row.total,
                "completed_courses": row.completed,
                "progress_percentage": (row.completed / row.total * 100) if row.total > 0 else 0
            }
        
        return skills
    
    async def _get_department_category_stats(self, department: str) -> Dict[str, Any]:
        """Get course completion stats by category for a department."""
        stats_query = await self.db.execute(
            select(
                Course.category,
                func.count(func.distinct(Course.course_id)).label('total_courses'),
                func.count(Enrollment.enrollment_id).label('total_enrollments'),
                func.count(case((Enrollment.status == 'completed', 1))).label('completions')
            ).outerjoin(Enrollment).join(User).where(
                User.department == department,
                or_(Course.department == department, Course.department == 'all')
            ).group_by(Course.category)
        )
        
        categories = {}
        for row in stats_query:
            categories[row.category] = {
                "courses": row.total_courses,
                "enrollments": row.total_enrollments,
                "completions": row.completions,
                "completion_rate": (row.completions / row.total_enrollments * 100) if row.total_enrollments > 0 else 0
            }
        
        return categories
    
    async def _get_department_compliance(self, department: str) -> Dict[str, Any]:
        """Get compliance status for required courses in a department."""
        # Get required courses for department
        required_courses = await self.db.execute(
            select(Course).where(
                Course.is_required == True,
                or_(Course.department == department, Course.department == 'all'),
                Course.is_active == True
            )
        )
        
        compliance_data = []
        
        for course in required_courses.scalars():
            # Get completion stats
            total_users = await self.db.scalar(
                select(func.count(User.id)).where(
                    User.department == department,
                    User.is_active == True
                )
            )
            
            completed_users = await self.db.scalar(
                select(func.count(func.distinct(Enrollment.user_id))).join(User).where(
                    User.department == department,
                    Enrollment.course_id == course.course_id,
                    Enrollment.status == 'completed'
                )
            )
            
            compliance_data.append({
                "course_id": str(course.course_id),
                "title": course.title_zh,
                "total_users": total_users,
                "completed_users": completed_users,
                "compliance_rate": (completed_users / total_users * 100) if total_users > 0 else 0,
                "deadline": course.deadline.isoformat() if hasattr(course, 'deadline') and course.deadline else None
            })
        
        overall_compliance = sum(c['compliance_rate'] for c in compliance_data) / len(compliance_data) if compliance_data else 0
        
        return {
            "overall_compliance_rate": overall_compliance,
            "required_courses": compliance_data
        }
    
    async def _generate_user_progress_report(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Generate detailed user progress report."""
        query = select(
            User.name,
            User.email,
            User.department,
            User.role,
            func.count(Enrollment.enrollment_id).label('enrolled_courses'),
            func.count(case((Enrollment.status == 'completed', 1))).label('completed_courses'),
            func.avg(Enrollment.progress_percentage).label('avg_progress'),
            func.sum(Progress.time_spent_minutes).label('total_minutes'),
            User.points
        ).outerjoin(Enrollment).outerjoin(Progress).where(
            User.is_active == True
        ).group_by(User.id, User.name, User.email, User.department, User.role, User.points)
        
        # Apply filters
        if filters.get('department'):
            query = query.where(User.department == filters['department'])
        
        if filters.get('start_date'):
            query = query.where(Enrollment.enrolled_at >= filters['start_date'])
        
        if filters.get('end_date'):
            query = query.where(Enrollment.enrolled_at <= filters['end_date'])
        
        result = await self.db.execute(query)
        
        data = []
        for row in result:
            data.append({
                '姓名': row.name,
                'Email': row.email,
                '部門': row.department,
                '角色': row.role,
                '已註冊課程': row.enrolled_courses,
                '已完成課程': row.completed_courses,
                '平均進度 (%)': round(row.avg_progress or 0, 1),
                '總學習時間 (小時)': round((row.total_minutes or 0) / 60, 1),
                '積分': row.points or 0
            })
        
        return pd.DataFrame(data)
    
    async def _generate_course_completion_report(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Generate course completion report."""
        query = select(
            Course.title_zh,
            Course.department,
            Course.difficulty,
            Course.duration_hours,
            func.count(Enrollment.enrollment_id).label('total_enrollments'),
            func.count(case((Enrollment.status == 'completed', 1))).label('completions'),
            func.avg(Enrollment.progress_percentage).label('avg_progress'),
            func.avg(
                case(
                    (Enrollment.completed_at.isnot(None), 
                     func.extract('epoch', Enrollment.completed_at - Enrollment.enrolled_at) / 86400)
                )
            ).label('avg_completion_days')
        ).outerjoin(Enrollment).where(
            Course.is_active == True
        ).group_by(Course.course_id, Course.title_zh, Course.department, Course.difficulty, Course.duration_hours)
        
        # Apply filters
        if filters.get('department'):
            query = query.where(
                or_(Course.department == filters['department'], Course.department == 'all')
            )
        
        result = await self.db.execute(query)
        
        data = []
        for row in result:
            completion_rate = (row.completions / row.total_enrollments * 100) if row.total_enrollments > 0 else 0
            data.append({
                '課程名稱': row.title_zh,
                '部門': row.department,
                '難度': row.difficulty,
                '時長 (小時)': row.duration_hours,
                '總註冊人數': row.total_enrollments,
                '完成人數': row.completions,
                '完成率 (%)': round(completion_rate, 1),
                '平均進度 (%)': round(row.avg_progress or 0, 1),
                '平均完成天數': round(row.avg_completion_days or 0, 1)
            })
        
        return pd.DataFrame(data)
    
    async def _generate_department_summary_report(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Generate department summary report."""
        departments = await self.db.execute(
            select(func.distinct(User.department)).where(User.is_active == True)
        )
        
        data = []
        for dept_row in departments:
            department = dept_row[0]
            if filters.get('department') and department != filters['department']:
                continue
            
            metrics = await self.get_department_analytics(department)
            
            data.append({
                '部門': department,
                '總人數': metrics['total_users'],
                '活躍學習者': metrics['metrics']['active_learners'],
                '參與率 (%)': round(metrics['metrics']['engagement_rate'], 1),
                '平均完成率 (%)': round(metrics['metrics']['average_completion_rate'], 1),
                '總學習時數': metrics['metrics']['total_learning_hours'],
                '合規率 (%)': round(metrics['compliance_status']['overall_compliance_rate'], 1)
            })
        
        return pd.DataFrame(data)