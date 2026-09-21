#!/usr/bin/env bash
# Simulates "infrastructure that already exists" by creating an S3 bucket
# with the AWS CLI -- i.e. NOT through Terraform -- so you have something
# real to practice importing. Run this yourself; it is not run for you.
#
# Usage: ./create-manual-bucket.sh <globally-unique-bucket-name> [region]
set -euo pipefail

BUCKET_NAME="${1:?Usage: $0 <bucket-name> [region]}"
REGION="${2:-us-east-1}"

if [ "$REGION" = "us-east-1" ]; then
  aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
else
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
fi

echo "Created s3://$BUCKET_NAME in $REGION (NOT tracked by Terraform yet)."
echo "Next: set bucket_name = \"$BUCKET_NAME\" in terraform.tfvars, then follow README.md."
