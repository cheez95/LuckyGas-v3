# Terraform Outputs

output "gke_cluster_name" {
  description = "Name of the GKE cluster"
  value       = google_container_cluster.primary.name
}

output "gke_cluster_endpoint" {
  description = "Endpoint for the GKE cluster"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "gke_cluster_ca_certificate" {
  description = "CA certificate for the GKE cluster"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "database_connection_name" {
  description = "Connection name for Cloud SQL instance"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_private_ip" {
  description = "Private IP address of the database"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Redis instance port"
  value       = google_redis_instance.cache.port
}

output "ingress_ip" {
  description = "Static IP address for ingress"
  value       = google_compute_global_address.ingress_ip.address
}

output "app_data_bucket" {
  description = "Name of the application data bucket"
  value       = google_storage_bucket.app_data.name
}

output "static_assets_bucket" {
  description = "Name of the static assets bucket"
  value       = google_storage_bucket.static_assets.name
}

output "static_assets_url" {
  description = "URL for static assets"
  value       = "https://storage.googleapis.com/${google_storage_bucket.static_assets.name}"
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "app_service_account_email" {
  description = "Email of the application service account"
  value       = google_service_account.app_identity.email
}

output "kubernetes_service_account_email" {
  description = "Email of the Kubernetes service account"
  value       = google_service_account.kubernetes.email
}

output "vpc_network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "vpc_subnet_name" {
  description = "Name of the VPC subnet"
  value       = google_compute_subnetwork.subnet.name
}

output "serverless_vpc_connector" {
  description = "Name of the serverless VPC connector"
  value       = google_vpc_access_connector.connector.name
}

output "monitoring_dashboard_url" {
  description = "URL to the monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.main.id}?project=${var.project_id}"
}

# Output Kubernetes configuration for kubectl
output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --zone ${var.zone} --project ${var.project_id}"
}