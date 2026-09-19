# STEP 2 — the source repo.
#
# NOTE: CodeCommit is closed to AWS accounts created after 2024-07-25 — if
# `apply` fails here with an access/not-available error, that's why. Use
# GitHub + a CodeStar Connection instead (console-only setup — see
# cloud-practice/aws/terraform/codebuild/README.md), and swap
# codepipeline.tf's Source stage to `provider = "CodeStarSourceConnection"`.

resource "aws_codecommit_repository" "app" {
  repository_name = local.name
  description     = "Source repo for the hand-wired CI/CD pipeline."
}
