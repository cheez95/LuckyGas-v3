"""
Custom Prometheus metrics for Lucky Gas monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info, Summary
from app.core.config import settings

# Business metrics
prediction_counter = Counter(
    'lucky_gas_predictions_total',
    'Total number of predictions generated',
    ['customer_type', 'status']
)

route_optimization_histogram = Histogram(
    'lucky_gas_route_optimization_duration_seconds',
    'Time spent optimizing routes',
    ['method', 'num_stops'],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120)
)

active_deliveries_gauge = Gauge(
    'lucky_gas_active_deliveries',
    'Number of active deliveries',
    ['area', 'driver']
)

orders_created_counter = Counter(
    'lucky_gas_orders_created_total',
    'Total number of orders created',
    ['order_type', 'customer_type']
)

cache_operations_counter = Counter(
    'lucky_gas_cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status']
)

background_tasks_counter = Counter(
    'lucky_gas_background_tasks_total',
    'Total number of background tasks',
    ['task_type', 'status']
)

# Business KPIs
revenue_counter = Counter(
    'lucky_gas_revenue_total',
    'Total revenue in TWD',
    ['payment_method', 'customer_type']
)

cylinders_delivered_counter = Counter(
    'lucky_gas_cylinders_delivered_total',
    'Total number of cylinders delivered',
    ['size', 'area']
)

customer_satisfaction_gauge = Gauge(
    'lucky_gas_customer_satisfaction_score',
    'Customer satisfaction score (1-5)',
    ['area', 'customer_type']
)

delivery_time_histogram = Histogram(
    'lucky_gas_delivery_time_seconds',
    'Time from order to delivery',
    ['area', 'is_urgent'],
    buckets=(3600, 7200, 14400, 28800, 43200, 86400)  # 1h, 2h, 4h, 8h, 12h, 24h
)

# API Performance metrics
api_request_counter = Counter(
    'lucky_gas_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration_histogram = Histogram(
    'lucky_gas_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
)

# Database performance
db_query_counter = Counter(
    'lucky_gas_db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

db_query_duration_histogram = Histogram(
    'lucky_gas_db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1)
)

db_connection_pool_gauge = Gauge(
    'lucky_gas_db_connection_pool_size',
    'Database connection pool status',
    ['status']  # active, idle, overflow
)

# Authentication & Security
auth_attempts_counter = Counter(
    'lucky_gas_auth_attempts_total',
    'Total authentication attempts',
    ['result', 'method']
)

active_sessions_gauge = Gauge(
    'lucky_gas_active_sessions',
    'Number of active user sessions',
    ['role']
)

# Inventory metrics
inventory_gauge = Gauge(
    'lucky_gas_inventory_cylinders',
    'Current cylinder inventory',
    ['size', 'location', 'status']
)

low_inventory_alerts_counter = Counter(
    'lucky_gas_low_inventory_alerts_total',
    'Low inventory alerts triggered',
    ['size', 'location']
)

# Driver performance
driver_deliveries_counter = Counter(
    'lucky_gas_driver_deliveries_total',
    'Total deliveries by driver',
    ['driver_id', 'status']
)

driver_efficiency_gauge = Gauge(
    'lucky_gas_driver_efficiency_score',
    'Driver efficiency score (deliveries per hour)',
    ['driver_id']
)

# Error tracking
error_counter = Counter(
    'lucky_gas_errors_total',
    'Total errors',
    ['error_type', 'severity', 'component']
)

# External service metrics
google_api_calls_counter = Counter(
    'lucky_gas_google_api_calls_total',
    'Google API calls',
    ['api_type', 'status']
)

google_api_latency_histogram = Histogram(
    'lucky_gas_google_api_latency_seconds',
    'Google API call latency',
    ['api_type'],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10)
)

# WebSocket metrics
websocket_connections_gauge = Gauge(
    'lucky_gas_websocket_connections',
    'Active WebSocket connections',
    ['client_type']
)

websocket_messages_counter = Counter(
    'lucky_gas_websocket_messages_total',
    'WebSocket messages sent/received',
    ['direction', 'message_type']
)

# System info
system_info = Info(
    'lucky_gas_system',
    'Lucky Gas system information'
)
system_info.info({
    'version': '1.0.0',
    'environment': settings.ENVIRONMENT.value,
    'framework': 'FastAPI',
    'project': settings.PROJECT_NAME
})