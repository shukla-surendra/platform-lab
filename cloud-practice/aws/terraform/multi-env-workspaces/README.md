# Multi-environment Terraform on AWS — the **workspace** way

Same infra as [`../multi-env-platform`](../multi-env-platform) (folder-per-env), but
using **one root module + Terraform workspaces**. Compare the two side by side.

```
main.tf versions.tf variables.tf outputs.tf   <- ONE copy of the code
vars/dev.tfvars qa.tfvars stage.tfvars prod.tfvars   <- only the differences
modules/                                      <- same modules as the folder version
```

## How it works

- One backend block; each workspace gets its own state file:
  `env/dev/terraform.tfstate`, `env/qa/terraform.tfstate`, …
- `terraform workspace select <env>` picks the state; `-var-file=vars/<env>.tfvars` picks the config.
- A `check` block fails the run if workspace and `environment` var disagree.

```bash
make validate-all            # offline
make plan  ENV=dev           # init + select/create workspace + plan
make apply ENV=dev
terraform workspace list     # see all envs
```

## Folders vs workspaces

| | Folders (`multi-env-platform`) | Workspaces (this) |
|---|---|---|
| Code duplication | thin per-env wrappers (backend, vars, module calls) | none: single root |
| Target env visible? | yes, from your `cd` | no: hidden in `workspace show` |
| Wrong-env risk | low | higher: forgot to switch, or wrong `-var-file` |
| Different backend/account/provider per env | easy | awkward (one backend block) |
| Env-specific resources / diverging code | easy | needs `count`/conditionals |
| Adding an env | new folder | new tfvars + `workspace new` |
| Best for | prod-grade, separate accounts, teams | identical envs, small teams, ephemeral/feature envs |

**Rule of thumb:** workspaces are good when environments are *identical copies*
(especially short-lived ones, e.g. one per PR). Once prod needs its own account, approvals,
or different shape, folders (or separate pipelines/repos) win. Many teams combine them:
folders for long-lived envs, workspaces for ephemeral previews.

## Setup

Same as the folder version: run `bootstrap/` once (state objects live under `env/<name>/*`
here), set the bucket in `versions.tf`, copy `pipeline/terraform-apply.yml` to
`.github/workflows/`, and configure GitHub Environments with reviewers on stage/prod.
