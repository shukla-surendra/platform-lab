locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/cloudfront"
    },
    var.extra_tags,
  )
}

##############################################################################
# Origin Access Control — the modern replacement for the older Origin
# Access Identity. Lets CloudFront sign requests to the S3 bucket so the
# bucket policy can allow ONLY this specific distribution, keeping the
# bucket itself fully private (no public-read ACL/policy needed at all).
##############################################################################
resource "aws_cloudfront_origin_access_control" "this" {
  name                              = local.name
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  default_root_object = var.default_root_object
  price_class         = var.price_class
  comment             = local.name

  origin {
    domain_name              = var.origin_bucket_regional_domain_name
    origin_id                = local.name
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = local.name
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    default_ttl = var.default_ttl_seconds
    min_ttl     = 0
    max_ttl     = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # No custom domain here, so CloudFront's own *.cloudfront.net certificate
  # is used automatically — an ACM cert (in us-east-1, CloudFront's one
  # required region for certs) is only needed once you attach aliases.
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.tags
}

##############################################################################
# Bucket policy — lives in THIS module's state (not s3/'s) because it's
# specific to this one distribution's ARN. Perfectly normal in Terraform to
# attach a policy to a bucket created by a different apply, referenced by ARN.
##############################################################################
resource "aws_s3_bucket_policy" "allow_cloudfront" {
  bucket = var.origin_bucket_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontServicePrincipalReadOnly"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${var.origin_bucket_arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.this.arn
        }
      }
    }]
  })
}
