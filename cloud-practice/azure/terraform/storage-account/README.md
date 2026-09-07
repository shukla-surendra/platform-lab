# Terraform: Azure Storage Account (minimal)

RG + a `StorageV2`/LRS/Hot Storage Account + one private Blob container.
The storage account name gets a random 6-char suffix since these names
must be globally unique across all of Azure, not just your subscription.

> ⚠️ **This creates billable resources**, though a nearly-empty storage
> account with no traffic costs fractions of a cent/month -- this is one
> of the cheapest services to leave running by mistake, but still not
> literally free. Run `terraform destroy` when done.

## Usage

```bash
terraform init
terraform apply
```

Try uploading something (Azure CLI, not Terraform's job):

```bash
az storage blob upload \
  --account-name $(terraform output -raw storage_account_name) \
  --container-name demo-container \
  --name hello.txt --file ./hello.txt \
  --connection-string "$(terraform output -raw primary_connection_string)"
```

## What's deliberately not here

No lifecycle management rules, no versioning/soft-delete, no static
website hosting, no CORS rules, no private endpoint (this uses the public
blob endpoint with a private *container* -- container-level access
control, not network-level isolation).

## Teardown

```bash
terraform destroy
```
