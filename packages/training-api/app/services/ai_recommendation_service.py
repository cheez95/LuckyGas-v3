import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import pandas as pd

from app.models.training import Course, Module, Enrollment, Progress, UserAchievement
from app.models.user import User
from app.services.caching_service import cache_service, cache_result


class AIRecommendationService:
    """AI-powered learning recommendation system using collaborative filtering and content-based filtering."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = cache_service
        
        # Feature weights for recommendation scoring
        self.weights = {
            "user_similarity": 0.3,
            "course_similarity": 0.25,
            "skill_gap": 0.2,
            "department_relevance": 0.15,
            "difficulty_progression": 0.1
        }
    
    async def get_personalized_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        exclude_enrolled: bool = True
    ) -> List[Dict[str, Any]]:
        """Get personalized course recommendations for a user."""
        # Try cache first
        cache_key = f"recommendations:{user_id}:{limit}:{exclude_enrolled}"
        cached = await self.cache.get(cache_key, namespace="ai_recommendations")
        if cached:
            return cached
        
        # Get user profile and history
        user_profile = await self._get_user_profile(user_id)
        if not user_profile:
            return []
        
        # Get recommendation scores using multiple strategies
        scores = {}
        
        # 1. Collaborative filtering (user-based)
        collab_scores = await self._collaborative_filtering(user_id, user_profile)
        for course_id, score in collab_scores.items():
            scores[course_id] = scores.get(course_id, 0) + score * self.weights["user_similarity"]
        
        # 2. Content-based filtering
        content_scores = await self._content_based_filtering(user_id, user_profile)
        for course_id, score in content_scores.items():
            scores[course_id] = scores.get(course_id, 0) + score * self.weights["course_similarity"]
        
        # 3. Skill gap analysis
        skill_gap_scores = await self._skill_gap_analysis(user_id, user_profile)
        for course_id, score in skill_gap_scores.items():
            scores[course_id] = scores.get(course_id, 0) + score * self.weights["skill_gap"]
        
        # 4. Department relevance
        dept_scores = await self._department_relevance_scoring(user_profile)
        for course_id, score in dept_scores.items():
            scores[course_id] = scores.get(course_id, 0) + score * self.weights["department_relevance"]
        
        # 5. Difficulty progression
        diff_scores = await self._difficulty_progression_scoring(user_id, user_profile)
        for course_id, score in diff_scores.items():
            scores[course_id] = scores.get(course_id, 0) + score * self.weights["difficulty_progression"]
        
        # Filter out enrolled courses if requested
        if exclude_enrolled:
            enrolled_courses = await self._get_enrolled_courses(user_id)
            for course_id in enrolled_courses:
                scores.pop(str(course_id), None)
        
        # Sort by score and get top recommendations
        sorted_courses = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Fetch course details
        recommendations = []
        for course_id, score in sorted_courses:
            course = await self._get_course_details(course_id)
            if course:
                recommendation = {
                    "course_id": course_id,
                    "title_zh": course["title_zh"],
                    "title_en": course["title_en"],
                    "description_zh": course["description_zh"],
                    "department": course["department"],
                    "difficulty": course["difficulty"],
                    "duration_hours": course["duration_hours"],
                    "recommendation_score": round(score, 3),
                    "reasons": await self._get_recommendation_reasons(user_id, course_id, score)
                }
                recommendations.append(recommendation)
        
        # Cache results
        await self.cache.set(
            cache_key,
            recommendations,
            ttl=3600,  # 1 hour
            namespace="ai_recommendations"
        )
        
        return recommendations
    
    async def get_next_module_recommendation(
        self,
        user_id: str,
        course_id: str
    ) -> Optional[Dict[str, Any]]:
        """Recommend the next best module to study in a course."""
        # Get user's progress in the course
        progress_query = select(Progress).where(
            Progress.user_id == user_id,
            Progress.module_id.in_(
                select(Module.module_id).where(Module.course_id == course_id)
            )
        )
        progress_result = await self.db.execute(progress_query)
        user_progress = {p.module_id: p for p in progress_result.scalars().all()}
        
        # Get all modules in the course
        modules_query = select(Module).where(
            Module.course_id == course_id,
            Module.is_active == True
        ).order_by(Module.order_index)
        modules_result = await self.db.execute(modules_query)
        modules = modules_result.scalars().all()
        
        # Find the best next module
        best_module = None
        best_score = -1
        
        for module in modules:
            # Skip completed modules
            if module.module_id in user_progress and user_progress[module.module_id].completed_at:
                continue
            
            score = 0
            
            # Prefer modules in order (but not strictly)
            order_score = 1.0 - (module.order_index / len(modules)) * 0.3
            score += order_score
            
            # Check prerequisites
            if hasattr(module, 'prerequisites') and module.prerequisites:
                prereq_met = all(
                    pid in user_progress and user_progress[pid].completed_at
                    for pid in module.prerequisites
                )
                if not prereq_met:
                    continue
            
            # Consider partially completed modules
            if module.module_id in user_progress:
                partial_progress = user_progress[module.module_id].progress_percentage / 100
                score += partial_progress * 0.5
            
            # Consider difficulty progression
            if hasattr(module, 'difficulty_level'):
                # Implement difficulty scoring
                pass
            
            if score > best_score:
                best_score = score
                best_module = module
        
        if best_module:
            return {
                "module_id": str(best_module.module_id),
                "title_zh": best_module.title_zh,
                "title_en": best_module.title_en,
                "content_type": best_module.content_type,
                "duration_minutes": best_module.duration_minutes,
                "order_index": best_module.order_index,
                "recommendation_reason": "Based on your progress and learning path"
            }
        
        return None
    
    async def get_learning_path_recommendation(
        self,
        user_id: str,
        goal: str
    ) -> List[Dict[str, Any]]:
        """Generate a personalized learning path towards a specific goal."""
        # This would typically use a more sophisticated algorithm
        # For now, we'll create a simple path based on prerequisites
        
        learning_path = []
        
        # Identify target courses for the goal
        if goal == "manager_training":
            target_categories = ["leadership", "management", "communication"]
            difficulty_order = ["beginner", "intermediate", "advanced"]
        elif goal == "safety_certification":
            target_categories = ["safety", "compliance", "emergency"]
            difficulty_order = ["beginner", "intermediate", "advanced"]
        else:
            # Generic learning path
            target_categories = ["general", "skills"]
            difficulty_order = ["beginner", "intermediate", "advanced"]
        
        # Get courses in order of difficulty
        for difficulty in difficulty_order:
            courses_query = select(Course).where(
                Course.category.in_(target_categories),
                Course.difficulty == difficulty,
                Course.is_active == True
            ).order_by(Course.duration_hours)
            
            courses_result = await self.db.execute(courses_query)
            courses = courses_result.scalars().all()
            
            for course in courses[:2]:  # Limit courses per difficulty
                learning_path.append({
                    "course_id": str(course.course_id),
                    "title_zh": course.title_zh,
                    "difficulty": course.difficulty,
                    "duration_hours": course.duration_hours,
                    "order": len(learning_path) + 1,
                    "estimated_completion_days": course.duration_hours * 2
                })
        
        return learning_path
    
    async def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive user profile for recommendations."""
        # Get user basic info
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Get learning history
        enrollments_query = select(Enrollment).where(Enrollment.user_id == user_id)
        enrollments_result = await self.db.execute(enrollments_query)
        enrollments = enrollments_result.scalars().all()
        
        # Get completed courses
        completed_courses = [
            e.course_id for e in enrollments if e.status == "completed"
        ]
        
        # Get average quiz scores
        quiz_scores_query = select(func.avg(Progress.quiz_score)).where(
            Progress.user_id == user_id,
            Progress.quiz_score.isnot(None)
        )
        avg_quiz_score = await self.db.scalar(quiz_scores_query) or 0
        
        # Calculate learning velocity (courses per month)
        if completed_courses:
            first_enrollment = min(e.enrolled_at for e in enrollments)
            months_active = max(1, (datetime.utcnow() - first_enrollment).days / 30)
            learning_velocity = len(completed_courses) / months_active
        else:
            learning_velocity = 0
        
        return {
            "user_id": user_id,
            "department": user.department,
            "role": user.role,
            "completed_courses": completed_courses,
            "enrolled_courses": [e.course_id for e in enrollments],
            "avg_quiz_score": float(avg_quiz_score),
            "learning_velocity": learning_velocity,
            "total_points": user.points or 0
        }
    
    async def _collaborative_filtering(
        self,
        user_id: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """User-based collaborative filtering."""
        # Find similar users based on course completion patterns
        similar_users = await self._find_similar_users(user_id, user_profile)
        
        scores = {}
        
        for similar_user_id, similarity_score in similar_users:
            # Get courses completed by similar user but not by current user
            similar_user_courses_query = select(Enrollment.course_id).where(
                Enrollment.user_id == similar_user_id,
                Enrollment.status == "completed",
                ~Enrollment.course_id.in_(user_profile["enrolled_courses"])
            )
            similar_user_courses_result = await self.db.execute(similar_user_courses_query)
            
            for course_id in similar_user_courses_result.scalars():
                course_id_str = str(course_id)
                scores[course_id_str] = scores.get(course_id_str, 0) + similarity_score
        
        # Normalize scores
        if scores:
            max_score = max(scores.values())
            scores = {k: v / max_score for k, v in scores.items()}
        
        return scores
    
    async def _find_similar_users(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Find users with similar learning patterns."""
        # Get all users in same department
        users_query = select(User).where(
            User.department == user_profile["department"],
            User.id != user_id,
            User.is_active == True
        )
        users_result = await self.db.execute(users_query)
        department_users = users_result.scalars().all()
        
        similar_users = []
        
        for other_user in department_users:
            # Get their completed courses
            other_enrollments_query = select(Enrollment.course_id).where(
                Enrollment.user_id == other_user.id,
                Enrollment.status == "completed"
            )
            other_enrollments_result = await self.db.execute(other_enrollments_query)
            other_completed = set(str(c) for c in other_enrollments_result.scalars())
            
            user_completed = set(str(c) for c in user_profile["completed_courses"])
            
            # Calculate Jaccard similarity
            if user_completed or other_completed:
                intersection = len(user_completed & other_completed)
                union = len(user_completed | other_completed)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0:
                    similar_users.append((str(other_user.id), similarity))
        
        # Sort by similarity and return top N
        similar_users.sort(key=lambda x: x[1], reverse=True)
        return similar_users[:limit]
    
    async def _content_based_filtering(
        self,
        user_id: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """Content-based filtering using course features."""
        if not user_profile["completed_courses"]:
            return {}
        
        # Get features of completed courses
        completed_features = await self._get_course_features(user_profile["completed_courses"])
        
        if not completed_features:
            return {}
        
        # Get all available courses
        all_courses_query = select(Course).where(
            Course.is_active == True,
            ~Course.course_id.in_(user_profile["enrolled_courses"])
        )
        all_courses_result = await self.db.execute(all_courses_query)
        available_courses = all_courses_result.scalars().all()
        
        scores = {}
        
        for course in available_courses:
            # Calculate similarity with completed courses
            course_features = self._extract_course_features(course)
            
            max_similarity = 0
            for completed_feat in completed_features:
                similarity = self._calculate_feature_similarity(course_features, completed_feat)
                max_similarity = max(max_similarity, similarity)
            
            scores[str(course.course_id)] = max_similarity
        
        return scores
    
    async def _skill_gap_analysis(
        self,
        user_id: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """Identify skill gaps and recommend courses to fill them."""
        # Define skill requirements by role
        role_skills = {
            "manager": ["leadership", "planning", "communication", "analytics"],
            "office_staff": ["customer_service", "systems", "communication", "compliance"],
            "driver": ["safety", "navigation", "customer_service", "maintenance"]
        }
        
        required_skills = role_skills.get(user_profile["role"], [])
        
        # Analyze completed courses for acquired skills
        acquired_skills = set()
        if user_profile["completed_courses"]:
            # This would typically map courses to skills
            # For now, we'll use categories as a proxy
            completed_query = select(Course.category).where(
                Course.course_id.in_(user_profile["completed_courses"])
            ).distinct()
            completed_result = await self.db.execute(completed_query)
            acquired_skills = set(completed_result.scalars())
        
        # Find courses that teach missing skills
        missing_skills = set(required_skills) - acquired_skills
        
        if not missing_skills:
            return {}
        
        # Score courses based on skill coverage
        skill_courses_query = select(Course).where(
            Course.category.in_(missing_skills),
            Course.is_active == True,
            ~Course.course_id.in_(user_profile["enrolled_courses"])
        )
        skill_courses_result = await self.db.execute(skill_courses_query)
        skill_courses = skill_courses_result.scalars().all()
        
        scores = {}
        for course in skill_courses:
            # Higher score for required courses
            base_score = 0.8 if course.is_required else 0.6
            
            # Adjust for difficulty (prefer appropriate level)
            if user_profile["completed_courses"]:
                if course.difficulty == "beginner" and len(user_profile["completed_courses"]) > 5:
                    base_score *= 0.7
                elif course.difficulty == "advanced" and len(user_profile["completed_courses"]) < 3:
                    base_score *= 0.5
            
            scores[str(course.course_id)] = base_score
        
        return scores
    
    async def _department_relevance_scoring(
        self,
        user_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """Score courses based on department relevance."""
        dept_courses_query = select(Course).where(
            or_(
                Course.department == user_profile["department"],
                Course.department == "all"
            ),
            Course.is_active == True,
            ~Course.course_id.in_(user_profile["enrolled_courses"])
        )
        dept_courses_result = await self.db.execute(dept_courses_query)
        dept_courses = dept_courses_result.scalars().all()
        
        scores = {}
        for course in dept_courses:
            if course.department == user_profile["department"]:
                scores[str(course.course_id)] = 1.0
            else:  # department == "all"
                scores[str(course.course_id)] = 0.7
        
        return scores
    
    async def _difficulty_progression_scoring(
        self,
        user_id: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """Score courses based on appropriate difficulty progression."""
        # Determine user's current level
        completed_count = len(user_profile["completed_courses"])
        avg_quiz_score = user_profile["avg_quiz_score"]
        
        if completed_count == 0:
            preferred_difficulty = "beginner"
        elif completed_count < 5:
            preferred_difficulty = "beginner" if avg_quiz_score < 70 else "intermediate"
        elif completed_count < 10:
            preferred_difficulty = "intermediate" if avg_quiz_score < 80 else "advanced"
        else:
            preferred_difficulty = "advanced" if avg_quiz_score > 75 else "intermediate"
        
        # Score courses based on difficulty match
        difficulty_scores = {
            "beginner": {"beginner": 1.0, "intermediate": 0.5, "advanced": 0.2},
            "intermediate": {"beginner": 0.3, "intermediate": 1.0, "advanced": 0.7},
            "advanced": {"beginner": 0.1, "intermediate": 0.6, "advanced": 1.0}
        }
        
        scores = {}
        
        courses_query = select(Course).where(
            Course.is_active == True,
            ~Course.course_id.in_(user_profile["enrolled_courses"])
        )
        courses_result = await self.db.execute(courses_query)
        courses = courses_result.scalars().all()
        
        for course in courses:
            score = difficulty_scores[preferred_difficulty].get(course.difficulty, 0.5)
            scores[str(course.course_id)] = score
        
        return scores
    
    def _extract_course_features(self, course: Course) -> Dict[str, Any]:
        """Extract features from a course for similarity calculation."""
        return {
            "category": course.category,
            "difficulty": course.difficulty,
            "department": course.department,
            "duration_hours": course.duration_hours,
            "is_required": course.is_required,
            "tags": getattr(course, 'tags', [])
        }
    
    async def _get_course_features(self, course_ids: List[str]) -> List[Dict[str, Any]]:
        """Get features for multiple courses."""
        courses_query = select(Course).where(Course.course_id.in_(course_ids))
        courses_result = await self.db.execute(courses_query)
        courses = courses_result.scalars().all()
        
        return [self._extract_course_features(course) for course in courses]
    
    def _calculate_feature_similarity(self, features1: Dict, features2: Dict) -> float:
        """Calculate similarity between two course feature sets."""
        score = 0.0
        
        # Category match
        if features1["category"] == features2["category"]:
            score += 0.3
        
        # Difficulty similarity
        diff_map = {"beginner": 0, "intermediate": 1, "advanced": 2}
        diff1 = diff_map.get(features1["difficulty"], 1)
        diff2 = diff_map.get(features2["difficulty"], 1)
        diff_score = 1 - abs(diff1 - diff2) / 2
        score += diff_score * 0.2
        
        # Department match
        if features1["department"] == features2["department"]:
            score += 0.2
        elif features1["department"] == "all" or features2["department"] == "all":
            score += 0.1
        
        # Duration similarity (normalize to 0-1)
        dur1 = features1["duration_hours"]
        dur2 = features2["duration_hours"]
        dur_similarity = 1 - abs(dur1 - dur2) / max(dur1, dur2) if max(dur1, dur2) > 0 else 1
        score += dur_similarity * 0.15
        
        # Required course boost
        if features1["is_required"] and features2["is_required"]:
            score += 0.1
        
        # Tag overlap (if available)
        if features1.get("tags") and features2.get("tags"):
            tags1 = set(features1["tags"])
            tags2 = set(features2["tags"])
            if tags1 and tags2:
                overlap = len(tags1 & tags2) / len(tags1 | tags2)
                score += overlap * 0.05
        
        return min(score, 1.0)
    
    async def _get_enrolled_courses(self, user_id: str) -> List[str]:
        """Get list of courses user is enrolled in."""
        query = select(Enrollment.course_id).where(Enrollment.user_id == user_id)
        result = await self.db.execute(query)
        return [str(course_id) for course_id in result.scalars()]
    
    async def _get_course_details(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get course details by ID."""
        query = select(Course).where(Course.course_id == course_id)
        result = await self.db.execute(query)
        course = result.scalar_one_or_none()
        
        if course:
            return {
                "course_id": str(course.course_id),
                "title_zh": course.title_zh,
                "title_en": course.title_en,
                "description_zh": course.description_zh,
                "description_en": course.description_en,
                "department": course.department,
                "difficulty": course.difficulty,
                "duration_hours": course.duration_hours,
                "category": course.category,
                "is_required": course.is_required
            }
        
        return None
    
    async def _get_recommendation_reasons(
        self,
        user_id: str,
        course_id: str,
        score: float
    ) -> List[str]:
        """Generate human-readable reasons for recommendation."""
        reasons = []
        
        if score > 0.8:
            reasons.append("強烈推薦：非常適合您的學習需求")
        elif score > 0.6:
            reasons.append("推薦：符合您的學習方向")
        
        # Add specific reasons based on scoring components
        # This would be more sophisticated in production
        reasons.extend([
            "與您已完成的課程相關",
            "符合您的部門需求",
            "適合您目前的學習程度"
        ])
        
        return reasons[:3]  # Limit to 3 reasons