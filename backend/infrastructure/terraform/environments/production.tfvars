# Production environment configuration
project_id  = "luckygas-production"  # Replace with actual production project ID
environment = "production"
region      = "asia-east1"
zone        = "asia-east1-a"

# Production-specific configurations
cloud_sql_tier              = "db-n1-standard-2"
cloud_sql_disk_size         = 100
redis_memory_size_gb        = 5
redis_tier                  = "STANDARD_HA"
enable_deletion_protection  = true
budget_amount               = 2000

# Monitoring notification channels
monitoring_notification_channels = [
  "admin@luckygas.tw",
  "devops@luckygas.tw",
  "oncall@luckygas.tw"
]

# Labels
labels = {
  project     = "luckygas"
  environment = "production"
  managed_by  = "terraform"
  cost_center = "operations"
}