terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "luckygas-terraform-state"
    prefix = "production"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Project variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-east1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudsql.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "iap.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "aiplatform.googleapis.com",
    "maps-backend.googleapis.com",
    "routes.googleapis.com"
  ])
  
  service = each.key
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "luckygas-vpc"
  auto_create_subnetworks = false
  
  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "main" {
  name          = "luckygas-subnet-${var.region}"
  ip_cidr_range = "10.0.0.0/24"
  network       = google_compute_network.main.id
  region        = var.region
  
  private_ip_google_access = true
}

# VPC Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "luckygas-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.main.name
  
  depends_on = [google_project_service.apis]
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "main" {
  name             = "luckygas-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier = var.environment == "production" ? "db-n1-standard-2" : "db-f1-micro"
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.region
      point_in_time_recovery_enabled = var.environment == "production"
      transaction_log_retention_days = var.environment == "production" ? 7 : 1
    }
    
    database_flags {
      name  = "max_connections"
      value = var.environment == "production" ? "200" : "50"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
    }
  }
  
  deletion_protection = var.environment == "production"
  
  depends_on = [google_project_service.apis, google_compute_network.main]
}

resource "google_sql_database" "main" {
  name     = "luckygas"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "luckygas_app"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Redis Instance
resource "google_redis_instance" "cache" {
  name           = "luckygas-redis-${var.environment}"
  tier           = var.environment == "production" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.environment == "production" ? 5 : 1
  region         = var.region
  
  authorized_network = google_compute_network.main.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
  
  depends_on = [google_project_service.apis]
}

# Artifact Registry
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "luckygas"
  description   = "Docker repository for Lucky Gas applications"
  format        = "DOCKER"
  
  depends_on = [google_project_service.apis]
}

# Secret Manager Secrets
resource "google_secret_manager_secret" "db_password" {
  secret_id = "database-password"
  
  replication {
    automatic = true
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret-key"
  
  replication {
    automatic = true
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

# Service Accounts
resource "google_service_account" "backend" {
  account_id   = "luckygas-backend"
  display_name = "Lucky Gas Backend Service Account"
}

resource "google_service_account" "frontend" {
  account_id   = "luckygas-frontend"
  display_name = "Lucky Gas Frontend Service Account"
}

# IAM Roles
resource "google_project_iam_member" "backend_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/storage.objectUser",
    "roles/aiplatform.user",
    "roles/redis.editor"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Storage Buckets
resource "google_storage_bucket" "media" {
  name          = "${var.project_id}-media"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-backups"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
  
  versioning {
    enabled = true
  }
}

# Cloud Load Balancer
resource "google_compute_global_address" "default" {
  name = "luckygas-ip"
}

resource "google_compute_backend_service" "frontend" {
  name        = "luckygas-frontend-backend"
  protocol    = "HTTP"
  timeout_sec = 30
  
  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }
  
  health_checks = [google_compute_health_check.frontend.id]
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "luckygas-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = "luckygas-frontend"
  }
}

resource "google_compute_health_check" "frontend" {
  name               = "luckygas-frontend-health-check"
  check_interval_sec = 10
  timeout_sec        = 5
  
  http_health_check {
    port         = 8080
    request_path = "/"
  }
}

resource "google_compute_url_map" "default" {
  name            = "luckygas-url-map"
  default_service = google_compute_backend_service.frontend.id
  
  host_rule {
    hosts        = ["app.luckygas.tw", "www.luckygas.tw"]
    path_matcher = "allpaths"
  }
  
  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.frontend.id
    
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend.id
    }
  }
}

resource "google_compute_backend_service" "backend" {
  name        = "luckygas-backend-backend"
  protocol    = "HTTP"
  timeout_sec = 30
  
  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }
  
  health_checks = [google_compute_health_check.backend.id]
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_region_network_endpoint_group" "backend_neg" {
  name                  = "luckygas-backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = "luckygas-backend"
  }
}

resource "google_compute_health_check" "backend" {
  name               = "luckygas-backend-health-check"
  check_interval_sec = 10
  timeout_sec        = 5
  
  http_health_check {
    port         = 8000
    request_path = "/health"
  }
}

resource "google_compute_target_https_proxy" "default" {
  name             = "luckygas-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

resource "google_compute_managed_ssl_certificate" "default" {
  name = "luckygas-ssl-cert"
  
  managed {
    domains = ["app.luckygas.tw", "www.luckygas.tw"]
  }
}

resource "google_compute_global_forwarding_rule" "default" {
  name       = "luckygas-forwarding-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}

# Cloud CDN
resource "google_compute_backend_bucket" "static_assets" {
  name        = "luckygas-static-assets"
  bucket_name = google_storage_bucket.static.name
  enable_cdn  = true
  
  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    client_ttl        = 3600
    default_ttl       = 3600
    max_ttl           = 86400
    negative_caching  = true
    serve_while_stale = 86400
  }
}

resource "google_storage_bucket" "static" {
  name          = "${var.project_id}-static"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# Cloud Scheduler for batch jobs
resource "google_cloud_scheduler_job" "daily_predictions" {
  name             = "daily-demand-predictions"
  description      = "Generate daily demand predictions"
  schedule         = "0 2 * * *"  # 2 AM daily Taiwan time
  time_zone        = "Asia/Taipei"
  attempt_deadline = "320s"
  
  http_target {
    http_method = "POST"
    uri         = "https://app.luckygas.tw/api/v1/predictions/batch/daily"
    
    oidc_token {
      service_account_email = google_service_account.backend.email
    }
  }
  
  depends_on = [google_project_service.apis]
}

# Monitoring and Alerting
resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notification"
  type         = "email"
  
  labels = {
    email_address = "alerts@luckygas.tw"
  }
}

resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate Alert"
  combiner     = "OR"
  
  conditions {
    display_name = "Error rate above 5%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Outputs
output "load_balancer_ip" {
  value = google_compute_global_address.default.address
}

output "database_connection" {
  value     = google_sql_database_instance.main.private_ip_address
  sensitive = true
}

output "redis_host" {
  value     = google_redis_instance.cache.host
  sensitive = true
}