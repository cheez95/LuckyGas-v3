# Lucky Gas Production Infrastructure Guide

## Overview

This guide documents the critical production infrastructure hardening implemented for Lucky Gas, focusing on high availability, monitoring, and security.

## Infrastructure Components

### 1. PostgreSQL High Availability

#### Architecture
- **Primary-Replica Setup**: Streaming replication with automatic failover
- **Connection Pooling**: pgBouncer for efficient connection management
- **Monitoring**: PostgreSQL Exporter for Prometheus metrics

#### Key Features
- Streaming replication with 2 read replicas
- pgBouncer connection pooling (1000 max connections)
- Automatic failover with repmgr
- Point-in-time recovery capability
- Daily automated backups to S3

#### Configuration
```yaml
# docker-compose.prod.yml
postgres-primary:
  # Primary database with optimized settings
  # Performance tuning for Taiwan workload patterns
  
postgres-replica:
  # Read replica for load distribution
  # Async replication for performance

pgbouncer:
  # Transaction pooling mode
  # 25 default pool size per database
```

### 2. Redis High Availability

#### Architecture
- **Master-Slave Replication**: 1 master, 1 slave
- **Sentinel**: 3 sentinels for automatic failover
- **Persistence**: AOF + RDB for data durability

#### Key Features
- Automatic failover in <10 seconds
- Data persistence with AOF
- Memory optimization with LRU eviction
- Redis Exporter for monitoring

#### Configuration
```yaml
# docker-compose.prod.yml
redis-master:
  # Persistence enabled
  # 512MB memory limit
  
redis-sentinel-1/2/3:
  # Quorum of 2 for failover
  # 5 second down detection
```

### 3. API Rate Limiting & Security

#### Rate Limiting with Slowapi
- **Per-Endpoint Limits**: Customized for each API endpoint
- **API Key Tiers**: Basic, Standard, Premium, Enterprise
- **Role-Based Multipliers**: Higher limits for admin users
- **Distributed Rate Limiting**: Redis-backed for multi-instance

#### Security Middleware
- **Security Headers**: OWASP recommended headers
- **SQL Injection Prevention**: Pattern detection and blocking
- **XSS Protection**: Input sanitization and CSP
- **Suspicious Activity Detection**: Automated blocking

#### API Key Management
```python
# Tier limits
"basic": "100/hour, 20/minute"
"standard": "1000/hour, 100/minute" 
"premium": "10000/hour, 500/minute"
"enterprise": "100000/hour, 2000/minute"
```

### 4. Monitoring & Observability

#### Prometheus Metrics
- **Business Metrics**: Orders, deliveries, revenue, predictions
- **System Metrics**: CPU, memory, disk, network
- **Application Metrics**: Request rate, latency, errors
- **Custom Dashboards**: Grafana dashboards for all metrics

#### OpenTelemetry Tracing
- **Distributed Tracing**: Full request lifecycle tracking
- **Performance Analysis**: Identify bottlenecks
- **Error Tracking**: Automatic exception capture
- **Service Dependencies**: Visualize service interactions

#### Health Checks
- **Comprehensive Checks**: Database, Redis, external APIs
- **Degraded State Detection**: Partial failure handling
- **Automated Alerts**: Prometheus alerting rules

### 5. Circuit Breakers

#### External Service Protection
```python
# Circuit breaker thresholds
google_api: failure_threshold=5, recovery_timeout=60s
sms_api: failure_threshold=3, recovery_timeout=120s
banking_api: failure_threshold=3, recovery_timeout=180s
einvoice_api: failure_threshold=5, recovery_timeout=120s
```

### 6. Production Docker Compose

#### Key Features
- **Resource Limits**: CPU and memory constraints
- **Health Checks**: All services monitored
- **Rolling Updates**: Zero-downtime deployments
- **Secret Management**: External secret files
- **Network Isolation**: Service segregation

## Deployment Process

### Prerequisites
1. Docker Engine 20.10+
2. Docker Compose 2.0+
3. 8GB+ RAM, 4+ CPU cores
4. SSL certificates for domains
5. S3 bucket for backups

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/luckygas-v3.git
cd luckygas-v3

# 2. Copy environment file
cp .env.production.example .env.production

# 3. Edit configuration
vim .env.production

# 4. Create secrets directory
mkdir -p secrets
cp /path/to/google-credentials.json secrets/

# 5. Generate secure passwords
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For JWT_SECRET_KEY
openssl rand -hex 16  # For database passwords

# 6. Pull and build images
docker-compose -f docker-compose.prod.yml build

# 7. Initialize database
docker-compose -f docker-compose.prod.yml up -d postgres-primary
docker-compose -f docker-compose.prod.yml exec postgres-primary psql -U postgres -c "CREATE DATABASE luckygas;"

# 8. Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 9. Start all services
docker-compose -f docker-compose.prod.yml up -d

# 10. Verify health
curl https://api.luckygas.tw/api/v1/health
```

### SSL Certificate Setup

```bash
# Using Let's Encrypt
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d luckygas.tw -d www.luckygas.tw -d api.luckygas.tw

# Copy certificates
cp /etc/letsencrypt/live/luckygas.tw/* deployment/nginx/ssl/
```

## Monitoring Setup

### Prometheus & Grafana

```bash
# Access Grafana
https://grafana.luckygas.tw (port 3000)
# Default: admin / [configured password]

# Import dashboards
- PostgreSQL: Dashboard ID 9628
- Redis: Dashboard ID 11835
- Node Exporter: Dashboard ID 1860
- Custom Lucky Gas dashboards in monitoring/grafana/dashboards/
```

### Alerts Configuration

Key alerts configured:
- Database down or high connections
- Redis down or high memory
- API high latency (>1s p95)
- API error rate >5%
- Order processing delays >2 hours
- External API failures
- Disk space <15%
- Container restarts >3 in 15min

## Backup & Recovery

### Automated Backups

```bash
# Daily backups at 2 AM Taiwan time
# Stored locally and uploaded to S3
# 7-day retention policy

# Manual backup
docker-compose -f docker-compose.prod.yml exec backup /usr/local/bin/backup.sh

# Restore from backup
docker-compose -f docker-compose.prod.yml exec postgres-primary pg_restore \
  -h localhost -U luckygas -d luckygas_restore \
  /backups/luckygas_prod_backup_20240120_020000.sql.gz
```

## Security Best Practices

1. **Secrets Management**
   - Never commit secrets to git
   - Use Docker secrets for sensitive data
   - Rotate API keys quarterly
   - Monitor key usage

2. **Network Security**
   - Use internal Docker networks
   - Expose only necessary ports
   - Enable firewall rules
   - Use VPN for admin access

3. **Application Security**
   - Keep dependencies updated
   - Run security scans regularly
   - Monitor for suspicious activity
   - Enable audit logging

4. **Data Protection**
   - Encrypt data at rest (S3)
   - Use SSL for all connections
   - Implement RBAC
   - Regular security audits

## Performance Optimization

### Database Optimization
- Connection pooling via pgBouncer
- Read replicas for read-heavy queries
- Proper indexing strategy
- Query optimization

### Caching Strategy
- Redis for session storage
- API response caching
- Static asset caching in Nginx
- CDN for frontend assets

### Application Optimization
- Async request handling
- Background job processing
- Resource pooling
- Efficient serialization

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
```bash
# Check pgBouncer
docker-compose -f docker-compose.prod.yml logs pgbouncer

# Check connection count
docker-compose -f docker-compose.prod.yml exec postgres-primary \
  psql -U luckygas -c "SELECT count(*) FROM pg_stat_activity;"
```

2. **Redis Failover Issues**
```bash
# Check sentinel status
docker-compose -f docker-compose.prod.yml exec redis-sentinel-1 \
  redis-cli -p 26379 sentinel masters
```

3. **High Memory Usage**
```bash
# Check container stats
docker stats

# Adjust memory limits in docker-compose.prod.yml
```

## Maintenance

### Regular Tasks

- **Daily**: Check backup completion, review error logs
- **Weekly**: Review metrics and alerts, update dependencies
- **Monthly**: Security patches, performance review
- **Quarterly**: Disaster recovery test, capacity planning

### Upgrade Process

```bash
# 1. Backup current state
./deployment/scripts/backup-prod.sh

# 2. Pull latest changes
git pull origin main

# 3. Build new images
docker-compose -f docker-compose.prod.yml build

# 4. Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale backend=3 backend
# Wait for health checks
docker-compose -f docker-compose.prod.yml up -d --no-deps backend

# 5. Run migrations if needed
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

## Support

For production issues:
1. Check monitoring dashboards
2. Review application logs
3. Check alert history
4. Contact DevOps team

## Appendix

### Resource Requirements

- **Minimum**: 4 vCPUs, 8GB RAM, 100GB SSD
- **Recommended**: 8 vCPUs, 16GB RAM, 200GB SSD
- **Network**: 100Mbps dedicated bandwidth
- **Storage**: S3 for backups, local SSD for databases

### Port Mapping

- 80: HTTP (redirects to HTTPS)
- 443: HTTPS 
- 3000: Grafana (internal)
- 9090: Prometheus (internal)
- 9100: Node Exporter (internal)
- 9187: PostgreSQL Exporter (internal)
- 9121: Redis Exporter (internal)