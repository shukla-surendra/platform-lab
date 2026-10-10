#!/usr/bin/env bash
# Creates the S3 bucket for Terraform state (same result as main.tf in this folder).
# Safe to re-run. Use EITHER this script OR `terraform apply` here, not both.
set -euo pipefail

REGION="us-east-1"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="tfstate-${ACCOUNT_ID}-${REGION}"

echo "Account: ${ACCOUNT_ID}"
echo "Bucket:  ${BUCKET}"

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Bucket already exists, only re-applying settings."
else
  # us-east-1 must NOT pass LocationConstraint; every other region must
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=${REGION}"
  fi
fi

aws s3api put-bucket-versioning --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Fill the placeholder in the next lesson so `terraform init` just works
NEXT="$(dirname "$0")/../04-ec2-s3-backend/main.tf"
if [ -f "$NEXT" ] && grep -q REPLACE_WITH_YOUR_STATE_BUCKET "$NEXT"; then
  sed -i.bak "s/REPLACE_WITH_YOUR_STATE_BUCKET/${BUCKET}/" "$NEXT" && rm -f "${NEXT}.bak"
  echo "Updated bucket name in ${NEXT}"
fi

echo "Done. Next: cd ../04-ec2-s3-backend && terraform init"
