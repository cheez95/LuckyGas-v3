output "vpc_network" {
  description = "The VPC network"
  value       = google_compute_network.vpc.name
}

output "app_subnet" {
  description = "The application subnet"
  value       = google_compute_subnetwork.app_subnet.name
}

output "service_account_email" {
  description = "The application service account email"
  value       = google_service_account.app_service_account.email
}

output "cloud_sql_instance_name" {
  description = "The Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "cloud_sql_connection_name" {
  description = "The Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "database_name" {
  description = "The database name"
  value       = google_sql_database.app_db.name
}

output "database_user" {
  description = "The database username"
  value       = google_sql_user.app_user.name
}

output "database_password_secret" {
  description = "The Secret Manager secret ID for the database password"
  value       = google_secret_manager_secret.db_password.secret_id
}

output "redis_host" {
  description = "The Redis instance host"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "The Redis instance port"
  value       = google_redis_instance.cache.port
}

output "media_bucket" {
  description = "The media storage bucket name"
  value       = google_storage_bucket.media.name
}

output "backup_bucket" {
  description = "The backup storage bucket name"
  value       = google_storage_bucket.backups.name
}

output "terraform_state_bucket" {
  description = "The Terraform state bucket name (production only)"
  value       = var.environment == "production" ? google_storage_bucket.terraform_state[0].name : null
}

output "monitoring_dashboard_url" {
  description = "URL to the monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.app_dashboard.id}?project=${var.project_id}"
}