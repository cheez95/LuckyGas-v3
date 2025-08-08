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
  description = "Environment name (production, staging, dev)"
  type        = string
  validation {
    condition     = contains(["production", "staging", "dev"], var.environment)
    error_message = "Environment must be production, staging, or dev."
  }
}

variable "domain" {
  description = "Primary domain name"
  type        = string
  default     = "luckygas.com.tw"
}

variable "cors_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default = [
    "https://luckygas.com.tw",
    "https://www.luckygas.com.tw"
  ]
}

# Database Configuration
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-n1-standard-2"
}

variable "db_backup_enabled" {
  description = "Enable database backups"
  type        = bool
  default     = true
}

variable "db_backup_start_time" {
  description = "Backup start time (HH:MM format)"
  type        = string
  default     = "03:00"
}

variable "db_max_connections" {
  description = "Maximum database connections"
  type        = number
  default     = 200
}

# Redis Configuration
variable "redis_tier" {
  description = "Redis tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "STANDARD_HA"
}

variable "redis_memory_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 5
}

# Cloud Run Configuration
variable "backend_image" {
  description = "Backend Docker image URL"
  type        = string
}

variable "cloud_run_cpu" {
  description = "Cloud Run CPU allocation"
  type        = string
  default     = "2"
}

variable "cloud_run_memory" {
  description = "Cloud Run memory allocation"
  type        = string
  default     = "2Gi"
}

variable "cloud_run_min_instances" {
  description = "Minimum Cloud Run instances"
  type        = string
  default     = "2"
}

variable "cloud_run_max_instances" {
  description = "Maximum Cloud Run instances"
  type        = string
  default     = "100"
}

variable "cloud_run_concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 100
}

# Security Configuration
variable "allowed_ip_ranges" {
  description = "IP ranges allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Open to all by default, restrict in production
}

variable "rate_limit_threshold" {
  description = "Rate limit threshold (requests per minute)"
  type        = number
  default     = 100
}

variable "rate_limit_ban_duration" {
  description = "Rate limit ban duration in seconds"
  type        = number
  default     = 600
}

# Monitoring Configuration
variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
}

variable "error_rate_threshold" {
  description = "Error rate threshold for alerts (percentage)"
  type        = number
  default     = 5
}

variable "uptime_check_interval" {
  description = "Uptime check interval in seconds"
  type        = number
  default     = 60
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for database"
  type        = bool
  default     = true
}

# Feature Flags
variable "enable_cdn" {
  description = "Enable Cloud CDN for static assets"
  type        = bool
  default     = true
}

variable "enable_armor" {
  description = "Enable Cloud Armor security policies"
  type        = bool
  default     = true
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    project     = "luckygas"
    managed_by  = "terraform"
    environment = "production"
  }
}