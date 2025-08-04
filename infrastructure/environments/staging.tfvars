# Staging Environment Configuration
project_id  = "vast-tributary-466619-m8"
region      = "asia-east1"
environment = "staging"

# Database Configuration
database_tier                    = "db-f1-micro"
database_backup_enabled          = true
database_point_in_time_recovery  = false
database_transaction_log_days    = 1
database_max_connections         = 50
database_deletion_protection     = false

# Redis Configuration
redis_tier         = "BASIC"
redis_memory_gb    = 1

# Cloud Run Configuration
backend_min_instances  = 0
backend_max_instances  = 3
backend_cpu            = "1"
backend_memory         = "2Gi"

frontend_min_instances = 0
frontend_max_instances = 5

# Domain Configuration
domains = ["staging.luckygas.tw"]

# Alerting Configuration
alert_email = "dev@luckygas.tw"

# Scaling Configuration
enable_autoscaling = true
enable_cdn         = false

# Security Configuration
enable_iap          = false
enable_armor        = false
enable_private_ip   = true

# Monitoring Configuration
enable_monitoring   = true
enable_logging      = true
enable_tracing      = false

# Backup Configuration
backup_retention_days = 7
enable_versioning     = false
EOF < /dev/null