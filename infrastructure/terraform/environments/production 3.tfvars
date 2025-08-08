# Production Environment Configuration
project_id  = "luckygas-production"
environment = "production"
region      = "asia-east1"
domain      = "luckygas.com.tw"

# CORS origins for production
cors_origins = [
  "https://luckygas.com.tw",
  "https://www.luckygas.com.tw",
  "https://app.luckygas.com.tw"
]

# Database configuration - Production specs
db_tier                       = "db-n1-standard-2"
db_backup_enabled            = true
db_backup_start_time         = "03:00"
db_max_connections           = 200
enable_point_in_time_recovery = true

# Redis configuration - High availability
redis_tier      = "STANDARD_HA"
redis_memory_gb = 5

# Cloud Run configuration - Production scale
backend_image            = "gcr.io/luckygas-production/backend:latest"
cloud_run_cpu           = "2"
cloud_run_memory        = "2Gi"
cloud_run_min_instances = "2"
cloud_run_max_instances = "100"
cloud_run_concurrency   = 100

# Security configuration
allowed_ip_ranges       = ["0.0.0.0/0"] # Open access, protected by auth
rate_limit_threshold    = 100
rate_limit_ban_duration = 600
enable_armor           = true
enable_iap             = false # Enable if needed for admin access

# Monitoring configuration
alert_email           = "ops@luckygas.com.tw"
error_rate_threshold  = 5
uptime_check_interval = 60

# Backup configuration
backup_retention_days = 30

# Feature flags
enable_cdn = true

# Tags
tags = {
  project     = "luckygas"
  environment = "production"
  managed_by  = "terraform"
  cost_center = "operations"
}