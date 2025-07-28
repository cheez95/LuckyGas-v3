# Cloud SQL PostgreSQL Instance

resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_name}-db-${var.environment}-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier              = var.environment == "production" ? "db-custom-4-16384" : "db-custom-2-8192"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.environment == "production" ? 100 : 50
    disk_autoresize   = true
    disk_autoresize_limit = var.environment == "production" ? 500 : 100
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "production"
      transaction_log_retention_days = var.environment == "production" ? 7 : 3
      
      backup_retention_settings {
        retained_backups = var.environment == "production" ? 30 : 7
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }
    
    database_flags {
      name  = "max_connections"
      value = var.environment == "production" ? "200" : "100"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = var.environment == "production" ? "4096MB" : "2048MB"
    }
    
    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
    
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    
    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }
    
    database_flags {
      name  = "log_temp_files"
      value = "0"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 3  # 3 AM Taiwan time
      update_track = var.environment == "production" ? "stable" : "canary"
    }
  }
  
  deletion_protection = var.environment == "production"
  
  depends_on = [
    google_service_networking_connection.private_vpc_connection,
  ]
}

# Random suffix for database instance name
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Database
resource "google_sql_database" "database" {
  name     = "luckygas"
  instance = google_sql_database_instance.postgres.name
  
  lifecycle {
    prevent_destroy = true
  }
}

# Database user
resource "google_sql_user" "app_user" {
  name     = "luckygas_app"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# Generate random password
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store database credentials in Secret Manager
resource "google_secret_manager_secret" "db_connection_string" {
  secret_id = "${var.project_name}-db-connection-${var.environment}"
  
  replication {
    auto {}
  }
  
  depends_on = [
    google_project_service.required_apis["secretmanager.googleapis.com"],
  ]
}

resource "google_secret_manager_secret_version" "db_connection_string" {
  secret = google_secret_manager_secret.db_connection_string.id
  
  secret_data = jsonencode({
    host     = google_sql_database_instance.postgres.private_ip_address
    port     = 5432
    database = google_sql_database.database.name
    username = google_sql_user.app_user.name
    password = google_sql_user.app_user.password
    connection_string = "postgresql://${google_sql_user.app_user.name}:${google_sql_user.app_user.password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.database.name}"
  })
}

# Grant access to the secret
resource "google_secret_manager_secret_iam_member" "app_secret_access" {
  secret_id = google_secret_manager_secret.db_connection_string.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_identity.email}"
}

# Create a high-availability read replica for production
resource "google_sql_database_instance" "read_replica" {
  count = var.environment == "production" ? 1 : 0
  
  name                 = "${var.project_name}-db-replica-${var.environment}-${random_id.db_suffix.hex}"
  master_instance_name = google_sql_database_instance.postgres.name
  database_version     = "POSTGRES_15"
  region               = var.region
  
  replica_configuration {
    failover_target = false
  }
  
  settings {
    tier              = "db-custom-2-8192"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 100
    disk_autoresize   = true
    
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }
}