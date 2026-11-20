# =============================================================================
# AWS Primary Anchor (80% — il-central-1 Tel Aviv · 3 Availability Zones)
# 4-Layer Hybrid Multi-Cloud National Citizen Portal Architecture
# =============================================================================

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
  backend "s3" {
    bucket       = "gov-portal-terraform-state-il-central-1"
    key          = "prod/aws-core/terraform.tfstate"
    region       = "il-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "il-central-1"
  default_tags {
    tags = {
      Project     = "HybridGovTechPortal"
      Environment = "prod"
      Compliance  = "Nimbus-IL"
      ManagedBy   = "Terraform"
    }
  }
}

# --- Layer 1: Sovereign KMS Key (CMK) & Immutable Audit Bucket ---
resource "aws_kms_key" "sovereign_cmk" {
  description             = "Sovereign CMK for citizen documents, Aurora, SQS, and audit logs"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_s3_bucket" "audit_worm_logs" {
  bucket              = "gov-sec-audit-logs-worm-il"
  object_lock_enabled = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit_worm_retention" {
  bucket = aws_s3_bucket.audit_worm_logs.id
  rule {
    default_retention {
      mode  = "COMPLIANCE"
      years = 7
    }
  }
}

# --- Layer 2: 3-Tier VPC (Public ALB-only / Private App / Isolated Data) ---
resource "aws_vpc" "prod_personal" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_vpc_endpoint" "s3_gateway_free" {
  vpc_id            = aws_vpc.prod_personal.id
  service_name      = "com.amazonaws.il-central-1.s3"
  vpc_endpoint_type = "Gateway"
}

resource "aws_ec2_transit_gateway" "hub" {
  description                     = "Central Hub-and-Spoke TGW linking 6 accounts + Direct Connect HQ"
  auto_accept_shared_attachments  = "disable"
  default_route_table_association = "enable"
}

# --- Layer 3: Serverless Mainframe Shock-Absorber (SQS FIFO + DLQ) ---
resource "aws_sqs_queue" "claims_dlq" {
  name                        = "citizen-claims-dlq.fifo"
  fifo_queue                  = true
  kms_master_key_id           = aws_kms_key.sovereign_cmk.arn
  message_retention_seconds   = 1209600 # 14 days
}

resource "aws_sqs_queue" "claims_fifo" {
  name                        = "citizen-claims-intake.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  kms_master_key_id           = aws_kms_key.sovereign_cmk.arn
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.claims_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_ecs_cluster" "personal_fargate" {
  name = "gov-personal-fargate-graviton"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# --- Layer 4: Citizen Document Vault (S3 Auto-Tiering -> Glacier Deep Archive) ---
resource "aws_s3_bucket" "citizen_docs_vault" {
  bucket              = "gov-citizen-docs-vault-il"
  object_lock_enabled = true
}

resource "aws_s3_bucket_public_access_block" "citizen_docs_block" {
  bucket                  = aws_s3_bucket.citizen_docs_vault.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "citizen_docs_finops" {
  bucket = aws_s3_bucket.citizen_docs_vault.id
  rule {
    id     = "finops-auto-tiering"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}
