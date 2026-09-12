# Databricks Lakehouse Monitoring

**Category:** ML monitoring / observability (Databricks-native)

## What it is

Databricks' built-in monitoring capability, part of Unity Catalog. You
attach a monitor directly to a Delta table on a schedule — no separate
job or report code required.

## What it's used for

- Has an **InferenceLog** profile type built specifically for ML: tracks
  prediction drift, label drift, feature drift, and model performance
  metrics over time.
- If you're using **Databricks Model Serving**, requests/responses
  auto-log to an inference table, which plugs straight into Lakehouse
  Monitoring with minimal setup — no separate logging code needed.
- Output is auto-generated Delta tables plus an auto-generated dashboard.

## Comparison vs. [Evidently](../evidently/README.md)

- **Less customizable** than Evidently — no fine-grained custom
  tests/thresholds like Evidently's `Report`/`TestSuite` API.
- **Zero glue code** if training, serving, and storage are fully inside
  Databricks/Unity Catalog — the monitor just watches a table.
- Evidently is preferable when you need **portability** across
  non-Databricks environments, or **custom test logic** beyond what
  Lakehouse Monitoring's presets cover.
- Not mutually exclusive: a common pattern is Lakehouse Monitoring as the
  always-on baseline, with Evidently pulled in for deeper one-off
  investigations.
