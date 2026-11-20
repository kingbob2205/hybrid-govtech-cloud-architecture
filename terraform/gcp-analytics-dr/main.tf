# =============================================================================
# GCP Specialist Wing (15% — me-west1 Tel Aviv · Nimbus Secondary Cloud)
# Serverless BigQuery Analytics + Fraud ML + Encrypted Nightly Cold DR Archive
# =============================================================================

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40"
    }
  }
}

variable "project_id" {
  type    = string
  default = "gov-portal-analytics-dr-il"
}

provider "google" {
  project = var.project_id
  region  = "me-west1"
}

resource "google_kms_key_ring" "dr_ring" {
  name     = "gov-cold-dr-keyring"
  location = "me-west1"
}

resource "google_kms_crypto_key" "dr_key" {
  name            = "gov-cold-dr-cmek"
  key_ring        = google_kms_key_ring.dr_ring.id
  rotation_period = "7776000s" # 90 days
}

resource "google_storage_bucket" "cold_dr_archive" {
  name                        = "${var.project_id}-cold-dr-archive"
  location                    = "ME-WEST1"
  storage_class               = "ARCHIVE"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  encryption {
    default_kms_key_name = google_kms_crypto_key.dr_key.id
  }

  retention_policy {
    retention_period = 2592000 # 30-day minimum lock for DR snapshots
  }
}

resource "google_bigquery_dataset" "welfare_fraud_analytics" {
  dataset_id                  = "welfare_analytics_prod"
  friendly_name               = "National Welfare Analytics & Fraud ML"
  location                    = "me-west1"
  default_table_expiration_ms = null

  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.dr_key.id
  }
}
