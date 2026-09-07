# Terraform: Azure Key Vault (minimal)

RG + a standard-SKU Key Vault + an access policy granting whoever applies
this Get/List/Set/Delete/Purge on secrets + one demo secret.

> ⚠️ **This creates billable resources**, though Key Vault's cost for light
> use (a handful of operations) is a fraction of a cent -- one of the
> cheapest services here to leave running. Run `terraform destroy` when done.

## Usage

```bash
terraform init
terraform apply
```

Read the secret back (proves the access policy actually works):

```bash
az keyvault secret show \
  --vault-name $(terraform output -raw key_vault_name) \
  --name demo-secret --query value -o tsv
```

## What's deliberately not here

`purge_protection_enabled = false` deliberately, so `terraform destroy`
can fully remove the vault -- flip it on before storing anything real,
since with it on a deleted vault's name stays reserved for the whole
retention window and can't be un-set afterward. No RBAC-mode
authorization (this uses the older access-policy model), no private
endpoint, no key/certificate objects (secrets only), no diagnostic
logging.

## Teardown

```bash
terraform destroy
```
