"""
Google Cloud Monitoring configuration for Lucky Gas application.

This module defines custom metrics, logging, and monitoring setup.
"""

import os
import logging
from typing import Dict, List, Optional
from google.cloud import monitoring_v3
from google.cloud import logging as cloud_logging
from prometheus_client import Counter, Histogram, Gauge, Info
import time


# Initialize logging
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and exports metrics to Google Cloud Monitoring."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize the metrics collector."""
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.client = monitoring_v3.MetricServiceClient()
        self.project_path = f"projects/{self.project_id}"
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Initialize Cloud Logging
        self._init_cloud_logging()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics for local collection."""
        # Request metrics
        self.request_count = Counter(
            'luckygas_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'luckygas_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
        )
        
        # Business metrics
        self.orders_created = Counter(
            'luckygas_orders_created_total',
            'Total number of orders created',
            ['order_type', 'customer_type']
        )
        
        self.deliveries_completed = Counter(
            'luckygas_deliveries_completed_total',
            'Total number of deliveries completed',
            ['driver_id', 'zone']
        )
        
        self.revenue = Counter(
            'luckygas_revenue_total',
            'Total revenue in TWD',
            ['product_type', 'payment_method']
        )
        
        # System metrics
        self.active_users = Gauge(
            'luckygas_active_users',
            'Number of active users',
            ['user_type']
        )
        
        self.cache_hit_rate = Gauge(
            'luckygas_cache_hit_rate',
            'Cache hit rate percentage'
        )
        
        self.prediction_accuracy = Gauge(
            'luckygas_prediction_accuracy',
            'ML prediction accuracy percentage'
        )
        
        # Route optimization metrics
        self.route_optimization_time = Histogram(
            'luckygas_route_optimization_seconds',
            'Time taken for route optimization',
            buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60)
        )
        
        self.route_efficiency = Gauge(
            'luckygas_route_efficiency',
            'Route efficiency percentage'
        )
        
        # Google API metrics
        self.google_api_calls = Counter(
            'luckygas_google_api_calls_total',
            'Total Google API calls',
            ['api_name', 'status']
        )
        
        self.google_api_cost = Counter(
            'luckygas_google_api_cost_usd',
            'Google API cost in USD',
            ['api_name']
        )
        
        # Application info
        self.app_info = Info(
            'luckygas_app',
            'Application information'
        )
        self.app_info.info({
            'version': os.getenv('APP_VERSION', 'unknown'),
            'environment': os.getenv('ENVIRONMENT', 'development')
        })
    
    def _init_cloud_logging(self):
        """Initialize Google Cloud Logging."""
        try:
            self.logging_client = cloud_logging.Client(project=self.project_id)
            self.logging_client.setup_logging()
            logger.info("Cloud Logging initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Cloud Logging: {e}")
            self.logging_client = None
    
    def create_custom_metrics(self):
        """Create custom metric descriptors in Google Cloud Monitoring."""
        metrics_to_create = [
            {
                'type': 'custom.googleapis.com/luckygas/orders/created',
                'display_name': 'Orders Created',
                'description': 'Number of orders created',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.INT64,
                'labels': [
                    {'key': 'order_type', 'value_type': 'STRING'},
                    {'key': 'customer_type', 'value_type': 'STRING'}
                ]
            },
            {
                'type': 'custom.googleapis.com/luckygas/deliveries/completed',
                'display_name': 'Deliveries Completed',
                'description': 'Number of deliveries completed',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.INT64,
                'labels': [
                    {'key': 'driver_id', 'value_type': 'STRING'},
                    {'key': 'zone', 'value_type': 'STRING'}
                ]
            },
            {
                'type': 'custom.googleapis.com/luckygas/revenue/total',
                'display_name': 'Total Revenue',
                'description': 'Total revenue in TWD',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.DOUBLE,
                'labels': [
                    {'key': 'product_type', 'value_type': 'STRING'},
                    {'key': 'payment_method', 'value_type': 'STRING'}
                ]
            },
            {
                'type': 'custom.googleapis.com/luckygas/route/optimization_time',
                'display_name': 'Route Optimization Time',
                'description': 'Time taken for route optimization in seconds',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.GAUGE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.DOUBLE
            },
            {
                'type': 'custom.googleapis.com/luckygas/route/efficiency',
                'display_name': 'Route Efficiency',
                'description': 'Route efficiency percentage',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.GAUGE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.DOUBLE
            },
            {
                'type': 'custom.googleapis.com/luckygas/prediction/accuracy',
                'display_name': 'Prediction Accuracy',
                'description': 'ML prediction accuracy percentage',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.GAUGE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.DOUBLE
            },
            {
                'type': 'custom.googleapis.com/luckygas/cache/hit_rate',
                'display_name': 'Cache Hit Rate',
                'description': 'Cache hit rate percentage',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.GAUGE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.DOUBLE
            },
            {
                'type': 'custom.googleapis.com/luckygas/google_api/calls',
                'display_name': 'Google API Calls',
                'description': 'Number of Google API calls',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.INT64,
                'labels': [
                    {'key': 'api_name', 'value_type': 'STRING'},
                    {'key': 'status', 'value_type': 'STRING'}
                ]
            },
            {
                'type': 'custom.googleapis.com/luckygas/google_api/cost',
                'display_name': 'Google API Cost',
                'description': 'Google API cost in USD',
                'metric_kind': monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE,
                'value_type': monitoring_v3.MetricDescriptor.ValueType.DOUBLE,
                'labels': [
                    {'key': 'api_name', 'value_type': 'STRING'}
                ]
            }
        ]
        
        for metric_def in metrics_to_create:
            try:
                descriptor = monitoring_v3.MetricDescriptor()
                descriptor.type = metric_def['type']
                descriptor.display_name = metric_def['display_name']
                descriptor.description = metric_def['description']
                descriptor.metric_kind = metric_def['metric_kind']
                descriptor.value_type = metric_def['value_type']
                
                if 'labels' in metric_def:
                    for label in metric_def['labels']:
                        label_descriptor = monitoring_v3.LabelDescriptor()
                        label_descriptor.key = label['key']
                        label_descriptor.value_type = label['value_type']
                        descriptor.labels.append(label_descriptor)
                
                self.client.create_metric_descriptor(
                    name=self.project_path,
                    metric_descriptor=descriptor
                )
                logger.info(f"Created custom metric: {metric_def['type']}")
                
            except Exception as e:
                # Metric might already exist
                logger.debug(f"Could not create metric {metric_def['type']}: {e}")
    
    def write_time_series(self, metric_type: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Write a time series data point to Cloud Monitoring."""
        try:
            series = monitoring_v3.TimeSeries()
            series.metric.type = metric_type
            
            if labels:
                for key, val in labels.items():
                    series.metric.labels[key] = val
            
            # Resource type and labels
            series.resource.type = 'global'
            
            # Create a data point
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10 ** 9)
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            point = monitoring_v3.Point({
                "interval": interval,
                "value": {"double_value": value}
            })
            series.points.append(point)
            
            # Write the time series
            self.client.create_time_series(
                name=self.project_path,
                time_series=[series]
            )
            
        except Exception as e:
            logger.error(f"Failed to write metric {metric_type}: {e}")
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record an HTTP request metric."""
        # Update Prometheus metrics
        self.request_count.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        
        # Optionally write to Cloud Monitoring
        if self.project_id:
            self.write_time_series(
                'custom.googleapis.com/luckygas/request/duration',
                duration,
                {'method': method, 'endpoint': endpoint}
            )
    
    def record_order_created(self, order_type: str, customer_type: str):
        """Record an order creation."""
        self.orders_created.labels(order_type=order_type, customer_type=customer_type).inc()
        
        if self.project_id:
            self.write_time_series(
                'custom.googleapis.com/luckygas/orders/created',
                1,
                {'order_type': order_type, 'customer_type': customer_type}
            )
    
    def record_delivery_completed(self, driver_id: str, zone: str):
        """Record a delivery completion."""
        self.deliveries_completed.labels(driver_id=driver_id, zone=zone).inc()
        
        if self.project_id:
            self.write_time_series(
                'custom.googleapis.com/luckygas/deliveries/completed',
                1,
                {'driver_id': driver_id, 'zone': zone}
            )
    
    def record_revenue(self, amount: float, product_type: str, payment_method: str):
        """Record revenue."""
        self.revenue.labels(product_type=product_type, payment_method=payment_method).inc(amount)
        
        if self.project_id:
            self.write_time_series(
                'custom.googleapis.com/luckygas/revenue/total',
                amount,
                {'product_type': product_type, 'payment_method': payment_method}
            )
    
    def set_cache_hit_rate(self, rate: float):
        """Set the cache hit rate."""
        self.cache_hit_rate.set(rate)
        
        if self.project_id:
            self.write_time_series('custom.googleapis.com/luckygas/cache/hit_rate', rate)
    
    def set_prediction_accuracy(self, accuracy: float):
        """Set the prediction accuracy."""
        self.prediction_accuracy.set(accuracy)
        
        if self.project_id:
            self.write_time_series('custom.googleapis.com/luckygas/prediction/accuracy', accuracy)
    
    def record_route_optimization(self, duration: float, efficiency: float):
        """Record route optimization metrics."""
        self.route_optimization_time.observe(duration)
        self.route_efficiency.set(efficiency)
        
        if self.project_id:
            self.write_time_series('custom.googleapis.com/luckygas/route/optimization_time', duration)
            self.write_time_series('custom.googleapis.com/luckygas/route/efficiency', efficiency)
    
    def record_google_api_call(self, api_name: str, status: str, cost: Optional[float] = None):
        """Record a Google API call."""
        self.google_api_calls.labels(api_name=api_name, status=status).inc()
        
        if cost:
            self.google_api_cost.labels(api_name=api_name).inc(cost)
        
        if self.project_id:
            self.write_time_series(
                'custom.googleapis.com/luckygas/google_api/calls',
                1,
                {'api_name': api_name, 'status': status}
            )
            
            if cost:
                self.write_time_series(
                    'custom.googleapis.com/luckygas/google_api/cost',
                    cost,
                    {'api_name': api_name}
                )


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector