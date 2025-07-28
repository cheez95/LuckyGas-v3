# Memorystore Redis Instance

resource "google_redis_instance" "cache" {
  name               = "${var.project_name}-redis-${var.environment}"
  tier               = var.environment == "production" ? "STANDARD_HA" : "BASIC"
  memory_size_gb     = var.environment == "production" ? 5 : 1
  region             = var.region
  redis_version      = "REDIS_7_0"
  display_name       = "${var.project_name} Redis ${var.environment}"
  reserved_ip_range  = var.redis_reserved_ip_range
  authorized_network = google_compute_network.vpc.id
  
  persistence_config {
    persistence_mode    = var.environment == "production" ? "RDB" : "DISABLED"
    rdb_snapshot_period = var.environment == "production" ? "TWELVE_HOURS" : null
  }
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }
  
  labels = {
    environment = var.environment
    purpose     = "cache"
  }
  
  depends_on = [
    google_project_service.required_apis["redis.googleapis.com"],
  ]
}

# Store Redis connection info in Secret Manager
resource "google_secret_manager_secret" "redis_connection" {
  secret_id = "${var.project_name}-redis-connection-${var.environment}"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_connection" {
  secret = google_secret_manager_secret.redis_connection.id
  
  secret_data = jsonencode({
    host = google_redis_instance.cache.host
    port = google_redis_instance.cache.port
    auth_string = google_redis_instance.cache.auth_string
    connection_string = "redis://:${google_redis_instance.cache.auth_string}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
  })
}

# Grant access to the secret
resource "google_secret_manager_secret_iam_member" "redis_secret_access" {
  secret_id = google_secret_manager_secret.redis_connection.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_identity.email}"
}