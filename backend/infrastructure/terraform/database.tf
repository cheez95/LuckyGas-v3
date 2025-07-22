# Cloud SQL for PostgreSQL

# Generate a random password for the database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store the database password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.environment}-database-password"
  project   = var.project_id
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Cloud SQL instance
resource "google_sql_database_instance" "postgres" {
  name                = "${var.environment}-luckygas-postgres"
  database_version    = "POSTGRES_15"
  region              = var.region
  project             = var.project_id
  deletion_protection = var.enable_deletion_protection
  
  settings {
    tier                        = var.cloud_sql_tier
    disk_size                   = var.cloud_sql_disk_size
    disk_type                   = "PD_SSD"
    disk_autoresize             = true
    disk_autoresize_limit       = var.cloud_sql_disk_size * 5
    availability_type           = var.environment == "production" ? "REGIONAL" : "ZONAL"
    deletion_protection_enabled = var.enable_deletion_protection
    
    backup_configuration {
      enabled                        = var.cloud_sql_backup_enabled
      start_time                     = var.cloud_sql_backup_start_time
      point_in_time_recovery_enabled = var.environment == "production"
      transaction_log_retention_days = var.environment == "production" ? 7 : 1
      
      backup_retention_settings {
        retained_backups = var.environment == "production" ? 30 : 7
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      
      enable_private_path_for_google_cloud_services = true
    }
    
    database_flags {
      name  = "max_connections"
      value = var.environment == "production" ? "200" : "50"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = var.environment == "production" ? "256MB" : "64MB"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    
    user_labels = merge(var.labels, {
      environment = var.environment
      component   = "database"
    })
  }
  
  depends_on = [
    google_project_service.apis["sqladmin.googleapis.com"],
    google_service_networking_connection.private_vpc_connection
  ]
}

# Create database
resource "google_sql_database" "app_db" {
  name     = "luckygas_${var.environment}"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

# Create database user
resource "google_sql_user" "app_user" {
  name     = "luckygas_${var.environment}"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
  project  = var.project_id
}

# Redis instance for caching
resource "google_redis_instance" "cache" {
  name               = "${var.environment}-luckygas-redis"
  tier               = var.redis_tier
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  project            = var.project_id
  redis_version      = "REDIS_7_0"
  display_name       = "Lucky Gas Redis Cache (${var.environment})"
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  
  labels = merge(var.labels, {
    environment = var.environment
    component   = "cache"
  })
  
  persistence_config {
    persistence_mode    = var.environment == "production" ? "RDB" : "DISABLED"
    rdb_snapshot_period = var.environment == "production" ? "TWELVE_HOURS" : null
  }
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 2
        minutes = 0
      }
    }
  }
  
  depends_on = [
    google_project_service.apis["redis.googleapis.com"],
    google_service_networking_connection.private_vpc_connection
  ]
}

# Service networking for private connections
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.environment}-private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  project       = var.project_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
  
  depends_on = [google_project_service.apis["servicenetworking.googleapis.com"]]
}