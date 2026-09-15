terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30, < 7.0"
    }
    random = {
      source  = "hashicorp/random"
    }
  }

  # State is local on purpose -- this is a throwaway smoke test to confirm
  # `terraform apply` can actually reach the llm-training-dev project, not a
  # module meant to be reused or shared.
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# GCS bucket names are globally unique across ALL of GCP, not just this
# project -- the random suffix is what makes re-running this from a clean
# state (no existing terraform.tfstate) safe to retry after a name collision.
resource "random_id" "suffix" {
  byte_length = 4
}

# The actual billable resource: one empty Standard-class bucket. An empty
# bucket costs effectively $0 (GCS bills per GB-month stored + operations;
# zero bytes stored is zero cost) -- this exists purely to prove
# terraform + gcloud auth + the target project all work end-to-end.
resource "google_storage_bucket" "smoke_test" {
  name                        = "tf-smoke-test-${var.project_id}-${random_id.suffix.hex}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  # Lets `terraform destroy` remove it even if something lands an object in
  # it later -- there's nothing here worth protecting against deletion.
  force_destroy = true

  labels = {
    purpose    = "tf-smoke-test"
    managed-by = "terraform"
  }
}

output "bucket_name" {
  value = google_storage_bucket.smoke_test.name
}

output "bucket_url" {
  value = google_storage_bucket.smoke_test.url
}
