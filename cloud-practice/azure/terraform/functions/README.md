# Terraform: Azure Functions (minimal)

RG + a Storage Account (the platform's own internal state, not your
data) + a Consumption ("Y1") plan + a Linux Function App running the
Node 18 stack, empty (no function code deployed).

Coming from AWS Lambda? [`AWS_LAMBDA_CONTRAST.md`](AWS_LAMBDA_CONTRAST.md)
covers where the two platforms actually differ — why Azure makes you
choose a Service Plan at all, the Trigger-vs-Bindings split, packaging/
deployment gotchas, and execution limits side by side.

> ⚠️ **This creates billable resources**, though a Consumption plan
> scales to zero and has a generous monthly free grant (1M executions) --
> an idle demo app like this one should cost close to nothing, but the
> Storage Account underneath it still bills a small, non-zero amount.
> Run `terraform destroy` when done.

## Usage

```bash
terraform init
terraform apply
```

Deploying actual function code is a separate step Terraform doesn't do --
scaffold and publish with the Azure Functions Core Tools:

```bash
func init my-function --javascript
cd my-function && func new --name HttpExample --template "HTTP trigger"
func azure functionapp publish $(terraform output -raw function_app_name)
```

## What's deliberately not here

No deployed function code (this only provisions the empty app), no
Application Insights, no VNet integration, no deployment slots, no
custom domain/TLS.

## Teardown

```bash
terraform destroy
```
