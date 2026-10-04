#!/usr/bin/env bash
# Deploy NEW CODE ONLY, without running terraform.
# Build zip -> upload to the artifacts bucket -> point the Lambda at it.
#
# Use this when Terraform only owns the infra (enable the `lifecycle { ignore_changes }`
# block in 04_lambda.tf). Otherwise the next `terraform apply` will notice the code
# differs from src/ and redeploy what is in src/.
set -euo pipefail

cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-us-east-1}"
BUCKET="$(terraform output -raw artifacts_bucket)"
FUNCTION="$(terraform output -raw lambda_name)"
ZIP="build/processor-$(date +%Y%m%d%H%M%S).zip"

mkdir -p build
(cd src && zip -qr "../$ZIP" .)

aws s3 cp "$ZIP" "s3://$BUCKET/lambda/$(basename "$ZIP")" --region "$REGION"

aws lambda update-function-code \
  --function-name "$FUNCTION" \
  --s3-bucket "$BUCKET" \
  --s3-key "lambda/$(basename "$ZIP")" \
  --region "$REGION" \
  --query '{Version:Version,LastModified:LastModified,CodeSha256:CodeSha256}'

aws lambda wait function-updated --function-name "$FUNCTION" --region "$REGION"
echo "deployed $ZIP to $FUNCTION"
