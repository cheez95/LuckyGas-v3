from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    training,
    courses,
    assessments,
    certificates,
    analytics,
    team,
    practice,
    notifications,
    profile
)

api_router = APIRouter()

# Auth endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Training endpoints
api_router.include_router(training.router, prefix="/training", tags=["Training"])

# Course endpoints
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])

# Assessment endpoints
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])

# Certificate endpoints
api_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])

# Analytics endpoints
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# Team management endpoints
api_router.include_router(team.router, prefix="/team", tags=["Team Management"])

# Practice environment endpoints
api_router.include_router(practice.router, prefix="/practice", tags=["Practice Environment"])

# Notification endpoints
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# Profile endpoints
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])