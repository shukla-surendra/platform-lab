# Requirements

| Need | Version / detail | Check |
|---|---|---|
| Azure subscription | Any, with permission to create resources **and role assignments** (Owner, or Contributor + User Access Administrator) | `az account show` |
| Azure CLI | 2.50+ | `az version` |
| CLI `datafactory` extension | installed on first use (`az extension add --name datafactory`) | `az extension list` |
| Terraform | >= 1.5 | `terraform version` |
| azurerm provider | `~> 5.0` (downloaded by `terraform init`) | |
| Resource providers registered | `Microsoft.DataFactory`, `Microsoft.Storage` | `az provider show -n Microsoft.DataFactory --query registrationState -o tsv` |
| Bash | for `scripts/run_pipeline.sh` | |

Register a provider if it says `NotRegistered`: `az provider register --namespace Microsoft.DataFactory`

Cost: effectively zero. One run of one Copy activity is a fraction of a cent, storage holds a few bytes, and the trigger is off.
