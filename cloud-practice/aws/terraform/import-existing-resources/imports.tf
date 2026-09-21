##############################################################################
# Import blocks (Terraform >= 1.5) — the declarative replacement for the
# `terraform import <addr> <id>` CLI command. This file is the entrypoint
# for two separate workflows; see README.md for the full walkthrough.
#
#   1. GENERATE config (run once, before main.tf has a matching resource
#      block, or whenever you want Terraform to draft one for you):
#
#        terraform plan -generate-config-out=generated.tf
#
#      Terraform reads the REAL bucket via the AWS provider and writes a
#      best-effort `resource "aws_s3_bucket" "imported" { ... }` block into
#      generated.tf. It does NOT touch state and does NOT touch main.tf.
#      Review + clean up generated.tf (see README "Cleaning up generated
#      config"), then merge the cleaned block into main.tf and delete
#      generated.tf.
#
#   2. IMPORT into state (run once main.tf has a real resource block —
#      hand-written or generated+cleaned):
#
#        terraform plan    # should show no changes, or only cosmetic diffs
#        terraform apply   # `apply` is what actually writes the resource
#                           # into state; `plan` alone never mutates state.
#
# After `apply` succeeds, `terraform state list` will show
# aws_s3_bucket.imported and every subsequent plan/apply treats this import
# block as a no-op — safe to leave in place as a record of how the resource
# entered management, or delete it once you've confirmed the import stuck.
##############################################################################

import {
  to = aws_s3_bucket.imported
  id = var.bucket_name
}
