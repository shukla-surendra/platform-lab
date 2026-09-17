locals {
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/dynamodb"
    },
    var.extra_tags,
  )
  has_range_key = var.range_key != ""
}

resource "aws_dynamodb_table" "this" {
  name         = var.project
  billing_mode = var.billing_mode
  hash_key     = var.hash_key
  range_key    = local.has_range_key ? var.range_key : null

  attribute {
    name = var.hash_key
    type = "S"
  }

  dynamic "attribute" {
    for_each = local.has_range_key ? [var.range_key] : []
    content {
      name = attribute.value
      type = "S"
    }
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled = true # AWS-owned key by default — no separate KMS key/cost, unlike ebs/'s customer-managed key
  }

  dynamic "ttl" {
    for_each = var.enable_ttl ? [1] : []
    content {
      attribute_name = var.ttl_attribute_name
      enabled        = true
    }
  }

  stream_enabled   = var.enable_stream
  stream_view_type = var.enable_stream ? "NEW_AND_OLD_IMAGES" : null

  tags = local.tags
}
