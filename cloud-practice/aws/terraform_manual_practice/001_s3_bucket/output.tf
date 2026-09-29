output "s3_bucket_id" {
  value       = aws_s3_bucket.main_prj.id
  description = "Bucket ID"
}
