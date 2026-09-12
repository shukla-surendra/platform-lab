# Terraform: Azure Data Factory (minimal ETL pipeline)

A Storage Account with two containers (`raw`, `processed`) + a Data
Factory wired with a Linked Service, two Datasets, and a one-Copy-activity
Pipeline that moves a file from `raw/` to `processed/`. This is the
standard, interview-canonical answer to "what does Azure use for ETL" —
verified live end-to-end below, not just deployed.

> ⚠️ **This creates billable resources.** Data Factory itself has a small
> per-pipeline-run + per-activity charge (a few cents per run, not
> ongoing); storage is pennies. Nothing here runs continuously — no
> schedule trigger is configured, see "What's deliberately not here."
> Run `terraform destroy` when done.

## What Azure service is "the ETL one"

**Azure Data Factory (ADF)** — a managed orchestration service, not a
compute engine itself. Its job is coordinating movement and (optionally)
transformation of data on a schedule or trigger, largely by calling out to
other services that do the actual work. The vocabulary, all created by
this module:

- **Linked Service** — connection info to one external system (here: this
  storage account's connection string). Reusable across many
  datasets/pipelines that need to talk to the same system.
- **Dataset** — a named pointer to one specific piece of data inside a
  Linked Service (a container + filename, here). Pipelines reference
  datasets by name, never raw paths directly.
- **Pipeline** — the actual workflow: an ordered (optionally branching)
  set of **Activities**. This demo has exactly one: a `Copy` activity from
  the `raw` dataset to the `processed` dataset.
- **Trigger** *(not created here — see below)* — what actually starts a
  pipeline run: a cron-like schedule, a tumbling window (backfill-aware,
  incremental), or an event (a blob landing in a container).

**Where ADF's own compute ends and a "real" transform engine begins**: a
`Copy` activity (what this demo uses) runs entirely on ADF's own
Integration Runtime — no Spark, no cluster, just a managed data-movement
service. The moment you need actual *transform* logic beyond copy/reshape
— joins, aggregations, dedup — ADF either uses its own Spark-backed
"Mapping Data Flows" feature, or (the more common real-world pattern) a
pipeline activity that triggers a Databricks notebook or Synapse Spark
job and waits for it to finish. ADF orchestrates; something else usually
computes.

## Usage

```bash
cd cloud-practice/azure/terraform/data-factory
terraform init
terraform apply
```

## Run the pipeline and verify the copy

Nothing runs automatically (no trigger is configured — see below), so
kick off a run by hand and watch it:

```bash
DF_NAME=$(terraform output -raw data_factory_name)
RG_NAME=$(terraform output -raw resource_group_name)
PL_NAME=$(terraform output -raw pipeline_name)

RUN_ID=$(az datafactory pipeline create-run \
  --factory-name "$DF_NAME" --resource-group "$RG_NAME" --name "$PL_NAME" \
  --query runId -o tsv)

# poll until it's done (Succeeded in ~1 minute for this file size)
az datafactory pipeline-run show \
  --factory-name "$DF_NAME" --resource-group "$RG_NAME" --run-id "$RUN_ID" \
  --query status -o tsv
```

Confirm the file actually moved:

```bash
SA_NAME=$(terraform output -raw storage_account_name)
KEY=$(az storage account keys list --account-name "$SA_NAME" --query "[0].value" -o tsv)
az storage blob download --account-name "$SA_NAME" --account-key "$KEY" \
  --container-name processed --name sample.csv --file /tmp/processed_sample.csv
cat /tmp/processed_sample.csv
```

You should see the same 3 rows that were seeded into `raw/sample.csv` at
`terraform apply` time, now also present under `processed/`.

## Why a Copy activity, not a Data Flow

A `Copy` activity is the simplest possible real pipeline — exactly enough
to demonstrate Linked Service → Dataset → Pipeline → (manual) Trigger
without also standing up a Spark-backed Mapping Data Flow, which needs its
own compute (a Data Flow debug cluster) and meaningfully more cost/startup
latency for a first exploration. Point the `source`/`sink` datasets at
different formats (`DelimitedTextSource`/`ParquetSink`, etc.) or add a
`Mapping Data Flow` activity referencing a `azurerm_data_factory_data_flow`
resource to go from "move" to "transform."

## What's deliberately not here

No trigger (schedule/tumbling-window/event) — pipeline runs are manual
(`az datafactory pipeline create-run`) so nothing bills or executes
unexpectedly after `apply`; add an `azurerm_data_factory_trigger_schedule`
pointed at this pipeline if you want it to run on a cadence. No Managed
Identity (the Linked Service uses the storage account's connection
string/key directly — a real deployment would use ADF's system-assigned
identity + an RBAC role on the storage account instead). No Mapping Data
Flow / actual transform logic (see above). No git integration
(`github_configuration`/`vsts_configuration` on `azurerm_data_factory`) —
that's for a team's CI/CD workflow around pipeline authoring, not a solo
demo.

## Teardown

```bash
terraform destroy
```
