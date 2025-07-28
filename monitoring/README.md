# LuckyGas Monitoring Stack

This directory contains the complete monitoring stack for LuckyGas, including dashboards for system metrics, business KPIs, and pilot program migration monitoring.

## 🚀 Quick Start

1. **Start the monitoring stack:**
   ```bash
   cd monitoring
   docker-compose up -d
   ```

2. **Access the services:**
   - Grafana: http://localhost:3001 (admin/luckygas2024)
   - Prometheus: http://localhost:9090
   - AlertManager: http://localhost:9093

3. **View dashboards:**
   - System Overview
   - API Performance
   - Business Metrics
   - Error Tracking
   - Infrastructure Health
   - Sync Monitoring

## 📊 Available Dashboards

### 1. System Overview
- Real-time system health metrics
- CPU, memory, and disk usage
- Request rates and success rates
- Active alerts and notifications

### 2. API Performance
- Endpoint-specific latency metrics (P50, P95, P99)
- Request rates by endpoint
- Error rates and response codes
- Performance trends over time

### 3. Business Metrics
- Daily orders and revenue (今日訂單數/營收)
- Active customer count (活躍客戶數)
- Delivery completion rate (配送完成率)
- Cylinder sales by size
- Driver performance metrics

### 4. Error Tracking
- Real-time error rates with alerts
- Error distribution by type
- Exception tracking
- Recent error logs from Loki
- Top error endpoints

### 5. Infrastructure Health
- Service uptime status
- Database connections and transactions
- Redis operations
- Network and disk I/O
- Service health matrix

### 6. Sync Monitoring (Pilot Program)
- Total sync operations
- Success/failure rates by entity type
- Sync latency metrics
- Conflict tracking
- Pilot customer growth

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   LuckyGas  │────▶│ Prometheus  │────▶│   Grafana   │
│     API     │     │  (Metrics)  │     │(Dashboards) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                         │
       │            ┌─────────────┐             │
       └───────────▶│    Loki     │─────────────┘
                    │   (Logs)    │
                    └─────────────┘
```

## 🔧 Configuration

### Prometheus Configuration
Edit `prometheus/prometheus.yml` to:
- Add new scrape targets
- Configure alert rules
- Adjust scrape intervals

### Grafana Provisioning
- Datasources: `grafana/provisioning/datasources/`
- Dashboards: `grafana/provisioning/dashboards/`
- Alert rules: `grafana/provisioning/alerting/`

### Custom Metrics

The LuckyGas API exports custom business metrics at `/api/v1/metrics/business`:

```yaml
# Order metrics
luckygas_orders_created_total
luckygas_orders_delivered_total
luckygas_order_status_gauge

# Revenue metrics
luckygas_revenue_total
luckygas_cylinder_revenue_total

# Customer metrics
luckygas_active_customers_total
luckygas_pilot_customers_total

# Sync metrics
luckygas_sync_operations_total
luckygas_sync_duration_seconds
luckygas_sync_conflicts_total
```

## 🚨 Alerting

### Configured Alerts

1. **High Error Rate**: >5% error rate for 5 minutes
2. **Service Down**: Any service unreachable
3. **Database Connection Pool**: >80% utilized
4. **Sync Failures**: >10 failures in 5 minutes
5. **Disk Space**: <10% free space

### Alert Channels
Configure in AlertManager (`alertmanager/alertmanager.yml`):
- Email notifications
- Slack webhooks
- PagerDuty integration
- Custom webhooks

## 📈 Performance Optimization

### Grafana Performance
- Dashboard refresh: 30s (configurable)
- Query caching enabled
- Time range limits for heavy queries

### Prometheus Retention
- Default: 30 days
- Adjust in docker-compose.yml: `--storage.tsdb.retention.time`

### Resource Requirements
- Prometheus: 2GB RAM, 10GB disk
- Grafana: 1GB RAM, 1GB disk
- Loki: 2GB RAM, 20GB disk

## 🔍 Troubleshooting

### Common Issues

1. **Grafana can't connect to Prometheus**
   - Check if Prometheus is running: `docker ps`
   - Verify network connectivity
   - Check datasource configuration

2. **Missing metrics**
   - Verify API is exposing metrics endpoint
   - Check Prometheus scrape configuration
   - Look for errors in Prometheus targets page

3. **High memory usage**
   - Reduce retention period
   - Optimize dashboard queries
   - Enable query result caching

### Useful Commands

```bash
# View logs
docker-compose logs -f grafana
docker-compose logs -f prometheus

# Restart services
docker-compose restart grafana

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test metrics endpoint
curl http://localhost:8000/api/v1/metrics/business
```

## 🛠️ Development

### Adding New Dashboards

1. Create dashboard in Grafana UI
2. Export as JSON
3. Save to `grafana/dashboards/`
4. Restart Grafana to auto-provision

### Adding Custom Metrics

1. Implement metric in backend:
   ```python
   from prometheus_client import Counter, Histogram
   
   order_counter = Counter(
       'luckygas_custom_metric_total',
       'Description of metric',
       ['label1', 'label2']
   )
   ```

2. Expose in metrics endpoint
3. Add to Prometheus scrape config
4. Create Grafana visualizations

## 📚 Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Loki Documentation](https://grafana.com/docs/loki/)