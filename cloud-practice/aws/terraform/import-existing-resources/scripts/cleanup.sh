#!/usr/bin/env bash
# Tears down the practice bucket AND removes it from Terraform state,
# leaving nothing behind. Run this yourself; it is not run for you.
#
# Usage: ./cleanup.sh <bucket-name>
set -euo pipefail

BUCKET_NAME="${1:?Usage: $0 <bucket-name>}"

echo "Removing aws_s3_bucket.imported from Terraform state (state only, bucket untouched)..."
terraform -chdir="$(dirname "$0")/.." state rm aws_s3_bucket.imported || true

echo "Emptying and deleting s3://$BUCKET_NAME ..."
aws s3 rm "s3://$BUCKET_NAME" --recursive || true
aws s3api delete-bucket --bucket "$BUCKET_NAME"

echo "Done. Bucket deleted, Terraform state clean."
