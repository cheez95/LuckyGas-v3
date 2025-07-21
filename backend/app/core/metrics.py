"""
Custom Prometheus metrics for Lucky Gas monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info

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

# System info
system_info = Info(
    'lucky_gas_system',
    'Lucky Gas system information'
)
system_info.info({
    'version': '1.0.0',
    'environment': 'production',
    'framework': 'FastAPI'
})