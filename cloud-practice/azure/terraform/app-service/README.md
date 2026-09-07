# Terraform: Azure App Service (minimal)

RG + an App Service Plan (Free "F1" tier) + a Linux Web App on the Node
18 runtime, no code deployed. The always-on PaaS sibling to Functions'
scale-to-zero model -- pick this when you need a continuously-running
process, Functions when you need event-triggered/bursty compute.

> ⚠️ The "F1" Free tier genuinely costs $0, but comes with real limits:
> 60 CPU-minutes/day, no custom domain or TLS, no "Always On" (the app can
> idle out and cold-start on the next request). Swap `sku_name` to `"B1"`
> for a realistic always-on test -- that one **does** bill hourly. Run
> `terraform destroy` when done either way, to free the reserved name.

## Usage

```bash
terraform init
terraform apply
curl https://$(terraform output -raw default_hostname)
```

Deploy actual code (separate from Terraform, same as the Functions
project):

```bash
az webapp up --name <the app name> --resource-group rg-appservice-demo
```

## What's deliberately not here

No deployment slots, no custom domain/TLS binding, no Application
Insights, no VNet integration, no scaling rules (F1/B1 don't autoscale
anyway -- that needs at least the Standard tier).

## Teardown

```bash
terraform destroy
```
