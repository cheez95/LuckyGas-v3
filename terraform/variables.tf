# Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "luckygas"
}

variable "environment" {
  description = "Environment (staging or production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-east1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "asia-east1-a"
}

# Networking variables
variable "subnet_cidr" {
  description = "CIDR range for subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "pods_cidr" {
  description = "CIDR range for GKE pods"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_cidr" {
  description = "CIDR range for GKE services"
  type        = string
  default     = "10.2.0.0/20"
}

variable "serverless_vpc_connector_cidr" {
  description = "CIDR range for serverless VPC connector"
  type        = string
  default     = "10.3.0.0/28"
}

variable "redis_reserved_ip_range" {
  description = "Reserved IP range for Redis instance"
  type        = string
  default     = "10.4.0.0/29"
}

# GKE variables
variable "kubernetes_version" {
  description = "Kubernetes version for GKE"
  type        = string
  default     = "1.28"
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for deployment"
  type        = string
  default     = "luckygas"
}

variable "machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "n2-standard-4"
}

variable "min_node_count" {
  description = "Minimum number of nodes in the node pool"
  type        = number
  default     = 2
}

variable "max_node_count" {
  description = "Maximum number of nodes in the node pool"
  type        = number
  default     = 10
}

# Monitoring variables
variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts (optional)"
  type        = string
  default     = ""
  sensitive   = true
}