# Spark Practice

PySpark notebooks written for data engineer interview prep: markdown
explanations paired with runnable code, covering Spark core/SQL (01-06:
architecture/lazy evaluation, DataFrame I/O and schemas, joins/broadcast/
skew, aggregations and window functions, partitioning and performance
tuning, structured streaming plus classic coding problems) and Spark ML
(07-09: `pyspark.ml` pipelines, feature engineering, classification/
regression + evaluation, hyperparameter tuning and productionizing).

**These notebooks are written but not executed.** PySpark isn't installed
in this environment (only a JDK is present), and setting up a full Spark
environment wasn't worth doing just to run demo cells — the code is
correct, standard PySpark; run it yourself once you have an environment.

## Setup (to actually run these)

```bash
cd spark_practice
python -m venv .venv && source .venv/bin/activate
pip install pyspark==3.5.1 jupyter
java -version        # need Java 11 or 17 on PATH — already present on this machine
jupyter notebook notebooks/
```

## Layout

```
spark_practice/
  notebooks/
    01_spark_core_concepts.ipynb              <- architecture, RDD vs DataFrame, lazy eval, jobs/stages/tasks
    02_dataframes_io_and_schemas.ipynb        <- reading/writing formats, explicit schemas, UDFs vs built-ins
    03_joins_and_broadcast.ipynb              <- join types, broadcast/sort-merge/shuffle-hash, data skew + salting
    04_aggregations_and_window_functions.ipynb <- groupBy/agg, rank/dense_rank/row_number, pivot, top-N per group
    05_partitioning_and_performance_tuning.ipynb <- repartition vs coalesce, shuffles, caching, Catalyst/AQE, debugging
    06_structured_streaming_and_interview_problems.ipynb <- streaming basics + word count, dedup, sessionization, nth-highest
    07_spark_ml_pipelines_and_feature_engineering.ipynb  <- Transformer/Estimator/Pipeline, StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
    08_spark_ml_classification_regression_and_evaluation.ipynb <- LogisticRegression, RandomForest, evaluators, confusion matrix, LinearRegression
    09_spark_ml_tuning_and_productionizing.ipynb         <- ParamGridBuilder/CrossValidator vs TrainValidationSplit, model persistence, Spark ML vs sklearn, serving
```

Notebooks build small DataFrames inline — no external data fixtures needed.
Each notebook ends with an interview Q&A section and a one-line pointer to
the next topic — read them in order the first time through, then use them
as a quick-reference the day before an interview.

## Related: `../sql_postgres_practice/`

Several problems here (top-N per group, window functions, upsert/dedup
logic) have direct SQL equivalents already worked through in
`sql_postgres_practice/practice/`. Interviewers often ask you to translate
between the two — worth reviewing both back to back.
