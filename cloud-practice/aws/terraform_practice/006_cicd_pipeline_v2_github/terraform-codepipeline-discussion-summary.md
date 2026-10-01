# Terraform + AWS CodePipeline V2 — Discussion Summary

## 1. Overall Pipeline Flow

The example pipeline is:

```text
GitHub
   ↓
CodeConnections / CodeStar Connection
   ↓
CodePipeline — Source Stage
   ↓
S3 Artifact Store
   ↓
CodePipeline — Build Stage
   ↓
CodeBuild Project
   ↓
buildspec.yml / another buildspec
```

The main resources are:

- GitHub connection
- S3 artifact bucket
- CodeBuild project
- IAM role for CodeBuild
- IAM role for CodePipeline
- CodePipeline V2

---

## 2. Where Does the Source Stage Download the Repository?

The Source action gets the repository from GitHub through the CodeConnections connection.

The source artifact is stored in the CodePipeline artifact store:

```hcl
resource "aws_s3_bucket" "artifacts" {
  bucket_prefix = "${local.name}-"
}
```

Conceptually:

```text
GitHub
   ↓
Source Action
   ↓
S3 Artifact Bucket
```

The S3 bucket is used to pass artifacts between pipeline stages.

---

## 3. How Does CodeBuild Get the Source?

The CodePipeline Build action specifies:

```hcl
input_artifacts = ["source_output"]
```

The CodeBuild project specifies:

```hcl
source {
  type = "CODEPIPELINE"
}
```

Therefore, CodePipeline passes the `source_output` artifact to CodeBuild.

You do **not** manually specify the S3 path in the CodeBuild project.

Flow:

```text
GitHub
   ↓
Source Action
   ↓
source_output
   ↓
Build Action
   ↓
CodeBuild
```

CodeBuild receives and extracts the source artifact automatically.

---

## 4. Artifact Names Are Not S3 Paths

This is important.

```hcl
output_artifacts = ["source_output"]
```

and:

```hcl
input_artifacts = ["source_output"]
```

refer to an **artifact name**, not a physical S3 path.

The Source action produces:

```text
source_output
```

The Build action consumes:

```text
source_output
```

CodePipeline manages the actual S3 location.

Think:

```text
Source Action
    output: source_output
           ↓
Build Action
    input: source_output
```

---

## 5. Pipeline → Stage → Action → Resource

The hierarchy is:

```text
CodePipeline
   ├── Stage
   │     └── Action
   │
   └── Stage
         └── Action
               └── CodeBuild Project
```

For this example:

```text
CodePipeline
   │
   ├── Source Stage
   │      └── Source Action → GitHub
   │
   └── Build Stage
          └── Build Action → CodeBuild Project
```

A **CodeBuild project is not itself a CodePipeline stage/action**. The CodePipeline action invokes the CodeBuild project.

---

## 6. Can One Stage Have Multiple Actions?

Yes.

For example:

```text
Build Stage
   ├── Test Action
   ├── Security Scan Action
   └── Build Action
```

Actions in the same stage can run in parallel when their dependencies allow it.

---

## 7. Can One Action Pass Output to Another Action?

Yes.

An action can produce an output artifact:

```hcl
output_artifacts = ["build_output"]
```

and another action can consume it:

```hcl
input_artifacts = ["build_output"]
```

Typical flow:

```text
Source Stage
   Source Action
       │
       │ source_output
       ▼
Build Stage
   Build Action
       │
       │ build_output
       ▼
Deploy Stage
   Deploy Action
```

Actions in different stages normally execute sequentially.

So:

- **Same stage** → actions can run in parallel.
- **Different stages** → stages provide the normal sequential flow.
- **Artifacts** → provide data between actions.

---

## 8. How Does CodeBuild Know What to Run?

CodeBuild normally uses a `buildspec.yml` file.

For example:

```yaml
phases:
  install:
    commands:
      - pip install -r requirements.txt

  build:
    commands:
      - python app.py

  post_build:
    commands:
      - echo "Build completed"
```

The general flow is:

```text
CodeBuild receives source
        ↓
Finds buildspec.yml
        ↓
Reads phases
        ↓
Runs commands
```

If the buildspec is in the repository root, CodeBuild can use:

```text
buildspec.yml
```

---

## 9. What If the File Is Called another-spec.yml?

You can explicitly configure the CodeBuild source:

```hcl
source {
  type      = "CODEPIPELINE"
  buildspec = "another-spec.yml"
}
```

You can also specify a directory:

```hcl
source {
  type      = "CODEPIPELINE"
  buildspec = "ci/another-spec.yml"
}
```

So the repository could contain:

```text
repo/
├── buildspec.yml
├── another-spec.yml
└── ci/
    └── another-buildspec.yml
```

and CodeBuild can be configured to use the desired file.

---

# 10. What Is CodeStar Connections?

**CodeStar Connections** is AWS's mechanism for connecting AWS services to external source providers such as GitHub.

In the Terraform example:

```hcl
resource "aws_codestarconnections_connection" "github" {
  name          = local.name
  provider_type = "GitHub"
}
```

It creates a connection between AWS and GitHub.

Conceptually:

```text
GitHub
   ↓
CodeConnections / CodeStar Connection
   ↓
CodePipeline
```

It is the **connection/authentication layer**, not the build system.

---

## 11. How Does AWS Get the GitHub Credentials?

Terraform creates the connection, but the connection starts as **PENDING**.

You then authorize it through AWS:

```text
Terraform
   ↓
Creates pending connection
   ↓
AWS Console
   ↓
"Update pending connection"
   ↓
GitHub authorization
   ↓
Connection becomes available
```

You do not put a GitHub username/password directly into Terraform.

After authorization, CodePipeline references the connection using its ARN:

```hcl
ConnectionArn = aws_codestarconnections_connection.github.arn
```

The connection is managed by AWS.

---

## 12. How Does CodePipeline Know Which GitHub Repository to Use?

The connection provides the authorization, while the pipeline configuration specifies the repository:

```hcl
configuration = {
  ConnectionArn    = aws_codestarconnections_connection.github.arn
  FullRepositoryId = var.github_repo
  BranchName       = var.branch
}
```

For example:

```hcl
github_repo = "surendra/pipeline-dummy-repo"
branch      = "main"
```

So:

```text
ConnectionArn
    → Who/what is authorized

FullRepositoryId
    → Which GitHub repository

BranchName
    → Which branch
```

---

## 13. How Long Does the Connection Last?

The connection is **persistent** rather than a short-lived credential.

It normally remains available until it is:

- Deleted.
- Disconnected/revoked.
- Reauthorized or otherwise invalidated through the GitHub/AWS connection setup.

It is not normally a credential that expires after a few hours or days.

---

# 14. Important Terraform Concepts From the Discussion

### `for_each`

When using a map:

```hcl
for_each = var.instances
```

Terraform exposes:

```text
each.key
each.value
```

Example:

```hcl
variable "instances" {
  default = {
    web    = "web-server"
    api    = "api-server"
    worker = "worker-server"
  }
}
```

Then:

```hcl
tags = {
  Name = each.value
  Type = each.key
}
```

For the `web` iteration:

```text
each.key   = "web"
each.value = "web-server"
```

---

## 15. `concat()` vs `join()`

### `concat()`

`concat()` combines lists.

```hcl
concat(
  ["a", "b"],
  ["c", "d"]
)
```

Result:

```hcl
["a", "b", "c", "d"]
```

It can combine more than two lists:

```hcl
concat(
  ["a"],
  ["b"],
  ["c"],
  ["d"]
)
```

Result:

```hcl
["a", "b", "c", "d"]
```

### `join()`

`join()` converts a list of strings into one string.

```hcl
join("-", ["a", "b", "c"])
```

Result:

```text
a-b-c
```

Remember:

```text
concat() → List + List → List

join()   → List → String
```

---

## 16. `max()` and List Expansion

Terraform's `max()` expects individual numeric arguments.

This is not correct:

```hcl
max(local.my_numbers)
```

If:

```hcl
local.my_numbers = [1, 2, 3, 4, 5]
```

use:

```hcl
max(local.my_numbers...)
```

The `...` expands the list into individual arguments:

```text
max(local.my_numbers...)
        ↓
max(1, 2, 3, 4, 5)
        ↓
5
```

---

# 17. One Mental Model to Remember

For the AWS pipeline:

```text
                 GitHub
                    │
                    │ Connection
                    ▼
              Source Action
                    │
                    │ output_artifacts
                    ▼
              S3 Artifact Store
                    │
                    │ input_artifacts
                    ▼
               Build Action
                    │
                    ▼
              CodeBuild Project
                    │
                    ▼
              buildspec.yml
                    │
                    ▼
                 Commands
```

And the Terraform hierarchy is:

```text
CodePipeline
    ↓
Stages
    ↓
Actions
    ↓
Resources/services
```

The key distinction is:

```text
Stage      = grouping / sequencing boundary
Action     = actual operation inside a stage
Artifact   = data passed between actions
S3         = physical artifact storage managed by CodePipeline
CodeBuild  = service that executes build commands
buildspec  = instructions telling CodeBuild what to execute
Connection = authentication/connection between AWS and GitHub
```
