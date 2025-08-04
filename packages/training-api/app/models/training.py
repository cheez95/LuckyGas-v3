from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Text, 
    ForeignKey, Table, JSON, ARRAY, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ModuleType(str, enum.Enum):
    VIDEO = "video"
    READING = "reading"
    QUIZ = "quiz"
    EXERCISE = "exercise"
    DISCUSSION = "discussion"


class AssessmentType(str, enum.Enum):
    QUIZ = "quiz"
    EXAM = "exam"
    ASSIGNMENT = "assignment"
    PRACTICAL = "practical"


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    MATCHING = "matching"


# Association tables
learning_path_courses = Table(
    'learning_path_courses',
    Base.metadata,
    Column('path_id', UUID(as_uuid=True), ForeignKey('learning_paths.path_id', ondelete='CASCADE')),
    Column('course_id', UUID(as_uuid=True), ForeignKey('courses.course_id', ondelete='CASCADE')),
    Column('order_index', Integer, nullable=False),
    Column('is_mandatory', Boolean, default=True),
    Column('days_to_complete', Integer),
    UniqueConstraint('path_id', 'order_index')
)


class TrainingProfile(Base):
    """Extended user profile for training."""
    __tablename__ = 'training_profiles'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    language_preference = Column(String(10), default='zh-TW')
    learning_style = Column(String(20), default='mixed')
    onboarding_completed = Column(Boolean, default=False)
    total_learning_hours = Column(Float, default=0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    level = Column(Integer, default=1)
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    enrollments = relationship("Enrollment", back_populates="profile")
    achievements = relationship("UserAchievement", back_populates="profile")
    activities = relationship("LearningActivity", back_populates="profile")
    notifications = relationship("TrainingNotification", back_populates="profile")


class Course(Base):
    """Training course definition."""
    __tablename__ = 'courses'
    
    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(JSONB, nullable=False)  # {"zh-TW": "課程名稱", "en": "Course Title"}
    description = Column(JSONB, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    subcategory = Column(String(50))
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    pass_percentage = Column(Integer, default=80)
    max_attempts = Column(Integer, default=3)
    valid_days = Column(Integer, default=365)
    tags = Column(ARRAY(Text), default=[])
    prerequisites = Column(ARRAY(UUID(as_uuid=True)), default=[])
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")
    feedback = relationship("CourseFeedback", back_populates="course")
    
    # Indexes
    __table_args__ = (
        Index('idx_courses_category_difficulty', 'category', 'difficulty'),
        Index('idx_courses_active_created', 'is_active', 'created_at'),
    )


class Module(Base):
    """Course module/lesson."""
    __tablename__ = 'modules'
    
    module_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    title = Column(JSONB, nullable=False)
    type = Column(SQLEnum(ModuleType), nullable=False)
    content_url = Column(String(500))
    duration_minutes = Column(Integer)
    order_index = Column(Integer, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    pass_percentage = Column(Integer)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="modules")
    progress = relationship("ModuleProgress", back_populates="module")
    assessments = relationship("Assessment", back_populates="module")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('course_id', 'order_index'),
    )


class LearningPath(Base):
    """Role-specific learning sequences."""
    __tablename__ = 'learning_paths'
    
    path_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(JSONB, nullable=False)
    description = Column(JSONB, nullable=False)
    target_role = Column(String(50), nullable=False, index=True)
    is_mandatory = Column(Boolean, default=False)
    estimated_hours = Column(Integer)
    validity_days = Column(Integer)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    courses = relationship("Course", secondary=learning_path_courses, backref="learning_paths")
    enrollments = relationship("Enrollment", back_populates="learning_path")


class Enrollment(Base):
    """User course enrollment."""
    __tablename__ = 'enrollments'
    
    enrollment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id'), nullable=False)
    path_id = Column(UUID(as_uuid=True), ForeignKey('learning_paths.path_id'))
    enrolled_date = Column(DateTime, server_default=func.now())
    start_date = Column(DateTime)
    due_date = Column(DateTime)
    completed_date = Column(DateTime)
    status = Column(SQLEnum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED)
    progress_percentage = Column(Float, default=0)
    final_score = Column(Float)
    attempt_count = Column(Integer, default=0)
    completion_certificate_id = Column(UUID(as_uuid=True))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    profile = relationship("TrainingProfile", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    learning_path = relationship("LearningPath", back_populates="enrollments")
    module_progress = relationship("ModuleProgress", back_populates="enrollment", cascade="all, delete-orphan")
    assessment_attempts = relationship("AssessmentAttempt", back_populates="enrollment")
    certificate = relationship("Certificate", back_populates="enrollment", uselist=False)
    feedback = relationship("CourseFeedback", back_populates="enrollment", uselist=False)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id'),
        Index('idx_enrollments_user_status', 'user_id', 'status'),
        Index('idx_enrollments_course', 'course_id'),
    )


class ModuleProgress(Base):
    """Detailed progress tracking per module."""
    __tablename__ = 'module_progress'
    
    progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('enrollments.enrollment_id', ondelete='CASCADE'), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey('modules.module_id'), nullable=False)
    status = Column(String(20), default='not_started')
    progress_percentage = Column(Float, default=0)
    time_spent_minutes = Column(Integer, default=0)
    last_position = Column(Integer)  # For videos: seconds, for documents: page
    completed_date = Column(DateTime)
    score = Column(Float)
    attempts = Column(Integer, default=0)
    notes = Column(Text)
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="module_progress")
    module = relationship("Module", back_populates="progress")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('enrollment_id', 'module_id'),
        Index('idx_module_progress_enrollment', 'enrollment_id'),
    )


class Assessment(Base):
    """Quiz, exam, or practical assessment."""
    __tablename__ = 'assessments'
    
    assessment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id'))
    module_id = Column(UUID(as_uuid=True), ForeignKey('modules.module_id'))
    title = Column(JSONB, nullable=False)
    type = Column(SQLEnum(AssessmentType), nullable=False)
    time_limit_minutes = Column(Integer)
    pass_percentage = Column(Integer, default=80)
    max_attempts = Column(Integer, default=3)
    randomize_questions = Column(Boolean, default=True)
    show_answers_after = Column(Boolean, default=True)
    question_count = Column(Integer)
    total_points = Column(Integer)
    instructions = Column(JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="assessments")
    module = relationship("Module", back_populates="assessments")
    questions = relationship("Question", back_populates="assessment", cascade="all, delete-orphan")
    attempts = relationship("AssessmentAttempt", back_populates="assessment")


class Question(Base):
    """Assessment question bank."""
    __tablename__ = 'questions'
    
    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey('assessments.assessment_id', ondelete='CASCADE'), nullable=False)
    question_text = Column(JSONB, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    options = Column(JSONB)  # For multiple choice
    correct_answer = Column(JSONB)
    points = Column(Integer, default=1)
    explanation = Column(JSONB)
    difficulty = Column(String(20))
    tags = Column(ARRAY(Text), default=[])
    media_url = Column(String(500))
    order_index = Column(Integer)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="questions")


class AssessmentAttempt(Base):
    """User assessment attempts."""
    __tablename__ = 'assessment_attempts'
    
    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('enrollments.enrollment_id'), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey('assessments.assessment_id'), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    started_at = Column(DateTime, server_default=func.now())
    submitted_at = Column(DateTime)
    time_taken_minutes = Column(Integer)
    score = Column(Float)
    passed = Column(Boolean)
    answers = Column(JSONB)
    feedback = Column(JSONB)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="assessment_attempts")
    assessment = relationship("Assessment", back_populates="attempts")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('enrollment_id', 'assessment_id', 'attempt_number'),
        Index('idx_assessment_attempts_enrollment', 'enrollment_id'),
    )


class Certificate(Base):
    """Course completion certificates."""
    __tablename__ = 'certificates'
    
    certificate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('enrollments.enrollment_id'), unique=True)
    certificate_number = Column(String(50), unique=True, nullable=False)
    issued_date = Column(Date, server_default=func.current_date())
    expiry_date = Column(Date)
    pdf_url = Column(String(500))
    verification_code = Column(String(50), unique=True, nullable=False, index=True)
    metadata = Column(JSONB, default={})
    revoked = Column(Boolean, default=False)
    revoked_reason = Column(Text)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    revoked_at = Column(DateTime)
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="certificate")


class LearningActivity(Base):
    """Detailed activity tracking."""
    __tablename__ = 'learning_activities'
    
    activity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    activity_type = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))
    action = Column(String(50), nullable=False)
    duration_seconds = Column(Integer)
    metadata = Column(JSONB, default={})
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    profile = relationship("TrainingProfile", back_populates="activities")
    
    # Indexes
    __table_args__ = (
        Index('idx_learning_activities_user_date', 'user_id', 'created_at'),
    )


class CourseFeedback(Base):
    """Course ratings and feedback."""
    __tablename__ = 'course_feedback'
    
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('enrollments.enrollment_id'), unique=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id'), nullable=False)
    rating = Column(Integer, nullable=False)
    comments = Column(Text)
    would_recommend = Column(Boolean)
    tags = Column(ARRAY(Text), default=[])
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="feedback")
    course = relationship("Course", back_populates="feedback")
    
    # Constraints
    __table_args__ = (
        Index('idx_course_feedback_rating', 'course_id', 'rating'),
    )


class Achievement(Base):
    """Gamification achievements."""
    __tablename__ = 'achievements'
    
    achievement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(JSONB, nullable=False)
    description = Column(JSONB, nullable=False)
    type = Column(String(50), nullable=False)
    criteria = Column(JSONB, nullable=False)  # {"type": "course_completion", "count": 5}
    points = Column(Integer, default=0)
    badge_image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """User earned achievements."""
    __tablename__ = 'user_achievements'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey('achievements.achievement_id'), primary_key=True)
    earned_date = Column(DateTime, server_default=func.now())
    progress = Column(JSONB, default={})
    
    # Relationships
    profile = relationship("TrainingProfile", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


class TrainingNotification(Base):
    """Training-specific notifications."""
    __tablename__ = 'training_notifications'
    
    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(String(500))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    priority = Column(String(20), default='normal')
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    profile = relationship("TrainingProfile", back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        Index('idx_training_notifications_user', 'user_id', 'is_read', 'created_at'),
    )