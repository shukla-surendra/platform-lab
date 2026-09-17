locals {
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/codecommit"
    },
    var.extra_tags,
  )
}

##############################################################################
# The repository. NOTE: CodeCommit is closed to NEW AWS customers (accounts
# created after 2024-07-25 cannot create repos) — see README for the
# GitHub/CodeStar-Connections alternative used as the source stage instead.
##############################################################################
resource "aws_codecommit_repository" "this" {
  repository_name = var.project
  description     = "Managed by Terraform — source repo for the CI/CD lab."
  # NOTE: no default_branch argument here on purpose — a brand-new repo has
  # ZERO branches, and CodeCommit's UpdateDefaultBranch API (which this
  # argument drives) requires the branch to already exist. Set it AFTER the
  # first push, either via `aws codecommit update-default-branch` (see
  # outputs.next_steps) or by re-running `terraform apply` once seed_readme's
  # null_resource has pushed `var.default_branch`.
}

# aws_codecommit_repository has no "put a file in it" argument — a repo starts
# genuinely empty. Terraform doesn't have a native "commit a file" resource
# either, so we shell out once via a local-exec null_resource. This is a
# deliberate, narrow exception to "no shell in Terraform" — CodeCommit simply
# doesn't expose this any other way.
resource "null_resource" "seed_commit" {
  count = var.seed_readme ? 1 : 0

  triggers = {
    repo_id = aws_codecommit_repository.this.repository_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      workdir="$(mktemp -d)"
      trap 'rm -rf "$workdir"' EXIT
      git clone "${aws_codecommit_repository.this.clone_url_http}" "$workdir"
      cd "$workdir"
      git checkout -b "${var.default_branch}" 2>/dev/null || git checkout "${var.default_branch}"
      echo "# ${var.project}" > README.md
      echo "Seeded by Terraform's codecommit/ module." >> README.md
      git add README.md
      git -c user.name="terraform" -c user.email="terraform@localhost" commit -m "Initial commit (seeded by Terraform)"
      git push origin "${var.default_branch}"
    EOT
  }
}
