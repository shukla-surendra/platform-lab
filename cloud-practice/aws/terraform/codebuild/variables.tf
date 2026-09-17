variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the CodeBuild project name."
  type        = string
  default     = "aws-mastery-codebuild"
}

variable "source_type" {
  description = "Where CodeBuild pulls source from: CODECOMMIT, GITHUB, or NO_SOURCE (uses only the inline buildspec, ignores any repo)."
  type        = string
  default     = "NO_SOURCE"

  validation {
    condition     = contains(["CODECOMMIT", "GITHUB", "NO_SOURCE"], var.source_type)
    error_message = "source_type must be one of: CODECOMMIT, GITHUB, NO_SOURCE."
  }
}

variable "codecommit_clone_url" {
  description = "HTTPS clone URL from the codecommit/ module's output — required if source_type = CODECOMMIT."
  type        = string
  default     = ""
}

variable "github_repo_url" {
  description = "https://github.com/<org>/<repo> — required if source_type = GITHUB (needs a CodeStar Connection authorized in the console first; see README)."
  type        = string
  default     = ""
}

variable "compute_type" {
  description = "BUILD_GENERAL1_SMALL / MEDIUM / LARGE — bigger = faster + more $/minute."
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "build_image" {
  description = "CodeBuild-managed image. The Amazon Linux 2023 standard image covers most simple builds (has git, python, node, docker CLI)."
  type        = string
  default     = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
}

variable "privileged_mode" {
  description = "Required if the buildspec runs `docker build`/pushes to ECR — grants the build container access to a Docker daemon."
  type        = bool
  default     = false
}

variable "buildspec" {
  description = "Inline buildspec (YAML as a string). Used verbatim when source_type = NO_SOURCE, or as an override for CODECOMMIT/GITHUB sources instead of a committed buildspec.yml."
  type        = string
  default     = <<-EOT
    version: 0.2
    phases:
      install:
        runtime-versions:
          nodejs: 20
      pre_build:
        commands:
          - echo "Pre-build: $(date -u)"
      build:
        commands:
          - echo "Building..."
          - mkdir -p dist
          - echo "<h1>Built by CodeBuild at $(date -u)</h1>" > dist/index.html
      post_build:
        commands:
          - echo "Build finished with exit code $CODEBUILD_BUILD_SUCCEEDING"
    artifacts:
      files:
        - '**/*'
      base-directory: dist
  EOT
}

variable "artifact_bucket_name" {
  description = "If set, reuse an existing S3 bucket for build artifacts (e.g. codepipeline/'s artifact bucket). If empty, this module creates its own."
  type        = string
  default     = ""
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
