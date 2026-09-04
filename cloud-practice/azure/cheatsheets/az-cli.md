# `az` CLI Cheatsheet

One-page recall, cross-cutting (not tied to one service module). AWS CLI equivalent noted where the mapping is direct — most of it isn't 1:1, see [`../docs/entra-id/`](../docs/entra-id/architecture.md) for why.

## Mental model
`az login` → short-lived OAuth token (no Access Key ID/Secret Access Key to generate or paste — closer to `aws sso login` than `aws configure`). Every other command runs against whatever tenant+subscription that token is scoped to.

## Auth & subscription
```bash
az login                                       # aws: aws sso login
az account show                                # aws: aws sts get-caller-identity
az account list --output table                 # every subscription this login can see
az account set --subscription "<name-or-id>"   # aws: aws configure set / --profile
az logout
```

## Resource groups
No AWS equivalent (closest: a CFN stack's boundary, or just tags) — in Azure every resource belongs to exactly one from creation, not optional.
```bash
az group list --output table
az group show   --name <rg>
az group delete --name <rg> --yes --no-wait     # deletes everything inside it
```

## Identity / RBAC (module 4 — [`../docs/entra-id/`](../docs/entra-id/architecture.md))
```bash
az ad signed-in-user show                                        # who am I
az role assignment list --assignee <object-id> --output table    # aws: aws iam list-attached-*-policies
az role assignment create --assignee <object-id> --role "AcrPull" --scope <resource-id>
az role definition list --query "[].roleName" --output tsv       # built-in role names
az identity show --resource-group <rg> --name <identity>         # inspect a Managed Identity
```

## VNet (module 1 — [`../docs/vnet/`](../docs/vnet/architecture.md))
```bash
az network vnet list --output table              # aws: aws ec2 describe-vpcs
az network vnet subnet list --resource-group <rg> --vnet-name <vnet> --output table
az network nsg list --output table                # aws: aws ec2 describe-security-groups (NSG ≠ SG semantics though)
az network nsg rule list --resource-group <rg> --nsg-name <nsg> --output table
```

## Blob Storage (module 5 — [`../docs/blob-storage/`](../docs/blob-storage/architecture.md))
```bash
az storage account list --output table              # aws: aws s3api list-buckets (account, not bucket, is the unit)
az storage container list --account-name <acct>       # aws: aws s3 ls
az storage blob list --account-name <acct> --container-name <container> --output table
az storage blob upload --account-name <acct> --container-name <container> --name <blob> --file <path>
```

## AKS (aws: eksctl / aws eks)
```bash
az aks list --output table
az aks show --resource-group <rg> --name <cluster>
az aks get-credentials --resource-group <rg> --name <cluster> --overwrite-existing
                                                    # aws: aws eks update-kubeconfig --name <cluster>
az aks nodepool list --resource-group <rg> --cluster-name <cluster> --output table
az aks stop  --resource-group <rg> --name <cluster>    # stop node-pool billing without deleting the cluster
az aks start --resource-group <rg> --name <cluster>
```

## ACR (aws: aws ecr)
```bash
az acr login --name <registry>                     # aws: aws ecr get-login-password | docker login
az acr repository list --name <registry> --output table
az acr repository show-tags --name <registry> --repository <repo> --output table
az acr build --registry <registry> --image <repo>:<tag> <path>   # builds INSIDE ACR, no local docker needed
```

## Cost (aws: aws ce get-cost-and-usage)
```bash
az consumption usage list --output table    # thin CLI surface -- Portal Cost Analysis is faster for actually reading it
```
Real cost-control move: **Portal → Cost Management + Billing → Cost analysis**, scoped to the resource group. The CLI here is more for scripting than exploring.

## Global flags
```bash
--output table   # -o table    human-readable (default is JSON)
--output tsv      # -o tsv      for piping into scripts
--query "<JMESPath>"   # same JMESPath as aws --query, one of the few things that transfers directly

az acr show --name <registry> --query loginServer --output tsv   # example: extract exactly one field
```
```bash
az configure   # interactive: set default --resource-group/--location so you stop retyping them
az upgrade
```

## Terraform note
`terraform`'s `azurerm` provider reuses `az login`'s cached credentials automatically (`provider "azurerm" { features {} }`, no explicit auth block needed) — same token-based flow as the CLI itself, not a separate credential to manage.
