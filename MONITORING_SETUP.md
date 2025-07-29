# Lucky Gas Monitoring Setup Guide

## 🎯 Overview

This guide covers the complete monitoring setup for Lucky Gas production environment, including metrics collection, alerting, logging, and performance monitoring.

## 📊 Monitoring Stack Components

### Core Components
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notification
- **Loki**: Log aggregation
- **Tempo**: Distributed tracing
- **OpenTelemetry**: Observability framework

### Exporters
- **Node Exporter**: System metrics
- **PostgreSQL Exporter**: Database metrics
- **Redis Exporter**: Cache metrics
- **Nginx Exporter**: Web server metrics
- **Custom API Metrics**: Application-specific metrics

## 🚀 Quick Start

### 1. Deploy Monitoring Stack

```bash
# Using docker-compose
docker-compose -f docker-compose.prod.yml up -d prometheus grafana

# Using Kubernetes
kubectl apply -f k8s/monitoring/
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000
  - Default login: admin/admin
  - Change password on first login

- **Prometheus**: http://localhost:9090
  - No authentication by default

- **AlertManager**: http://localhost:9093
  - Configure webhook for notifications

## 📈 Metrics Configuration

### Application Metrics

```python
# backend/app/core/monitoring.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Business metrics
active_orders = Gauge(
    'luckygas_active_orders',
    'Number of active orders',
    ['status', 'area']
)

daily_revenue = Gauge(
    'luckygas_daily_revenue_twd',
    'Daily revenue in TWD',
    ['product_type']
)

# Custom middleware for automatic metrics
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

### Database Metrics

```yaml
# deployment/postgres/monitoring/queries.yaml
pg_luckygas:
  query: |
    SELECT 
      COUNT(*) as total_orders,
      COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
      COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered_orders
    FROM orders
    WHERE created_at >= CURRENT_DATE
  metrics:
    - total_orders:
        usage: "GAUGE"
        description: "Total orders today"
    - pending_orders:
        usage: "GAUGE"
        description: "Pending orders today"
    - delivered_orders:
        usage: "GAUGE"
        description: "Delivered orders today"

pg_customer_metrics:
  query: |
    SELECT 
      COUNT(DISTINCT customer_id) as active_customers,
      AVG(order_count) as avg_orders_per_customer
    FROM (
      SELECT customer_id, COUNT(*) as order_count
      FROM orders
      WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
      GROUP BY customer_id
    ) customer_orders
  metrics:
    - active_customers:
        usage: "GAUGE"
        description: "Active customers in last 30 days"
    - avg_orders_per_customer:
        usage: "GAUGE"
        description: "Average orders per customer"
```

## 🔔 Alert Configuration

### Critical Alerts

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: luckygas_critical
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"
          
      # Database connection issues
      - alert: DatabaseConnectionFailure
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "PostgreSQL is down"
          description: "Cannot connect to PostgreSQL database"
          
      # High response time
      - alert: HighResponseTime
        expr: |
          histogram_quantile(0.95, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 2
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High API response time"
          description: "95th percentile response time is {{ $value }}s"
```

### Business Alerts

```yaml
  - name: luckygas_business
    interval: 60s
    rules:
      # No orders in last hour
      - alert: NoOrdersReceived
        expr: increase(luckygas_orders_created_total[1h]) == 0
        for: 1h
        labels:
          severity: warning
          team: business
        annotations:
          summary: "No orders received in the last hour"
          description: "Check if there are system issues or business slowdown"
          
      # Low prediction accuracy
      - alert: LowPredictionAccuracy
        expr: luckygas_prediction_accuracy < 0.7
        for: 30m
        labels:
          severity: warning
          team: data
        annotations:
          summary: "AI prediction accuracy below threshold"
          description: "Prediction accuracy is {{ $value | humanizePercentage }}"
```

## 📊 Grafana Dashboards

### 1. Executive Dashboard

```json
{
  "dashboard": {
    "title": "Lucky Gas Executive Dashboard",
    "panels": [
      {
        "title": "Revenue Trend",
        "targets": [
          {
            "expr": "sum(luckygas_daily_revenue_twd) by (product_type)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Active Customers",
        "targets": [
          {
            "expr": "luckygas_active_customers"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Order Fulfillment Rate",
        "targets": [
          {
            "expr": "rate(luckygas_orders_delivered_total[1h]) / rate(luckygas_orders_created_total[1h])"
          }
        ],
        "type": "gauge"
      }
    ]
  }
}
```

### 2. Operations Dashboard

```json
{
  "dashboard": {
    "title": "Lucky Gas Operations",
    "panels": [
      {
        "title": "Active Routes",
        "targets": [
          {
            "expr": "luckygas_active_routes"
          }
        ],
        "type": "worldmap"
      },
      {
        "title": "Driver Utilization",
        "targets": [
          {
            "expr": "luckygas_driver_utilization_percent"
          }
        ],
        "type": "heatmap"
      },
      {
        "title": "Delivery Performance",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, luckygas_delivery_time_minutes_bucket)"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

### 3. Technical Dashboard

```json
{
  "dashboard": {
    "title": "Lucky Gas Technical Metrics",
    "panels": [
      {
        "title": "API Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends{datname=\"luckygas\"}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))"
          }
        ],
        "type": "gauge"
      }
    ]
  }
}
```

## 📝 Logging Configuration

### Application Logging

```python
# backend/app/core/logging_config.py
import logging
import json
from pythonjsonlogger import jsonlogger

# Configure structured logging
def setup_logging():
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        json_ensure_ascii=False
    )
    logHandler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    
    # Add custom fields
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.service = "luckygas-backend"
        record.environment = os.getenv("ENVIRONMENT", "development")
        record.version = os.getenv("VERSION", "unknown")
        return record
    
    logging.setLogRecordFactory(record_factory)
```

### Log Aggregation with Loki

```yaml
# deployment/loki/loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /tmp/loki
  storage:
    filesystem:
      chunks_directory: /tmp/loki/chunks
      rules_directory: /tmp/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://alertmanager:9093
```

### Promtail Configuration

```yaml
# deployment/promtail/promtail-config.yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: luckygas
    static_configs:
      - targets:
          - localhost
        labels:
          job: luckygas
          __path__: /var/log/luckygas/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            service: service
            message: message
            timestamp: timestamp
      - labels:
          level:
          service:
      - timestamp:
          source: timestamp
          format: RFC3339
```

## 🔍 Distributed Tracing

### OpenTelemetry Setup

```python
# backend/app/core/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_tracing(app):
    # Set up the tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()
    
    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
        insecure=True
    )
    
    # Add batch processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Instrument libraries
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
```

## 🚨 Incident Response

### Runbook Template

```markdown
# Runbook: High Error Rate

## Alert Details
- **Alert Name**: HighErrorRate
- **Severity**: Critical
- **Team**: Backend

## Investigation Steps

1. **Check Error Logs**
   ```bash
   kubectl logs -l app=backend --tail=100 | grep ERROR
   ```

2. **Identify Error Pattern**
   ```promql
   sum by (endpoint, status) (rate(http_requests_total{status=~"5.."}[5m]))
   ```

3. **Check Recent Deployments**
   ```bash
   kubectl rollout history deployment/backend
   ```

## Mitigation Steps

1. **Rollback if Recent Deployment**
   ```bash
   kubectl rollout undo deployment/backend
   ```

2. **Scale Up if Load Issue**
   ```bash
   kubectl scale deployment/backend --replicas=5
   ```

3. **Clear Cache if Data Issue**
   ```bash
   redis-cli FLUSHDB
   ```

## Escalation
- After 15 minutes: Page on-call engineer
- After 30 minutes: Page team lead
- After 60 minutes: Page CTO
```

## 📱 Mobile Monitoring

### Firebase Performance Monitoring

```kotlin
// android/app/src/main/java/com/luckygas/MainActivity.kt
import com.google.firebase.perf.FirebasePerformance
import com.google.firebase.perf.metrics.Trace

class MainActivity : AppCompatActivity() {
    private lateinit var loadTrace: Trace
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Start custom trace
        loadTrace = FirebasePerformance.getInstance().newTrace("app_load")
        loadTrace.start()
        
        // Your app initialization
        
        loadTrace.stop()
    }
    
    fun trackDeliveryCompletion(orderId: String) {
        val trace = FirebasePerformance.getInstance().newTrace("delivery_completion")
        trace.putAttribute("order_id", orderId)
        trace.start()
        
        // Delivery completion logic
        
        trace.incrementMetric("deliveries_completed", 1)
        trace.stop()
    }
}
```

## 🔧 Maintenance Scripts

### Metrics Cleanup

```bash
#!/bin/bash
# scripts/cleanup-metrics.sh

# Delete metrics older than 90 days
curl -X POST -g 'http://prometheus:9090/api/v1/admin/tsdb/delete_series?match[]={__name__=~".+"}[90d]'

# Compact storage
curl -X POST http://prometheus:9090/api/v1/admin/tsdb/clean_tombstones
```

### Dashboard Backup

```bash
#!/bin/bash
# scripts/backup-dashboards.sh

# Export all Grafana dashboards
for dashboard in $(curl -s "http://admin:admin@grafana:3000/api/search" | jq -r '.[] | .uid'); do
  curl -s "http://admin:admin@grafana:3000/api/dashboards/uid/$dashboard" | \
    jq '.dashboard' > "dashboards/$dashboard.json"
done

# Upload to cloud storage
gsutil -m cp dashboards/*.json gs://luckygas-backups/grafana/
```

## 📈 SLI/SLO Configuration

### Service Level Indicators

```yaml
# monitoring/sli-config.yaml
slis:
  - name: api_availability
    description: "API endpoint availability"
    query: |
      sum(rate(http_requests_total{status!~"5.."}[5m]))
      /
      sum(rate(http_requests_total[5m]))
    
  - name: api_latency
    description: "API p95 latency"
    query: |
      histogram_quantile(0.95,
        sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
      )
    
  - name: order_success_rate
    description: "Order processing success rate"
    query: |
      sum(rate(luckygas_orders_delivered_total[24h]))
      /
      sum(rate(luckygas_orders_created_total[24h]))
```

### Service Level Objectives

```yaml
# monitoring/slo-config.yaml
slos:
  - name: api_availability_slo
    sli: api_availability
    objective: 0.999  # 99.9% availability
    window: 30d
    
  - name: api_latency_slo
    sli: api_latency
    objective: 0.2  # 200ms p95 latency
    window: 30d
    
  - name: order_success_slo
    sli: order_success_rate
    objective: 0.98  # 98% order success rate
    window: 7d
```

## 🎯 Getting Started Checklist

- [ ] Deploy monitoring stack components
- [ ] Configure Prometheus scrape targets
- [ ] Import Grafana dashboards
- [ ] Set up alert notification channels
- [ ] Configure log aggregation
- [ ] Enable distributed tracing
- [ ] Create custom business metrics
- [ ] Set up SLI/SLO monitoring
- [ ] Document runbooks for alerts
- [ ] Train team on dashboard usage
- [ ] Schedule regular reviews
- [ ] Test incident response procedures

Remember: Good monitoring is proactive, not reactive. Set up alerts before you need them!