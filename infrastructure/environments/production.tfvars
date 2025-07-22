# Production Environment Configuration
project_id  = "luckygas-production"
region      = "asia-east1"
environment = "production"

# Database Configuration
database_tier                    = "db-n1-standard-2"
database_backup_enabled          = true
database_point_in_time_recovery  = true
database_transaction_log_days    = 7
database_max_connections         = 200
database_deletion_protection     = true

# Redis Configuration
redis_tier         = "STANDARD_HA"
redis_memory_gb    = 5

# Cloud Run Configuration
backend_min_instances  = 1
backend_max_instances  = 10
backend_cpu            = "2"
backend_memory         = "4Gi"

frontend_min_instances = 1
frontend_max_instances = 20

# Domain Configuration
domains = ["app.luckygas.tw", "www.luckygas.tw"]

# Alerting Configuration
alert_email = "alerts@luckygas.tw"

# Scaling Configuration
enable_autoscaling = true
enable_cdn         = true

# Security Configuration
enable_iap          = true
enable_armor        = true
enable_private_ip   = true

# Monitoring Configuration
enable_monitoring   = true
enable_logging      = true
enable_tracing      = true

# Backup Configuration
backup_retention_days = 30
enable_versioning     = true
EOF < /dev/null