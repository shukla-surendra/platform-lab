locals {
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/ecr"
    },
    var.extra_tags,
  )
}

resource "aws_ecr_repository" "this" {
  name                 = var.project
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }
}

# Untagged images (superseded by a new push of the same tag, or orphaned by a
# failed build) are the #1 source of ECR storage bloat — expire them fast,
# separately from the "keep N tagged images" rule below.
resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep only the most recent ${var.max_image_count} tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "latest"]
          countType     = "imageCountMoreThan"
          countNumber   = var.max_image_count
        }
        action = { type = "expire" }
      },
    ]
  })
}

# Cross-account/public-read style access is opt-in and explicit — by default
# this repo is only reachable by principals in THIS account with ecr:* IAM
# permission (e.g. the ECS task execution role in ecs-fargate/).
data "aws_caller_identity" "current" {}
