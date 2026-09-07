# Terraform: Azure Cosmos DB (minimal)

RG + a Cosmos DB account (SQL/Core API) with `free_tier_enabled = true` +
one database + one container (autoscale, max 1000 RU/s), partitioned on
`/id`.

> ⚠️ **Free-tier is per-subscription, not per-account.** Azure grants
> exactly one free Cosmos DB account (1000 RU/s + 25GB storage, genuinely
> $0) per subscription -- if you've already claimed it elsewhere, this
> `apply` will fail rather than silently billing you for a second one.
> Set `free_tier_enabled = false` if that happens (and note it then
> **does** bill). Run `terraform destroy` when done regardless.

## Usage

```bash
terraform init
terraform apply
```

Insert/read a document with the Azure CLI (or any Cosmos SDK) using the
endpoint + key from outputs:

```bash
az cosmosdb sql container throughput show \
  --account-name $(terraform output -raw cosmosdb_endpoint | sed -E 's#https://([^.]+).*#\1#') \
  --resource-group rg-cosmos-demo \
  --database-name demo-database --name demo-container
```

## What's deliberately not here

Only the SQL (Core) API is shown -- Cosmos DB also emulates MongoDB,
Cassandra, Gremlin, and Table wire protocols via different `kind`/API
resource types, not covered here. No multi-region writes, no private
endpoint, no RBAC-based data-plane access (this uses the account's
primary key), no backup-policy override.

## Teardown

```bash
terraform destroy
```
