from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.models.training import Course, Module, Enrollment, Progress, Achievement
from app.models.user import User
from app.schemas.training import (
    CourseResponse, CourseCreate, CourseUpdate,
    ModuleResponse, EnrollmentResponse, ProgressUpdate
)
from app.api.deps import get_current_user, require_role
from app.core.cache import cache
from app.services.achievement_service import AchievementService

router = APIRouter()

@router.get("/", response_model=List[CourseResponse])
async def get_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    department: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available courses with filtering."""
    query = select(Course).where(Course.is_active == True)
    
    if department:
        query = query.where(Course.department == department)
    if difficulty:
        query = query.where(Course.difficulty == difficulty)
    if search:
        query = query.where(
            func.lower(Course.title_zh).contains(search.lower()) |
            func.lower(Course.title_en).contains(search.lower())
        )
    
    # Add user-specific filters based on role
    if not current_user.is_admin:
        query = query.where(Course.department.in_(current_user.departments))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    courses = result.scalars().all()
    
    # Add enrollment status for each course
    enrollment_query = select(Enrollment).where(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id.in_([c.course_id for c in courses])
    )
    enrollment_result = await db.execute(enrollment_query)
    enrollments = {e.course_id: e for e in enrollment_result.scalars().all()}
    
    response = []
    for course in courses:
        course_dict = course.__dict__.copy()
        enrollment = enrollments.get(course.course_id)
        course_dict['enrollment_status'] = enrollment.status if enrollment else None
        course_dict['progress_percentage'] = enrollment.progress_percentage if enrollment else 0
        response.append(CourseResponse(**course_dict))
    
    return response

@router.get("/{course_id}", response_model=CourseResponse)
@cache(expire=300)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed course information."""
    query = select(Course).where(
        Course.course_id == course_id,
        Course.is_active == True
    )
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check access permissions
    if not current_user.is_admin and course.department not in current_user.departments:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get modules
    module_query = select(Module).where(
        Module.course_id == course_id,
        Module.is_active == True
    ).order_by(Module.order_index)
    module_result = await db.execute(module_query)
    modules = module_result.scalars().all()
    
    # Get user's enrollment and progress
    enrollment_query = select(Enrollment).where(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id
    )
    enrollment_result = await db.execute(enrollment_query)
    enrollment = enrollment_result.scalar_one_or_none()
    
    # Build response
    course_data = course.__dict__.copy()
    course_data['modules'] = [ModuleResponse.from_orm(m) for m in modules]
    course_data['total_modules'] = len(modules)
    course_data['enrollment_status'] = enrollment.status if enrollment else None
    course_data['progress_percentage'] = enrollment.progress_percentage if enrollment else 0
    
    return CourseResponse(**course_data)

@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enroll current user in a course."""
    # Check if course exists
    course_query = select(Course).where(
        Course.course_id == course_id,
        Course.is_active == True
    )
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check access permissions
    if not current_user.is_admin and course.department not in current_user.departments:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already enrolled
    existing_query = select(Enrollment).where(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        if existing.status == "completed":
            raise HTTPException(status_code=400, detail="Course already completed")
        return EnrollmentResponse.from_orm(existing)
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=course_id,
        enrolled_at=datetime.utcnow()
    )
    db.add(enrollment)
    
    # Award enrollment achievement
    achievement_service = AchievementService(db)
    await achievement_service.check_enrollment_achievements(current_user.id)
    
    await db.commit()
    await db.refresh(enrollment)
    
    return EnrollmentResponse.from_orm(enrollment)

@router.put("/{course_id}/modules/{module_id}/progress", response_model=dict)
async def update_module_progress(
    course_id: UUID,
    module_id: UUID,
    progress_update: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's progress on a module."""
    # Verify enrollment
    enrollment_query = select(Enrollment).where(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id,
        Enrollment.status == "enrolled"
    )
    enrollment_result = await db.execute(enrollment_query)
    enrollment = enrollment_result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")
    
    # Get or create progress record
    progress_query = select(Progress).where(
        Progress.user_id == current_user.id,
        Progress.module_id == module_id
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalar_one_or_none()
    
    if not progress:
        progress = Progress(
            user_id=current_user.id,
            module_id=module_id,
            enrollment_id=enrollment.enrollment_id
        )
        db.add(progress)
    
    # Update progress
    progress.progress_percentage = progress_update.progress_percentage
    progress.time_spent_minutes = progress_update.time_spent_minutes
    progress.last_accessed = datetime.utcnow()
    
    if progress_update.progress_percentage >= 100 and not progress.completed_at:
        progress.completed_at = datetime.utcnow()
        progress.passed = True
        
        # Award completion points
        points_awarded = 50  # Base points for module completion
        if progress_update.quiz_score:
            progress.quiz_score = progress_update.quiz_score
            if progress_update.quiz_score >= 80:
                points_awarded += 20  # Bonus for high quiz score
        
        # Update user points
        current_user.points = (current_user.points or 0) + points_awarded
        
        # Check for achievements
        achievement_service = AchievementService(db)
        await achievement_service.check_module_achievements(current_user.id, module_id)
    
    # Update enrollment progress
    await update_enrollment_progress(db, enrollment)
    
    await db.commit()
    
    return {
        "progress_percentage": progress.progress_percentage,
        "completed": progress.completed_at is not None,
        "points_earned": points_awarded if progress.completed_at else 0
    }

async def update_enrollment_progress(db: AsyncSession, enrollment: Enrollment):
    """Calculate and update overall course progress."""
    # Get all modules in the course
    module_query = select(Module).where(
        Module.course_id == enrollment.course_id,
        Module.is_active == True
    )
    module_result = await db.execute(module_query)
    modules = module_result.scalars().all()
    total_modules = len(modules)
    
    if total_modules == 0:
        return
    
    # Get completed modules
    progress_query = select(func.count(Progress.progress_id)).where(
        Progress.enrollment_id == enrollment.enrollment_id,
        Progress.completed_at.isnot(None)
    )
    progress_result = await db.execute(progress_query)
    completed_modules = progress_result.scalar()
    
    # Update enrollment progress
    enrollment.progress_percentage = (completed_modules / total_modules) * 100
    enrollment.modules_completed = completed_modules
    enrollment.last_accessed = datetime.utcnow()
    
    # Check if course is completed
    if enrollment.progress_percentage >= 100:
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
        
        # Award course completion achievement
        achievement_service = AchievementService(db)
        await achievement_service.check_course_achievements(
            enrollment.user_id, 
            enrollment.course_id
        )

@router.post("/", response_model=CourseResponse)
@require_role(["admin", "training_manager"])
async def create_course(
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new course (admin/training manager only)."""
    # Check if course with same title exists
    existing_query = select(Course).where(
        func.lower(Course.title_zh) == course_data.title_zh.lower()
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Course with this title already exists")
    
    course = Course(**course_data.dict())
    course.created_by = current_user.id
    
    db.add(course)
    await db.commit()
    await db.refresh(course)
    
    return CourseResponse.from_orm(course)

@router.put("/{course_id}", response_model=CourseResponse)
@require_role(["admin", "training_manager"])
async def update_course(
    course_id: UUID,
    course_update: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update course details (admin/training manager only)."""
    query = select(Course).where(Course.course_id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Update fields
    update_data = course_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
    
    course.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(course)
    
    # Invalidate cache
    await cache.delete(f"course:{course_id}")
    
    return CourseResponse.from_orm(course)

@router.delete("/{course_id}")
@require_role(["admin"])
async def delete_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a course (admin only)."""
    query = select(Course).where(Course.course_id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if there are active enrollments
    enrollment_query = select(func.count(Enrollment.enrollment_id)).where(
        Enrollment.course_id == course_id,
        Enrollment.status == "enrolled"
    )
    enrollment_result = await db.execute(enrollment_query)
    active_enrollments = enrollment_result.scalar()
    
    if active_enrollments > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete course with {active_enrollments} active enrollments"
        )
    
    course.is_active = False
    course.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Invalidate cache
    await cache.delete(f"course:{course_id}")
    
    return {"message": "Course deleted successfully"}