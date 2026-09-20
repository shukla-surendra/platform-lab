# The source repo. The pipeline watches var.branch_name.
#
# NOTE: CodeCommit was closed to AWS accounts created after 2024-07-25. If
# `apply` fails here with an access/not-available error, that's why.

resource "aws_codecommit_repository" "app" {
  repository_name = local.name
  description     = "Source repo for the V2 CI/CD pipeline."
}
