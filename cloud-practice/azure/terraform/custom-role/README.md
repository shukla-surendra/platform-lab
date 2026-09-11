# Terraform: Azure custom role (resource-group scope)

RG + a custom role definition scoped to that RG only (`*/read` plus VM
start/restart, nothing else) + a role assignment binding it to whoever
applies this.

Role definitions and assignments aren't billable -- the only cost here is
the (empty) resource group, which is free too.

## Usage

```bash
terraform init
terraform apply
```

Verify the role exists and is scoped correctly:

```bash
az role definition list \
  --custom-role-only true \
  --scope $(terraform output -raw resource_group_id) \
  --query "[].{name:roleName, scope:assignableScopes}" -o table
```

Verify the assignment resolved:

```bash
az role assignment list \
  --scope $(terraform output -raw resource_group_id) \
  --query "[].{principal:principalName, role:roleDefinitionName}" -o table
```

## What's deliberately not here

Only one action set (`*/read`, VM start/restart) -- no write/delete
`actions`, no `data_actions` (no data-plane access), no `not_actions`
carve-outs since the allow list is already minimal. Assigned only to the
applying principal, not to a real "operator" user or group.

## Teardown

```bash
terraform destroy
```
