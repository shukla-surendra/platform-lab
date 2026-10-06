# Azure Data Factory tutorial (Terraform)

Checked *(verified)*: `terraform validate` passes and `terraform plan` shows **13 resources to add**. **Not applied yet**: the run results below are what you should see when you do.

Requirements: see [REQUIREMENTS.md](REQUIREMENTS.md). This builds on `../data-factory` (one hard-coded Copy using a storage key); here the pipeline is parameterized and uses managed identity.

## ADF in one picture

```
Trigger ──starts──▶ Pipeline ──contains──▶ Activity (Copy)
                                              │ reads/writes via
                                           Dataset (WHAT data: container + file + format)
                                              │ uses
                                        Linked service (HOW to connect: endpoint + auth)
```

| Concept | Meaning | In `main.tf` |
|---|---|---|
| **Linked service** | A connection (like a connection string) | `ls_storage` |
| **Dataset** | A named view of data inside it (path, format) | `ds_raw_csv`, `ds_processed_csv` |
| **Activity** | One step (Copy, Lookup, Web, ForEach...) | `CopyRawToProcessed` |
| **Pipeline** | A group of activities, with parameters | `pl_copy_file` |
| **Trigger** | When a pipeline runs (schedule, event, tumbling window) | `tr_daily` (off) |
| **Integration runtime** | The compute that moves data (the default Azure one here) | implicit |

## What this teaches

- **Managed identity**: the factory authenticates as itself. No keys. The linked service holds only an endpoint; the access comes from the **role assignment**.
- **Parameters**: `fileName` flows `pipeline parameter -> dataset parameter -> file path`, via expressions like `@pipeline().parameters.fileName`. One dataset serves any file.
- **Trigger as a separate object** you start and stop without touching the pipeline.

## Tutorial

### 1. Deploy
```bash
az login
terraform init
terraform apply          # ~2 min
```

### 2. Run the pipeline
```bash
./scripts/run_pipeline.sh              # copies orders.csv
```
Expected: statuses `InProgress` then `Succeeded`, then the three CSV rows printed from `processed/orders.csv`.

**If it fails with a 403 / AuthorizationPermissionMismatch:** the role assignment takes up to ~5 minutes to propagate. Wait and run again.

### 3. Use the parameter
Upload another file and run the same pipeline for it:
```bash
SA=$(terraform output -raw storage_account_name)
printf 'id,name\n1,ada\n2,grace\n' > /tmp/people.csv
az storage blob upload --account-name $SA --container-name raw --name people.csv --file /tmp/people.csv --auth-mode key
./scripts/run_pipeline.sh people.csv
```
Same pipeline, same datasets, different file. That is the point of parameters.

### 4. Look at it in the portal
Portal > Data factories > `adf-tutorial-...` > **Launch studio**:
- **Author**: open `pl_copy_file`, click the Copy activity, check Source/Sink (the dataset parameter is filled with `@pipeline().parameters.fileName`).
- **Monitor** > Pipeline runs: your runs, with duration and rows copied.

> Terraform owns these objects. Edits made in the studio are **not** saved to Terraform and will be reverted by the next `terraform apply`. Change `main.tf` instead.

### 5. Make it fail on purpose (learn to debug)
```bash
./scripts/run_pipeline.sh nope.csv
```
Expected: `Failed`, with a "blob does not exist" message. In Monitor, click the failed run, then the activity's error icon.

### 6. Turn on the schedule
```bash
az datafactory trigger start -g $(terraform output -raw resource_group_name) \
  --factory-name $(terraform output -raw data_factory_name) --name tr_daily
```
Then stop it so it doesn't keep running:
```bash
az datafactory trigger stop  -g ... --factory-name ... --name tr_daily
```
Note: Terraform created it with `activated = false`. If you start it by CLI, `terraform apply` will want to switch it back off.

### 7. Experiments
- Add a second activity (e.g. a Web activity or `Delete`) in `activities_json` with `dependsOn`.
- Change `frequency = "Hour"` and watch `terraform plan`.
- Remove the `azurerm_role_assignment` and apply: the next run fails with 403. That shows the identity does nothing until it is granted a role.

## Cleanup
```bash
terraform destroy
```
(Everything lives in `rg-adf-tutorial`; deleting the resource group also works.)

## Troubleshooting

| Symptom | Cause |
|---|---|
| `AuthorizationFailed` creating the role assignment | You lack Owner / User Access Administrator |
| Run fails 403 right after apply | Role propagation delay, wait ~5 min |
| `MissingSubscriptionRegistration` | Register `Microsoft.DataFactory` (see REQUIREMENTS.md) |
| `az datafactory` not found | `az extension add --name datafactory` |
