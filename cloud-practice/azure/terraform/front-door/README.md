# Terraform: Azure Front Door (minimal)

RG + a Storage Account static website as a self-contained real origin
(with one `index.html` blob so there's actual content to serve) + a
Standard Azure Front Door profile/endpoint/origin-group/origin/route
fronting it. This is the current CDN product for any new Azure
deployment -- see the note on retired alternatives below.

> ⚠️ **This creates billable resources.** Front Door Standard bills per
> GB served + a small base charge; a nearly-idle demo like this one costs
> very little but not $0. Run `terraform destroy` when done.

> ⚠️ **Front Door is blocked on Free Trial / Student subscriptions.**
> Hit this directly running `terraform apply` against a Free Trial
> subscription: the resource group, storage account, static website, and
> index.html blob all created fine, then
> `azurerm_cdn_frontdoor_profile` failed with
> `BadRequest: Free Trial and Student account is forbidden for Azure
> Frontdoor resources.` This is an account-tier restriction Azure enforces
> server-side, not a config problem — Front Door needs a Pay-As-You-Go (or
> other non-trial) subscription. The storage static website half is
> unaffected and independently useful — verified serving real content via
> `curl` straight at `azurerm_storage_account.origin.primary_web_endpoint`
> even while the Front Door resources above it failed to create.

## Usage

```bash
terraform init
terraform apply
```

Hit it through Front Door (not the origin directly) -- give it a couple
of minutes after apply for the edge configuration to propagate:

```bash
curl https://$(terraform output -raw frontdoor_endpoint_hostname)
```

## Why the origin is a Storage static website, not a "real" app

Front Door needs something to front. Rather than requiring you to stand
up a VM or App Service first, this pairs it with the cheapest possible
real HTTPS origin: Blob Storage's static website feature, which serves
plain HTML with no server to manage. Point `azurerm_cdn_frontdoor_origin`'s
`host_name` at the `app-service/` or `load-balancer/` project's output
instead if you want to front one of those.

## What's deliberately not here

Standard tier only (Premium adds a managed WAF, bot protection, and
Private Link origins), no custom domain (this uses the default
`*.azurefd.net` hostname via `link_to_default_domain = true`), no caching
rules/compression config, no rule set (header rewriting, redirects
beyond the built-in HTTPS redirect).

## Teardown

```bash
terraform destroy
```
