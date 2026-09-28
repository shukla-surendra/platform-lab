# Terraform lab: adopt manually-created Azure resources, then change them

The real-world situation: somebody built infrastructure by hand (portal / `az`
CLI), an app is already using it, and now it has to come under Terraform
**without being recreated and without losing data**. After that, all changes
go through code.

```
 Phase 1: MANUAL          Phase 2: IMPORT              Phase 3: MODIFY
 az CLI creates    ──▶    Terraform adopts it    ──▶   Terraform changes it
 8 resources              plan = 8 import, 0 change    in place, 0 destroy
 app writes data          data + identity unchanged    data + identity unchanged
```

## What gets built (all near-free)

| Resource | Name | Notes |
|---|---|---|
| Resource group | `rg-import-lab` | tags `env=lab owner=manual` |
| Storage account | `stimport<6 hex>` | StorageV2 / LRS / Hot, the app's datastore |
| Blob container | `appdata` | private |
| NSG + rule | `nsg-import-lab` / `allow-ssh` | inbound 22 from `203.0.113.0/24` |
| VNet + subnet | `vnet-import-lab` / `snet-app` | `10.50.0.0/16`, `10.50.1.0/24`, NSG attached |

> ⚠️ The storage account costs fractions of a cent while it exists. VNets and NSGs are free. Run `scripts/99-cleanup.sh` when you're done.

## Layout

```
scripts/01-manual-create.sh   phase 1: az CLI creates everything, writes .lab.env + tf/terraform.tfvars
program/app.sh                the "application": write / read / check orders in blob storage
tests/verify.sh <phase>       assertions for: manual | imported | modified | drift
stages/02-import/             main.tf matching reality + imports.tf (import blocks)
stages/03-modify/             main.tf with the changes, no imports.tf
scripts/use-stage.sh <stage>  copies a stage's .tf files into tf/
tf/                           the Terraform working dir (versions.tf lives here; state lands here)
scripts/99-cleanup.sh         az group delete + wipe local state
```

`versions.tf` and the state file stay in `tf/` the whole time. Only
`main.tf` and `imports.tf` get swapped. This is the same as editing one
config over time, but you can diff the stages side by side.

---

## Phase 1: create by hand

```bash
az login                              # if needed
scripts/01-manual-create.sh
program/app.sh write                  # run it 2–3 times
program/app.sh read
tests/verify.sh manual
```

The script records two **identity fingerprints** in `.lab.env`:

- `SA_CREATED`: the storage account's `creationTime`
- `VNET_GUID`: the VNet's `resourceGuid`

Neither value can be changed. If Terraform ever destroys and recreates the
resource, even under the same name, these values change. Every test phase
checks them, so a test pass proves "adopted and changed", not
"silently replaced".

## Phase 2: import

```bash
scripts/use-stage.sh 02-import
terraform -chdir=tf init
terraform -chdir=tf plan              # READ THIS CAREFULLY
```

The **only** acceptable result is:

```
Plan: 8 to import, 0 to add, 0 to change, 0 to destroy.
```

A non-zero "change" means your HCL doesn't match reality, and `apply` would
modify a live resource you only meant to adopt. Fix the HCL, not Azure.

### The two gotchas this lab actually hit

1. **Provider defaults ≠ CLI/portal defaults.** The first plan showed:
   ```
   ~ resource "azurerm_subnet" "app" {
       ~ default_outbound_access_enabled = false -> true
   ```
   Newer `az` creates subnets as "private" (no implicit outbound internet),
   but the azurerm provider still defaults the attribute to `true`. If you
   applied without reading, the import would have re-opened outbound
   access. The fix is `default_outbound_access_enabled = false` in the HCL.
   Same story with `allow_nested_items_to_be_public` on the storage account:
   `az` defaults it to false and the provider defaults it to true, so the
   config sets it explicitly.
2. **Associations are not real objects.** `azurerm_subnet_network_security_group_association`
   is just the subnet's `networkSecurityGroup` property, so its import ID is
   the **subnet ID**. Check the "Import" section at the bottom of each
   resource's provider docs page for the exact ID format.

Then:

```bash
terraform -chdir=tf apply
tests/verify.sh imported              # 15 checks incl. "plan is clean (exit 0)"
```

### Alternative ways to import (try them)

- **CLI, one at a time** (the pre-1.5 way; not previewed, writes straight to state):
  ```bash
  terraform -chdir=tf state rm azurerm_network_security_rule.allow_ssh
  terraform -chdir=tf import azurerm_network_security_rule.allow_ssh \
    "/subscriptions/$SUB_ID/resourceGroups/rg-import-lab/providers/Microsoft.Network/networkSecurityGroups/nsg-import-lab/securityRules/allow-ssh"
  ```
- **Let Terraform write the HCL for you**: remove a `resource` block (keep its
  `import` block), then:
  ```bash
  terraform -chdir=tf plan -generate-config-out=generated.tf
  ```
  The generated file lists *every* attribute, including computed and
  default ones. Treat it as a first draft, trim it, and rerun plan until it's clean.

## Drift: someone changes Azure by hand again

```bash
source .lab.env
az network nsg rule update -g $RG --nsg-name nsg-import-lab -n allow-ssh --destination-port-ranges 2222
az group update -n $RG --set tags.hotfix=yes
tests/verify.sh drift                 # expects plan exit code 2
terraform -chdir=tf plan              # shows 2222 -> 22 and hotfix tag -> null
terraform -chdir=tf apply             # Terraform puts it back
```

Terraform wins, because the code is the source of truth. If the hotfix was
*correct*, the right move is to put it into the HCL, not to keep
re-applying over it.

## Phase 3: modify through Terraform

```bash
diff stages/02-import/main.tf stages/03-modify/main.tf
scripts/use-stage.sh 03-modify        # also deletes imports.tf: those resources are in state now
terraform -chdir=tf plan              # expect: 2 to add, 6 to change, 0 to destroy
terraform -chdir=tf apply
program/app.sh write                  # the app keeps working
tests/verify.sh modified
```

| Change | Plan symbol |
|---|---|
| tags `owner=platform-team`, `managed_by=terraform` on RG/SA/VNet/NSG | `~` |
| blob versioning + 7-day blob & container soft delete | `~` |
| `allow-ssh` source `203.0.113.0/24` → `198.51.100.0/24` | `~` |
| `snet-app` gets `Microsoft.Storage` service endpoint | `~` |
| new rule `allow-https` (443) | `+` |
| new subnet `snet-data` | `+` |
| `prevent_destroy` on the storage account | (no API change) |

### Prove the safety net works

Renaming a storage account forces replacement (`-/+`). With `prevent_destroy`,
Terraform refuses at plan time:

```bash
terraform -chdir=tf plan -var storage_account_name=stimportrenamed
# Error: Instance cannot be destroyed
```

## More experiments

- Give `azurerm_virtual_network.lab` an inline `subnet {}` block while the
  separate `azurerm_subnet` resources exist, and watch the two fight on every plan.
- Remove `allow_nested_items_to_be_public = false` from stage 02 before the
  import and read the diff it produces.
- Change `account_replication_type` to `GRS` (in place) vs. `account_kind`
  to `BlobStorage` (replacement, blocked by `prevent_destroy`).
- `terraform -chdir=tf state rm azurerm_subnet.data`: Terraform "forgets" it
  but Azure keeps it. The next plan wants to *create* it and fails because it
  already exists. Bring it back with an `import` block.

## Cleanup

```bash
scripts/99-cleanup.sh
```

This uses `az group delete` because `prevent_destroy` makes
`terraform destroy` refuse, which is the point of `prevent_destroy`.
