# Workspace concepts: state paths, where workspace info lives, what goes in git

## 1. A workspace is a separate state file

Same code, one state per workspace. `terraform.workspace` (a built-in string) is the
current name; use it in resource names and to pick per-env settings.

## 2. How the backend picks the path "dynamically"

You never write the workspace name in the backend block. Backend blocks cannot use
variables or `terraform.workspace`. You write a template; Terraform fills in the workspace.

```hcl
backend "s3" {
  bucket               = "my-state-bucket"
  key                  = "ec2/terraform.tfstate"
  workspace_key_prefix = "env"
  use_lockfile         = true
}
```

| Workspace | State object |
|---|---|
| dev     | `s3://my-state-bucket/env/dev/ec2/terraform.tfstate` |
| qa      | `s3://my-state-bucket/env/qa/ec2/terraform.tfstate` |
| prod    | `s3://my-state-bucket/env/prod/ec2/terraform.tfstate` |
| default | `s3://my-state-bucket/ec2/terraform.tfstate` (no prefix) |

- `terraform init` configures the bucket once; `workspace select` only changes which object is used (no re-init).
- Locking is per workspace path: a `.tflock` object appears beside that workspace's state during plan/apply and does not block other workspaces.
- Local backend equivalent: `terraform.tfstate.d/<workspace>/terraform.tfstate`.

## 3. Where workspace information is stored

Two separate things:

**a) The list of workspaces = the state files themselves.** No config file says "dev exists".

| Backend | Where |
|---|---|
| local | one folder per workspace under `terraform.tfstate.d/` |
| s3    | objects under `<workspace_key_prefix>/` |

`terraform workspace list` just lists those. With S3, everyone with bucket access sees the same
list, and a new teammate gets it after `terraform init`.

**b) The currently selected workspace = `.terraform/environment`**, a one-line file containing
the name (e.g. `qa`). It is per checkout, so each person and each CI job has their own;
`workspace select` is a personal action, not a shared setting.

```bash
ls terraform.tfstate.d/
cat .terraform/environment
```

## 4. What goes in git

Do **not** commit:
```
.terraform/
*.tfstate*
terraform.tfstate.d/
```
State can contain secrets and changes on every apply; with a remote backend it lives in the
bucket anyway. `.terraform/environment` is just your personal pointer.

Do commit: `*.tf` (including the `backend` block, no secrets in it), `vars/*.tfvars`,
and `.terraform.lock.hcl` (pins provider versions).

In CI, create/select the workspace on every run, so nothing about workspaces needs committing:
```bash
terraform init
terraform workspace select dev || terraform workspace new dev
```

## 5. Risk to remember

The state bucket is the source of truth. If someone deletes `env/prod/...`, Terraform forgets
prod exists even though the resources still run in AWS. Keep the bucket private, versioned and
encrypted, and restrict `env/prod/*` to the prod deploy role.

## See also
- `03-ec2/`: workspaces with local state
- `04-ec2-s3-backend/`: same code with the S3 backend
