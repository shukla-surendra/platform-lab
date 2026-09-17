output "distribution_domain_name" {
  value       = aws_cloudfront_distribution.this.domain_name
  description = "The *.cloudfront.net hostname — this is what you actually browse to."
}

output "distribution_id" {
  value       = aws_cloudfront_distribution.this.id
  description = "Needed for cache invalidations."
}

output "next_steps" {
  value = <<-EOT
    1. Upload something via the s3/ module's bucket: aws s3 cp ./index.html s3://<bucket>/index.html
    2. First request is slow (cache miss, fetched from S3): curl -I https://${aws_cloudfront_distribution.this.domain_name}/index.html
    3. Second request is fast (cache hit — check the "X-Cache" response header: Hit from cloudfront).
    4. After updating an object in S3, CloudFront still serves the OLD cached copy until default_ttl expires — force it immediately:
         aws cloudfront create-invalidation --distribution-id ${aws_cloudfront_distribution.this.id} --paths "/*"
  EOT
}
