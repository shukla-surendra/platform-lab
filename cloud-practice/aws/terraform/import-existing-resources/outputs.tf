output "bucket_name" {
  description = "Name of the now-Terraform-managed bucket."
  value       = aws_s3_bucket.imported.bucket
}

output "bucket_arn" {
  description = "ARN of the now-Terraform-managed bucket."
  value       = aws_s3_bucket.imported.arn
}

output "next_steps" {
  description = "What to do after the import succeeds."
  value       = <<-EOT
    1. terraform state list                 # confirm aws_s3_bucket.imported is present
    2. terraform plan                       # should now show "No changes"
    3. Delete generated.tf if you haven't already merged/cleaned it into main.tf
    4. Optionally remove the `import` block from imports.tf -- it's a no-op
       from here on, but some teams keep it as a record of provenance.
  EOT
}
