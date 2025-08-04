from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from functools import wraps
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute

# Define metrics
REQUEST_COUNT = Counter(
    'training_api_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'training_api_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_USERS = Gauge(
    'training_active_users',
    'Number of currently active users'
)

WEBSOCKET_CONNECTIONS = Gauge(
    'training_websocket_connections',
    'Number of active WebSocket connections'
)

ENROLLMENTS = Counter(
    'training_enrollments_total',
    'Total number of course enrollments',
    ['course_id', 'department']
)

COMPLETIONS = Counter(
    'training_completions_total',
    'Total number of course completions',
    ['course_id', 'department']
)

VIDEO_VIEWS = Counter(
    'training_video_views_total',
    'Total number of video views',
    ['course_id', 'module_id']
)

ACHIEVEMENTS_EARNED = Counter(
    'training_achievements_earned_total',
    'Total number of achievements earned',
    ['achievement_type', 'department']
)

QUIZ_SUBMISSIONS = Counter(
    'training_quiz_submissions_total',
    'Total number of quiz submissions',
    ['course_id', 'module_id', 'passed']
)

AVERAGE_PROGRESS = Gauge(
    'training_average_progress',
    'Average progress percentage across all active enrollments'
)

COMPLETION_RATE = Gauge(
    'training_completion_rate',
    'Overall course completion rate percentage'
)

LEARNING_HOURS = Counter(
    'training_learning_hours_total',
    'Total learning hours logged',
    ['department']
)

API_INFO = Info(
    'training_api',
    'Training API information'
)

# Set API info
API_INFO.info({
    'version': '1.0.0',
    'environment': 'production'
})

# Metrics collection decorator
def track_request_metrics(func: Callable) -> Callable:
    """Decorator to track request metrics."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        start_time = time.time()
        
        # Get endpoint path
        endpoint = request.url.path
        method = request.method
        
        try:
            response = await func(request, *args, **kwargs)
            status = response.status_code if hasattr(response, 'status_code') else 200
        except Exception as e:
            status = 500
            raise e
        finally:
            # Track metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(time.time() - start_time)
        
        return response
    
    return wrapper

# Prometheus metrics endpoint
async def metrics_endpoint(request: Request) -> Response:
    """Return Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# Custom API route class with metrics
class MetricsRoute(APIRoute):
    """Custom route class that tracks metrics."""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def metrics_route_handler(request: Request) -> Response:
            start_time = time.time()
            
            # Get endpoint info
            endpoint = self.path
            method = request.method
            
            try:
                response = await original_route_handler(request)
                status = response.status_code
            except Exception as e:
                status = 500
                raise e
            finally:
                # Track metrics
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()
                
                REQUEST_DURATION.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(time.time() - start_time)
            
            return response
        
        return metrics_route_handler

# Utility functions for updating business metrics
def track_enrollment(course_id: str, department: str):
    """Track new course enrollment."""
    ENROLLMENTS.labels(
        course_id=course_id,
        department=department
    ).inc()

def track_completion(course_id: str, department: str):
    """Track course completion."""
    COMPLETIONS.labels(
        course_id=course_id,
        department=department
    ).inc()

def track_video_view(course_id: str, module_id: str):
    """Track video view."""
    VIDEO_VIEWS.labels(
        course_id=course_id,
        module_id=module_id
    ).inc()

def track_achievement(achievement_type: str, department: str):
    """Track achievement earned."""
    ACHIEVEMENTS_EARNED.labels(
        achievement_type=achievement_type,
        department=department
    ).inc()

def track_quiz_submission(course_id: str, module_id: str, passed: bool):
    """Track quiz submission."""
    QUIZ_SUBMISSIONS.labels(
        course_id=course_id,
        module_id=module_id,
        passed=str(passed)
    ).inc()

def track_learning_time(department: str, hours: float):
    """Track learning time."""
    LEARNING_HOURS.labels(department=department).inc(hours)

def update_active_users(count: int):
    """Update active users gauge."""
    ACTIVE_USERS.set(count)

def update_websocket_connections(count: int):
    """Update WebSocket connections gauge."""
    WEBSOCKET_CONNECTIONS.set(count)

def update_average_progress(percentage: float):
    """Update average progress gauge."""
    AVERAGE_PROGRESS.set(percentage)

def update_completion_rate(percentage: float):
    """Update completion rate gauge."""
    COMPLETION_RATE.set(percentage)

# Background task to update gauges
async def update_metrics_task(db_session):
    """Background task to update gauge metrics."""
    from app.services.analytics_service import AnalyticsService
    
    while True:
        try:
            analytics = AnalyticsService(db_session)
            
            # Get dashboard metrics
            metrics = await analytics.get_dashboard_metrics()
            
            # Update gauges
            update_active_users(metrics.get('active_learners', 0))
            update_average_progress(metrics.get('average_completion_rate', 0))
            
            # Calculate and update completion rate
            if metrics.get('total_enrollments', 0) > 0:
                completion_rate = (
                    metrics.get('total_completions', 0) / 
                    metrics.get('total_enrollments', 1) * 100
                )
                update_completion_rate(completion_rate)
            
            # Update WebSocket connections from manager
            from app.core.websocket import manager
            update_websocket_connections(manager.get_online_count())
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        # Update every 60 seconds
        await asyncio.sleep(60)