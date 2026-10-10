# Databricks-only examples (not runnable locally)

These need a real Databricks workspace. Open-source Spark does not include Auto Loader, Lakeflow
Declarative Pipelines, Unity Catalog or Asset Bundles. The files here are reference material
for the matching docs; replace the `<placeholders>` before use.

| File | Shows | Doc |
|---|---|---|
| `autoloader.py` | Incremental file ingestion with schema evolution and a rescued-data column | [04](../docs/04-ingestion-and-streaming.md) |
| `lakeflow_pipeline.py` | Declarative pipeline: streaming tables, expectations, CDC with SCD2 | [05](../docs/05-pipelines-jobs-and-cicd.md) |
| `databricks.yml` | An Asset Bundle: one job + one pipeline with dev/prod targets | [05](../docs/05-pipelines-jobs-and-cicd.md) |
| `unity_catalog.sql` | Catalog/schema layout, grants, masks, row filters, volumes | [06](../docs/06-unity-catalog-governance.md) |

Cheapest way to try them: a Databricks **Free Edition** workspace (serverless compute only), then
check which features it supports.
