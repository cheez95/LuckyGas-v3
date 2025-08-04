from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from sqlalchemy.dialects.postgresql import TSVECTOR
import re

from app.models.training import Course, Module
from app.models.user import User
from app.core.cache import cache
from app.services.caching_service import cache_service, CacheKeyBuilder


class SearchService:
    """Advanced search service with full-text search and relevance ranking."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.min_search_length = 2
        self.max_results = 100
        
        # Search weights for different fields
        self.weights = {
            "title": 3.0,
            "description": 2.0,
            "content": 1.0,
            "tags": 2.5,
            "instructor": 1.5
        }
    
    async def search_courses(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """Search courses with relevance ranking."""
        # Validate query
        query = query.strip()
        if len(query) < self.min_search_length:
            return [], 0
        
        # Check cache first
        cache_key = f"search:courses:{query}:{filters}:{limit}:{offset}"
        cached = await cache_service.get(cache_key, namespace="search")
        if cached:
            return cached
        
        # Prepare search terms
        search_terms = self._prepare_search_terms(query)
        
        # Build base query
        courses_query = select(Course).where(Course.is_active == True)
        
        # Apply filters
        if filters:
            if filters.get("department"):
                courses_query = courses_query.where(
                    or_(
                        Course.department == filters["department"],
                        Course.department == "all"
                    )
                )
            
            if filters.get("difficulty"):
                courses_query = courses_query.where(
                    Course.difficulty == filters["difficulty"]
                )
            
            if filters.get("category"):
                courses_query = courses_query.where(
                    Course.category == filters["category"]
                )
            
            if filters.get("duration_min"):
                courses_query = courses_query.where(
                    Course.duration_hours >= filters["duration_min"]
                )
            
            if filters.get("duration_max"):
                courses_query = courses_query.where(
                    Course.duration_hours <= filters["duration_max"]
                )
        
        # Apply search conditions
        search_conditions = []
        
        # Full-text search on title and description
        for term in search_terms:
            term_conditions = or_(
                func.lower(Course.title_zh).contains(term.lower()),
                func.lower(Course.title_en).contains(term.lower()),
                func.lower(Course.description_zh).contains(term.lower()),
                func.lower(Course.description_en).contains(term.lower()),
            )
            search_conditions.append(term_conditions)
        
        if search_conditions:
            courses_query = courses_query.where(or_(*search_conditions))
        
        # Count total results
        count_query = select(func.count()).select_from(courses_query.subquery())
        total_count = await self.db.scalar(count_query)
        
        # Apply pagination
        courses_query = courses_query.offset(offset).limit(limit)
        
        # Execute query
        result = await self.db.execute(courses_query)
        courses = result.scalars().all()
        
        # Calculate relevance scores
        scored_courses = []
        for course in courses:
            score = self._calculate_relevance_score(course, search_terms)
            course_dict = {
                "course_id": str(course.course_id),
                "title_zh": course.title_zh,
                "title_en": course.title_en,
                "description_zh": course.description_zh,
                "description_en": course.description_en,
                "department": course.department,
                "difficulty": course.difficulty,
                "duration_hours": course.duration_hours,
                "category": course.category,
                "is_required": course.is_required,
                "relevance_score": score
            }
            
            # Add user-specific data if available
            if user_id:
                enrollment = await self._get_user_enrollment(user_id, course.course_id)
                if enrollment:
                    course_dict["enrollment_status"] = enrollment.status
                    course_dict["progress_percentage"] = enrollment.progress_percentage
            
            scored_courses.append(course_dict)
        
        # Sort by relevance score
        scored_courses.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Cache results
        result_tuple = (scored_courses, total_count)
        await cache_service.set(
            cache_key,
            result_tuple,
            ttl=300,  # 5 minutes
            namespace="search",
            tags=["search", "courses"]
        )
        
        return result_tuple
    
    async def search_modules(
        self,
        query: str,
        course_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Search modules within courses."""
        # Validate query
        query = query.strip()
        if len(query) < self.min_search_length:
            return [], 0
        
        # Prepare search terms
        search_terms = self._prepare_search_terms(query)
        
        # Build query
        modules_query = select(Module).join(Course).where(
            Module.is_active == True,
            Course.is_active == True
        )
        
        if course_id:
            modules_query = modules_query.where(Module.course_id == course_id)
        
        # Apply search conditions
        search_conditions = []
        for term in search_terms:
            term_conditions = or_(
                func.lower(Module.title_zh).contains(term.lower()),
                func.lower(Module.title_en).contains(term.lower()),
                func.lower(Module.description_zh).contains(term.lower()),
                func.lower(Module.description_en).contains(term.lower()),
            )
            search_conditions.append(term_conditions)
        
        if search_conditions:
            modules_query = modules_query.where(or_(*search_conditions))
        
        # Count total
        count_query = select(func.count()).select_from(modules_query.subquery())
        total_count = await self.db.scalar(count_query)
        
        # Apply pagination
        modules_query = modules_query.offset(offset).limit(limit)
        
        # Execute query
        result = await self.db.execute(modules_query)
        modules = result.scalars().all()
        
        # Format results
        module_results = []
        for module in modules:
            module_dict = {
                "module_id": str(module.module_id),
                "course_id": str(module.course_id),
                "title_zh": module.title_zh,
                "title_en": module.title_en,
                "description_zh": module.description_zh,
                "description_en": module.description_en,
                "content_type": module.content_type,
                "duration_minutes": module.duration_minutes,
                "order_index": module.order_index
            }
            module_results.append(module_dict)
        
        return module_results, total_count
    
    async def global_search(
        self,
        query: str,
        types: List[str] = ["courses", "modules", "users"],
        limit: int = 10
    ) -> Dict[str, List[Dict]]:
        """Perform global search across multiple entity types."""
        results = {}
        
        # Search in parallel
        tasks = []
        
        if "courses" in types:
            tasks.append(self.search_courses(query, limit=limit))
        
        if "modules" in types:
            tasks.append(self.search_modules(query, limit=limit))
        
        if "users" in types:
            tasks.append(self.search_users(query, limit=limit))
        
        # Execute all searches in parallel
        search_results = await asyncio.gather(*tasks)
        
        # Map results
        result_index = 0
        if "courses" in types:
            results["courses"] = search_results[result_index][0]
            result_index += 1
        
        if "modules" in types:
            results["modules"] = search_results[result_index][0]
            result_index += 1
        
        if "users" in types:
            results["users"] = search_results[result_index][0]
            result_index += 1
        
        return results
    
    async def search_users(
        self,
        query: str,
        department: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Search users (for admin/manager features)."""
        # This should be restricted to authorized users only
        query = query.strip()
        if len(query) < self.min_search_length:
            return [], 0
        
        # Build query
        users_query = select(User).where(User.is_active == True)
        
        if department:
            users_query = users_query.where(User.department == department)
        
        # Search in name and email
        search_conditions = or_(
            func.lower(User.name).contains(query.lower()),
            func.lower(User.email).contains(query.lower())
        )
        users_query = users_query.where(search_conditions)
        
        # Count total
        count_query = select(func.count()).select_from(users_query.subquery())
        total_count = await self.db.scalar(count_query)
        
        # Apply pagination
        users_query = users_query.offset(offset).limit(limit)
        
        # Execute query
        result = await self.db.execute(users_query)
        users = result.scalars().all()
        
        # Format results (exclude sensitive data)
        user_results = []
        for user in users:
            user_dict = {
                "user_id": str(user.id),
                "name": user.name,
                "department": user.department,
                "role": user.role,
                "points": user.points or 0
            }
            user_results.append(user_dict)
        
        return user_results, total_count
    
    def _prepare_search_terms(self, query: str) -> List[str]:
        """Prepare search terms from query."""
        # Remove special characters
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        
        # Split into terms
        terms = cleaned.split()
        
        # Remove duplicates and short terms
        unique_terms = []
        seen = set()
        for term in terms:
            if term not in seen and len(term) >= self.min_search_length:
                unique_terms.append(term)
                seen.add(term)
        
        return unique_terms
    
    def _calculate_relevance_score(self, course: Course, search_terms: List[str]) -> float:
        """Calculate relevance score for a course."""
        score = 0.0
        
        # Check each search term
        for term in search_terms:
            term_lower = term.lower()
            
            # Title matches (highest weight)
            if term_lower in course.title_zh.lower():
                score += self.weights["title"]
            if term_lower in course.title_en.lower():
                score += self.weights["title"]
            
            # Description matches
            if course.description_zh and term_lower in course.description_zh.lower():
                score += self.weights["description"]
            if course.description_en and term_lower in course.description_en.lower():
                score += self.weights["description"]
            
            # Tag matches
            if hasattr(course, 'tags') and course.tags:
                for tag in course.tags:
                    if term_lower in tag.lower():
                        score += self.weights["tags"]
        
        # Boost for exact matches
        full_query = " ".join(search_terms).lower()
        if full_query in course.title_zh.lower() or full_query in course.title_en.lower():
            score *= 2
        
        # Boost for required courses
        if course.is_required:
            score *= 1.2
        
        return score
    
    async def _get_user_enrollment(self, user_id: str, course_id: str):
        """Get user's enrollment for a course."""
        from app.models.training import Enrollment
        
        query = select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_search_suggestions(
        self,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """Get search suggestions based on prefix."""
        if len(prefix) < 2:
            return []
        
        # In a real implementation, this would use a search index
        # or a dedicated suggestion service
        
        # For now, return popular search terms
        suggestions = [
            "安全培訓",
            "客戶服務",
            "配送流程",
            "系統操作",
            "緊急應變",
            "新人訓練",
            "進階課程",
            "法規遵循"
        ]
        
        # Filter by prefix
        filtered = [s for s in suggestions if s.startswith(prefix)]
        
        return filtered[:limit]
    
    async def index_course(self, course: Course):
        """Index or update course in search index."""
        # In a real implementation, this would update
        # Elasticsearch, Algolia, or PostgreSQL full-text index
        pass
    
    async def remove_from_index(self, entity_type: str, entity_id: str):
        """Remove entity from search index."""
        # Clear relevant caches
        await cache_service.delete_by_tags([f"search:{entity_type}"])


# Utility functions for search
def highlight_search_terms(text: str, search_terms: List[str]) -> str:
    """Highlight search terms in text."""
    highlighted = text
    
    for term in search_terms:
        # Case-insensitive replacement with highlight
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        highlighted = pattern.sub(f"<mark>{term}</mark>", highlighted)
    
    return highlighted


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text for indexing."""
    # Simple keyword extraction
    # In production, use TF-IDF or more advanced NLP
    
    # Remove common words (stopwords)
    stopwords = {"的", "是", "在", "和", "了", "與", "及", "the", "is", "at", "and"}
    
    # Split and clean
    words = re.findall(r'\w+', text.lower())
    
    # Filter and count
    word_counts = {}
    for word in words:
        if len(word) > 1 and word not in stopwords:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Sort by frequency
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return top keywords
    return [word for word, count in sorted_words[:max_keywords]]