# Staging environment configuration
project_id  = "vast-tributary-466619-m8"  # Actual staging project ID
environment = "staging"
region      = "asia-east1"
zone        = "asia-east1-a"

# Staging-specific configurations
cloud_sql_tier              = "db-g1-small"
cloud_sql_disk_size         = 20
redis_memory_size_gb        = 1
redis_tier                  = "BASIC"
enable_deletion_protection  = false
budget_amount               = 500

# Monitoring notification channels
monitoring_notification_channels = [
  "admin@luckygas.tw",
  "devops@luckygas.tw"
]

# Labels
labels = {
  project     = "luckygas"
  environment = "staging"
  managed_by  = "terraform"
  cost_center = "engineering"
}