output "bucket_name" {
  value       = aws_s3_bucket.this.bucket
  description = "Pass into cloudfront/'s origin_bucket_name variable, or reference from any other module's IAM policy."
}

output "bucket_arn" {
  value       = aws_s3_bucket.this.arn
  description = "Bucket ARN."
}

output "bucket_regional_domain_name" {
  value       = aws_s3_bucket.this.bucket_regional_domain_name
  description = "The exact origin domain cloudfront/ needs (NOT the website endpoint — this is the private REST API endpoint used with Origin Access Control)."
}

output "next_steps" {
  value = <<-EOT
    1. Upload something: aws s3 cp ./index.html s3://${aws_s3_bucket.this.bucket}/index.html
    2. List versions (with versioning_enabled): aws s3api list-object-versions --bucket ${aws_s3_bucket.this.bucket}
    3. Confirm it's NOT publicly reachable: curl -I https://${aws_s3_bucket.this.bucket_regional_domain_name}/index.html (expect 403 — that's correct, see cloudfront/ for the private-origin pattern)
    4. Wire bucket_name / bucket_regional_domain_name into cloudfront/.
  EOT
}
