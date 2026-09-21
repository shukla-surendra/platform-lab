##############################################################################
# Locals
##############################################################################
locals {
  tags = merge(
    {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
      Module      = "aws/terraform/import-existing-resources"
    },
    var.extra_tags,
  )
}

##############################################################################
# aws_s3_bucket.imported
#
# This is the CLEANED-UP version of what `terraform plan
# -generate-config-out=generated.tf` produces for a plain bucket created by
# scripts/create-manual-bucket.sh. Raw generated output is uglier and MUST
# be hand-edited before you keep it — see README "Cleaning up generated
# config" for exactly what was changed here and why:
#
#   - `bucket = "REPLACE_WITH_YOUR_BUCKET_NAME"` -> `bucket = var.bucket_name`
#   - dropped computed-only attributes the generator includes that aren't
#     valid arguments to set (e.g. arn, bucket_domain_name, hosted_zone_id,
#     bucket_regional_domain_name, region, id)
#   - dropped the generator's `# __generated__ by Terraform` / lifecycle
#     comment noise
#   - added `tags = local.tags` so it merges into this module's normal
#     tagging convention instead of the empty map the generator leaves you
#     with (a manually-created bucket usually has no/inconsistent tags)
##############################################################################
resource "aws_s3_bucket" "imported" {
  bucket = var.bucket_name
  tags   = local.tags
}

##############################################################################
# aws_s3_bucket_versioning / aws_s3_bucket_server_side_encryption_configuration
#
# In the AWS provider v4+, versioning/encryption/public-access-block are
# SEPARATE resources from aws_s3_bucket itself (see ../s3/main.tf for the
# from-scratch equivalent). Each needs its OWN import block if the
# manually-created bucket already has these configured — generate-config-out
# only drafts config for resources you gave it an `import` block for, it
# will not discover related sub-resources automatically.
#
# scripts/create-manual-bucket.sh does not enable versioning, so this repo
# does not import an aws_s3_bucket_versioning resource. If your real bucket
# has versioning/encryption/a policy already, add:
#
#   import {
#     to = aws_s3_bucket_versioning.imported
#     id = var.bucket_name
#   }
#
# to imports.tf, re-run `terraform plan -generate-config-out=generated.tf`,
# and merge the new block in the same way as above.
##############################################################################
