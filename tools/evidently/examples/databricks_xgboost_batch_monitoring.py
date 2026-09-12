"""
Evidently drift/quality monitoring for an XGBoost batch classifier on Databricks.

Context: model scores a batch every 4 hours; this runs as the downstream task
in the same Databricks Workflow, right after the scoring task.

Labels usually lag scoring, so this is split conceptually into two runs:
  - DataDriftPreset: safe to run immediately (features + predictions only)
  - ClassificationPreset: run later, once ground truth ("actual_label") has
    landed in ml_monitoring.batch_predictions for this batch window
"""

import mlflow
# NOTE: current evidently (0.7.x) moved the classic Report/ColumnMapping
# API under `evidently.legacy` - the presets/behavior are unchanged.
from evidently.legacy.report import Report
from evidently.legacy.metric_preset import DataDriftPreset, ClassificationPreset
from evidently.legacy.pipeline.column_mapping import ColumnMapping

# Reference = training-time snapshot: features + true label + model's own
# prediction on that same data. Lives in Unity Catalog as a Delta table.
reference_data = spark.table("ml_monitoring.reference_scored").toPandas()

# Current = just the batch that was scored in the last 4 hours
current_data = (
    spark.table("ml_monitoring.batch_predictions")
    .filter("scoring_ts >= current_timestamp() - interval 4 hours")
    .toPandas()
)

column_mapping = ColumnMapping(
    target="actual_label",       # NaN until labels arrive
    prediction="predicted_label",
    numerical_features=["feat_1", "feat_2"],   # replace with real feature list
    categorical_features=["feat_cat_1"],       # replace with real feature list
)

report = Report(metrics=[DataDriftPreset(), ClassificationPreset()])
report.run(
    reference_data=reference_data,
    current_data=current_data,
    column_mapping=column_mapping,
)

with mlflow.start_run(run_name="xgb_monitor_batch"):
    report.save_html("/dbfs/tmp/evidently_report.html")
    mlflow.log_artifact("/dbfs/tmp/evidently_report.html")

    result = report.as_dict()
    drift_detected = result["metrics"][0]["result"]["dataset_drift"]
    mlflow.log_metric("dataset_drift_detected", int(drift_detected))

    # Evidently's report is a single point-in-time snapshot, not a time
    # series — append to a Delta table ourselves to get a trend view.
    from pyspark.sql import functions as F

    spark.createDataFrame(
        [(drift_detected,)], ["dataset_drift_detected"]
    ).withColumn("run_ts", F.current_timestamp()).write.mode("append").saveAsTable(
        "ml_monitoring.drift_history"
    )
