variable "project_name" {
  description = "Project name"
  type        = string
  default     = "luckygas"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "gcp_project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region"
  type        = string
  default     = "asia-east1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.100.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.100.1.0/24", "10.100.2.0/24", "10.100.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.100.11.0/24", "10.100.12.0/24", "10.100.13.0/24"]
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for CloudFront (production only)"
  type        = string
  default     = ""
}

variable "enable_video_processing" {
  description = "Enable automatic video processing"
  type        = bool
  default     = true
}

variable "enable_practice_environment" {
  description = "Enable practice environment feature"
  type        = bool
  default     = true
}

variable "moodle_admin_email" {
  description = "Moodle administrator email"
  type        = string
  default     = "admin@luckygas.com.tw"
}

variable "moodle_site_name" {
  description = "Moodle site name"
  type        = string
  default     = "Lucky Gas Training Center"
}

variable "backup_retention_days" {
  description = "Database backup retention in days"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "CloudWatch logs retention in days"
  type        = number
  default     = 90
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}