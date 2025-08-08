terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "luckygas-terraform-state"
    key            = "training/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "LuckyGas-Training"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Google Cloud Provider Configuration
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC Module
module "vpc" {
  source = "../modules/vpc"

  name               = "${var.project_name}-training-${var.environment}"
  cidr               = var.vpc_cidr
  availability_zones = data.aws_availability_zones.available.names
  
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
  
  tags = {
    Component = "Training"
  }
}

# EKS Cluster for Training Services
module "eks" {
  source = "../modules/eks"

  cluster_name    = "${var.project_name}-training-${var.environment}"
  cluster_version = "1.28"
  
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  
  node_groups = {
    training = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 6
      desired_size   = 3
      
      labels = {
        workload = "training"
      }
    }
  }
  
  tags = {
    Component = "Training"
  }
}

# RDS PostgreSQL for Training Database
module "rds" {
  source = "../modules/rds"

  identifier = "${var.project_name}-training-${var.environment}"
  
  engine         = "postgres"
  engine_version = "15.5"
  instance_class = var.db_instance_class
  
  allocated_storage     = 100
  max_allocated_storage = 500
  
  database_name = "luckygas_training"
  username      = "training_admin"
  
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  allowed_cidr_blocks = module.vpc.private_subnet_cidrs
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  enable_performance_insights = true
  
  tags = {
    Component = "Training-Database"
  }
}

# ElastiCache Redis for Session Management
module "elasticache" {
  source = "../modules/elasticache"

  name = "${var.project_name}-training-${var.environment}"
  
  node_type               = var.redis_node_type
  number_cache_nodes      = 2
  parameter_group_family  = "redis7"
  engine_version          = "7.1"
  
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  allowed_cidr_blocks = module.vpc.private_subnet_cidrs
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Component = "Training-Cache"
  }
}

# S3 Buckets for Training Content
resource "aws_s3_bucket" "training_content" {
  bucket = "${var.project_name}-training-content-${var.environment}"
  
  tags = {
    Component = "Training-Storage"
  }
}

resource "aws_s3_bucket_versioning" "training_content" {
  bucket = aws_s3_bucket.training_content.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "training_content" {
  bucket = aws_s3_bucket.training_content.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "training_content" {
  bucket = aws_s3_bucket.training_content.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Distribution for Video Delivery
resource "aws_cloudfront_distribution" "training_cdn" {
  origin {
    domain_name = aws_s3_bucket.training_content.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.training_content.id}"
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.training.cloudfront_access_identity_path
    }
  }
  
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  
  aliases = var.environment == "production" ? ["training-cdn.luckygas.com.tw"] : []
  
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.training_content.id}"
    
    forwarded_values {
      query_string = false
      
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
  }
  
  # Cache behavior for video content
  ordered_cache_behavior {
    path_pattern     = "*.mp4"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.training_content.id}"
    
    forwarded_values {
      query_string = false
      
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 3600
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = false
  }
  
  price_class = "PriceClass_200"
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = var.environment != "production"
    acm_certificate_arn            = var.environment == "production" ? var.acm_certificate_arn : null
    ssl_support_method             = var.environment == "production" ? "sni-only" : null
  }
  
  tags = {
    Component = "Training-CDN"
  }
}

resource "aws_cloudfront_origin_access_identity" "training" {
  comment = "OAI for ${var.project_name} training content"
}

# S3 Bucket Policy for CloudFront
resource "aws_s3_bucket_policy" "training_content" {
  bucket = aws_s3_bucket.training_content.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.training.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.training_content.arn}/*"
      }
    ]
  })
}

# Lambda for Video Processing
resource "aws_lambda_function" "video_processor" {
  filename         = "../lambda/video-processor.zip"
  function_name    = "${var.project_name}-video-processor-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "index.handler"
  source_code_hash = filebase64sha256("../lambda/video-processor.zip")
  runtime         = "python3.11"
  timeout         = 900
  memory_size     = 3008
  
  environment {
    variables = {
      SOURCE_BUCKET = aws_s3_bucket.training_content.id
      OUTPUT_BUCKET = aws_s3_bucket.training_content.id
      MEDIACONVERT_ENDPOINT = "https://mediaconvert.${var.aws_region}.amazonaws.com"
      MEDIACONVERT_ROLE_ARN = aws_iam_role.mediaconvert.arn
    }
  }
  
  tags = {
    Component = "Training-VideoProcessor"
  }
}

# S3 Event Trigger for Video Processing
resource "aws_s3_bucket_notification" "video_upload" {
  bucket = aws_s3_bucket.training_content.id
  
  lambda_function {
    lambda_function_arn = aws_lambda_function.video_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".mp4"
  }
  
  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.video_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.training_content.arn
}

# IAM Roles
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution.name
}

resource "aws_iam_role_policy" "lambda_s3_mediaconvert" {
  name = "${var.project_name}-lambda-s3-mediaconvert-${var.environment}"
  role = aws_iam_role.lambda_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.training_content.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "mediaconvert:CreateJob",
          "mediaconvert:GetJob",
          "mediaconvert:ListJobs"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = aws_iam_role.mediaconvert.arn
      }
    ]
  })
}

resource "aws_iam_role" "mediaconvert" {
  name = "${var.project_name}-mediaconvert-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "mediaconvert.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "mediaconvert_s3" {
  name = "${var.project_name}-mediaconvert-s3-${var.environment}"
  role = aws_iam_role.mediaconvert.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.training_content.arn}/*"
      }
    ]
  })
}

# Outputs
output "training_api_endpoint" {
  value = module.eks.cluster_endpoint
}

output "training_cdn_domain" {
  value = aws_cloudfront_distribution.training_cdn.domain_name
}

output "training_database_endpoint" {
  value = module.rds.endpoint
}

output "training_redis_endpoint" {
  value = module.elasticache.primary_endpoint_address
}