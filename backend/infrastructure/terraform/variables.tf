variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "asia-east1"  # Taiwan
}

variable "zone" {
  description = "The GCP zone for resources"
  type        = string
  default     = "asia-east1-a"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "gcp_apis" {
  description = "List of GCP APIs to enable"
  type        = list(string)
  default = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudrun.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "clouderrorreporting.googleapis.com",
    "maps-backend.googleapis.com",
    "routes.googleapis.com",
    "places-backend.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "billingbudgets.googleapis.com",
  ]
}

variable "app_service_account_roles" {
  description = "IAM roles for the application service account"
  type        = list(string)
  default = [
    "roles/cloudsql.client",
    "roles/redis.editor",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectUser",
    "roles/aiplatform.user",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/errorreporting.writer",
  ]
}

variable "app_subnet_cidr" {
  description = "CIDR range for the application subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "db_subnet_cidr" {
  description = "CIDR range for the database subnet"
  type        = string
  default     = "10.0.2.0/24"
}

variable "cloud_sql_tier" {
  description = "Machine type for Cloud SQL instance"
  type        = string
  default     = "db-g1-small"  # For staging; use db-n1-standard-2 for production
}

variable "cloud_sql_disk_size" {
  description = "Disk size in GB for Cloud SQL instance"
  type        = number
  default     = 20  # For staging; use 100+ for production
}

variable "cloud_sql_backup_enabled" {
  description = "Enable automated backups for Cloud SQL"
  type        = bool
  default     = true
}

variable "cloud_sql_backup_start_time" {
  description = "Start time for automated backups (HH:MM format)"
  type        = string
  default     = "02:00"  # 2 AM Taiwan time
}

variable "redis_memory_size_gb" {
  description = "Memory size for Redis instance"
  type        = number
  default     = 1  # For staging; use 5+ for production
}

variable "redis_tier" {
  description = "Service tier for Redis instance"
  type        = string
  default     = "BASIC"  # For staging; use STANDARD_HA for production
}

variable "storage_location" {
  description = "Location for storage buckets"
  type        = string
  default     = "ASIA"  # Multi-region Asia
}

variable "storage_class" {
  description = "Storage class for buckets"
  type        = string
  default     = "STANDARD"
}

variable "monitoring_notification_channels" {
  description = "Email addresses for monitoring alerts"
  type        = list(string)
  default     = []
}

variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 1000  # Adjust based on requirements
}

variable "budget_alert_thresholds" {
  description = "Budget alert threshold percentages"
  type        = list(number)
  default     = [50, 80, 90, 100]
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = true  # Should be true for production
}

variable "labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    project     = "luckygas"
    managed_by  = "terraform"
    cost_center = "engineering"
  }
}