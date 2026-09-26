output "bucket_name" {
  value       = aws_s3_bucket.this.bucket
  description = "Bucket name."
}

output "bucket_arn" {
  value       = aws_s3_bucket.this.arn
  description = "Bucket ARN."
}

output "kms_key_arn" {
  value       = aws_kms_key.this.arn
  description = "CMK ARN — use this exact string for --sse-kms-key-id, the bucket policy compares it literally."
}

output "kms_key_alias" {
  value       = aws_kms_alias.this.name
  description = "Key alias (handy for the console/CLI; not accepted by the bucket policy's key-id condition)."
}

output "consumer_policy_json" {
  value       = data.aws_iam_policy_document.consumer.json
  description = "IAM policy granting read/write on the bucket plus use of the key. Attach to any role that needs access."
}

output "next_steps" {
  value = <<-EOT
    1. Upload (default encryption applies the CMK):
         aws s3 cp ./somefile.txt s3://${aws_s3_bucket.this.bucket}/somefile.txt
    2. Confirm SSE-KMS + the key that was used:
         aws s3api head-object --bucket ${aws_s3_bucket.this.bucket} --key somefile.txt
         (expect ServerSideEncryption=aws:kms, SSEKMSKeyId=${aws_kms_key.this.arn}, BucketKeyEnabled=true)
    3. Try to bypass it — this should be denied by the bucket policy:
         aws s3 cp ./somefile.txt s3://${aws_s3_bucket.this.bucket}/bad.txt --sse AES256
    4. Check rotation: aws kms get-key-rotation-status --key-id ${aws_kms_key.this.key_id}
    5. Kill switch: aws kms disable-key --key-id ${aws_kms_key.this.key_id}  (reads then fail; re-enable to restore)
  EOT
}
