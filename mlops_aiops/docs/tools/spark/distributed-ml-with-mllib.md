# Distributed Classical ML with Spark MLlib

Part of [`README.md`](README.md)'s Spark section — that file covers Spark as a general
distributed data engine (partitioning, shuffles, joins, Catalyst, AQE); this file is
specifically about the ML layer built on top of it. It's also worth placing correctly
relative to two other docs so the three don't get confused:

- [`07_distributed_training_serving.md`](../../../../fundamentals/system_design_foundation/01_ml_system_design/07_distributed_training_serving.md)
  (elsewhere in this workspace) covers **distributed deep learning** — data/model/pipeline
  parallelism, gradient sync via all-reduce/NCCL, Ray/Ray Serve. That's a different world:
  training a single, very large neural network faster by spreading *its* computation across
  many GPUs.
- **This file** covers **distributing classical ML algorithms** (linear models, trees,
  k-means) across a cluster of machines specifically because the *data* is too large for one
  machine — a genuinely different problem with a genuinely different set of solutions, and
  the reason a model can be simple (logistic regression) while still needing a cluster.
- [`../scikit-learn/README.md`](../scikit-learn/README.md) and
  [`../scikit-learn/ml-fundamentals-deep-dive.md`](../scikit-learn/ml-fundamentals-deep-dive.md)
  cover the same classical algorithms, single-machine — read those first for the algorithm
  theory (bias-variance, regularization, what gradient descent actually computes); this file
  assumes that grounding and adds "now do it when the data doesn't fit on one machine."

Everything below was actually run against PySpark 3.5.3 (local mode, 4 partitions) on this
machine.

## `spark.ml` vs. the legacy `spark.mllib`: use the DataFrame API

Spark has shipped **two** machine learning APIs historically, and the name "MLlib" refers to
both, which is the source of a lot of stale-tutorial confusion:

- **`spark.mllib`** (legacy, RDD-based) — Spark's original ML API, operating directly on
  RDDs. In maintenance mode only since Spark 2.0; new algorithms and features don't land here.
- **`spark.ml`** (current, DataFrame-based) — built on DataFrames, which means every
  advantage [`README.md`](README.md#catalyst-optimizer-and-tungsten) already covers for
  Spark SQL/DataFrames — the Catalyst optimizer, Tungsten code generation, predicate
  pushdown — applies to ML feature engineering and pipelines too, not just plain queries.
  This is the actively developed API and the one every example below uses. "MLlib," used
  informally today, almost always means `spark.ml` specifically.

## The core abstraction: `Transformer`, `Estimator`, `Pipeline`

`spark.ml`'s object model is deliberately shaped like scikit-learn's (see
[`../scikit-learn/README.md`](../scikit-learn/README.md#what-it-is-and-the-one-idea-the-whole-library-is-built-around))
— `.fit()` produces a fitted model, `.transform()` applies it — but every operation executes
as a **distributed Spark job**, not an in-process NumPy computation. Concretely:

- An **`Estimator`** (`LogisticRegression`, `StringIndexer`, `RandomForestClassifier`) has a
  `.fit(df)` method that learns something from a distributed DataFrame and returns a
  **`Transformer`**.
- A **`Transformer`** has a `.transform(df)` method that maps one DataFrame to another —
  `StandardScalerModel.transform` scales columns, a fitted `LogisticRegressionModel.transform`
  adds prediction columns, and so on. Some things are transformers without ever being fit
  (`VectorAssembler`, `OneHotEncoder` in its unfit form is an Estimator, its fitted form is a
  Transformer).
- A **`Pipeline`** chains stages together and is itself an `Estimator` — calling `.fit()` on
  the whole pipeline calls `.fit()`/`.transform()` on each stage in sequence, and (same
  reason as scikit-learn's `Pipeline`) is what makes it structurally hard to leak information
  between preprocessing steps by accident, now across a cluster instead of within one process.

## Feature engineering: why a `VectorAssembler` step is mandatory

Spark ML estimators expect **one column holding a single vector** of all input features, not
N separate feature columns the way scikit-learn's 2D array accepts directly — a real,
required extra step with no equivalent in the single-machine libraries:

```python
from pyspark.sql import SparkSession
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator

spark = SparkSession.builder.appName("mllib-demo").master("local[4]").getOrCreate()

# df has columns: age (double), income (double), city (string), plan (string), label (int)
train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

city_indexer = StringIndexer(inputCol="city", outputCol="city_idx")
plan_indexer = StringIndexer(inputCol="plan", outputCol="plan_idx")
city_ohe = OneHotEncoder(inputCol="city_idx", outputCol="city_vec")
plan_ohe = OneHotEncoder(inputCol="plan_idx", outputCol="plan_vec")
assembler = VectorAssembler(inputCols=["age", "income", "city_vec", "plan_vec"], outputCol="features")
lr = LogisticRegression(featuresCol="features", labelCol="label")

pipeline = Pipeline(stages=[city_indexer, plan_indexer, city_ohe, plan_ohe, assembler, lr])
model = pipeline.fit(train_df)
preds = model.transform(test_df)

evaluator = BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC")
print("Test AUC:", round(evaluator.evaluate(preds), 4))
```
```
Test AUC: 0.8423
```

`StringIndexer` converts a string column into a numeric category index (required — Spark ML
algorithms are purely numeric internally, unlike scikit-learn/pandas pipelines that can carry
category dtypes further into the pipeline); `OneHotEncoder` then expands that index into a
sparse vector, exactly mirroring
[`../scikit-learn/README.md`](../scikit-learn/README.md#columntransformer-different-preprocessing-for-different-columns-as-one-step)'s
`ColumnTransformer` pattern conceptually, but expressed as an explicit chain of pipeline
stages rather than one composite object, because each step here is its own distributed job
over the DataFrame, not an in-process NumPy transformation.

## How training actually distributes: it depends entirely on the algorithm

This is the part with no direct scikit-learn equivalent to lean on, and the part worth
understanding precisely rather than trusting as a black box. **Not every algorithm
distributes the same way, and some classical algorithms don't distribute well at all** —
which is a direct, practical constraint on what Spark ML can and can't do well, not an
implementation detail.

### Linear and logistic regression: distributed gradient descent

[`../scikit-learn/ml-fundamentals-deep-dive.md`](../scikit-learn/ml-fundamentals-deep-dive.md#gradient-descent-how-a-model-actually-learns-its-parameters)
showed gradient descent computing a gradient from the *entire* training set on every step
(batch gradient descent). That gradient is a **sum** over every training example's individual
contribution — and a sum over partitioned data distributes trivially: each partition computes
its own partial sum (its local subset's contribution to the gradient) independently and in
parallel, on whichever executor holds that partition; the driver then adds the partial sums
together to get the true, full-dataset gradient, updates the model's weights, and broadcasts
the updated weights back out for the next iteration. This is exactly a MapReduce shape (map:
compute a local partial gradient per partition; reduce: sum them), repeated once per gradient
descent iteration — and it's precisely *why* linear models are among the most naturally
Spark-friendly algorithms to train at scale: the underlying math is already a sum, which is
the one operation distributed systems are best at.

The real cost this implies: **one round of network communication (the weight broadcast +
partial-gradient collection) per training iteration** — for an algorithm that might take
hundreds of iterations to converge, that's hundreds of synchronization rounds across the
cluster, each one gated on the slowest partition/executor finishing its local computation
(the same straggler problem [`README.md`](README.md#partitioning) covers for partition
skew generally — a skewed partition here doesn't just slow one stage, it slows every single
training iteration).

### Tree-based models: distributed histogram-based split-finding

A single decision tree can't be split across machines the naive way (build the left subtree
on one machine, the right subtree on another) because which rows go left vs. right at any
node depends on decisions made at every node above it — the tree structure itself is
sequential. Spark ML's `RandomForestClassifier`/`GBTClassifier` instead distribute **within
each split decision**: for every candidate split at a given tree node, each partition
computes a local histogram of the relevant feature's values for the rows currently at that
node (conceptually similar to [`../xgboost/README.md`](../xgboost/README.md)'s
histogram-based split finding, but aggregated *across machines* via a shuffle/reduce rather
than just across CPU cores on one machine); the driver aggregates every partition's local
histogram into a global one, picks the best split, and broadcasts that decision back out
before every executor moves on to the next node. **Bagging** (each of the forest's trees
trained on an independent bootstrap sample) adds a second, embarrassingly-parallel layer on
top — different trees can, in principle, be built fully independently of each other, which is
exactly the same variance-reduction mechanism
[`../scikit-learn/ml-fundamentals-deep-dive.md`](../scikit-learn/ml-fundamentals-deep-dive.md#ensemble-methods-bagging-vs-boosting)
describes single-machine, just with "independent" now also meaning "on different executors."

```python
from pyspark.ml.classification import RandomForestClassifier

rf = RandomForestClassifier(featuresCol="features", labelCol="label", numTrees=50, maxDepth=5, seed=42)
pipeline = Pipeline(stages=[city_indexer, plan_indexer, city_ohe, plan_ohe, assembler, rf])
model = pipeline.fit(train_df)
preds = model.transform(test_df)

print("RF Test AUC:", round(evaluator.evaluate(preds), 4))

rf_model = model.stages[-1]
print("feature importances:", [round(x, 4) for x in rf_model.featureImportances.toArray()])
```
```
RF Test AUC: 0.8071
feature importances: [0.0577, 0.7951, 0.0075, 0.0077, 0.0194, 0.1126]
```
(feature order: `age, income, city_Austin/Denver, plan_basic/pro` — `income` at `0.7951`
dominates, correctly matching this synthetic dataset's design, where income was the primary
signal driving the label.)

### K-Means: distributed Lloyd's algorithm

Each iteration: every partition assigns its local points to their nearest current centroid
and computes a local partial sum (and count) of points per cluster — again, exactly the same
"sum distributes trivially across partitions" shape as linear regression's gradient. The
driver aggregates every partition's partial sums to compute the new, true centroids and
broadcasts them back out for the next iteration. Same MapReduce shape, same per-iteration
communication cost, different quantity being summed.

### What genuinely doesn't distribute well, and why Spark ML's API reflects it

- **Exact k-nearest-neighbors** requires comparing a query point against *every* training
  point to find the true nearest neighbors — an operation that doesn't decompose into a
  per-partition-independent computation the way a sum does; every partition potentially holds
  a relevant neighbor for every query. This is why Spark ML has no exact k-NN classifier at
  all — approximate nearest-neighbor techniques (locality-sensitive hashing, which Spark ML
  *does* ship as `BucketedRandomProjectionLSH`/`MinHashLSH`) trade exactness for
  distributability, deliberately.
- **Non-linear-kernel SVMs** have a training cost that scales with the size of an implicit
  kernel matrix relating every training point to every other training point — quadratic in
  dataset size, and not a sum that partitions independently the way a linear model's gradient
  is. This is exactly why Spark ML's `LinearSVC` is **linear only** — it's not a missing
  feature, it's the direct, correct consequence of which SVM variant actually has a
  distributable training algorithm at all. See
  [`../scikit-learn/README.md`](../scikit-learn/README.md#support-vector-machine) for the
  full-flexibility (including `rbf`) single-machine version, appropriate once the data
  genuinely fits on one machine.

**The general rule this implies, worth carrying forward as a mental model**: an algorithm
distributes cleanly across a Spark cluster to the exact extent its core computation can be
expressed as a **sum (or other associative/commutative aggregate) over independent
partitions** — gradient descent's gradient, a histogram's per-bucket counts, k-means'
per-cluster centroid sums. An algorithm whose core computation inherently needs to compare
*every* point against *every other* point, or make a sequential decision that depends on
every prior decision, resists distribution — and Spark ML's actual algorithm catalog is a
direct map of which classical algorithms happen to fall on which side of that line.

## Seeing the physical distribution directly

```python
part_counts = df.repartition(4).rdd.glom().map(len).collect()
print("rows per partition:", part_counts)
```
```
rows per partition: [500, 500, 500, 500]
```

2000 rows, `repartition(4)`, and each of the 4 partitions genuinely holds exactly 500 rows —
`.glom()` collects each partition's contents as a list so `len` can be measured per
partition directly, real, physical evidence (not an assumption) that the DataFrame really is
split across 4 independent chunks before any of the training above runs. Every model fit
above operated on data actually spread this way — the AUC/feature-importance numbers weren't
computed by one process quietly loading everything into memory.

## Hyperparameter tuning at scale: `CrossValidator`

```python
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

grid = (ParamGridBuilder()
        .addGrid(lr.regParam, [0.01, 0.1, 1.0])
        .addGrid(lr.elasticNetParam, [0.0, 0.5])
        .build())
cv = CrossValidator(estimator=pipeline, estimatorParamMaps=grid, evaluator=evaluator, numFolds=3, seed=42)
cv_model = cv.fit(train_df)

print("CV avg metrics:", [round(m, 4) for m in cv_model.avgMetrics])
best_lr = cv_model.bestModel.stages[-1]
print("best regParam:", best_lr.getRegParam(), "best elasticNetParam:", best_lr.getElasticNetParam())
```
```
CV avg metrics: [0.8116, 0.8121, 0.8104, 0.8019, 0.806, 0.5]
best regParam: 0.01 best elasticNetParam: 0.5
```

Mechanically the distributed version of
[`../scikit-learn/README.md`](../scikit-learn/README.md#cross-validation-and-hyperparameter-search-as-library-calls)'s
`GridSearchCV` — every one of the 6 hyperparameter combinations gets fit and evaluated across
3 folds as its own set of distributed Spark jobs. Worth reading the last score in that list
(`0.5`, at `regParam=1.0, elasticNetParam=1.0` — pure, heavy L1 regularization) as a real,
concrete instance of
[`../scikit-learn/ml-fundamentals-deep-dive.md`](../scikit-learn/ml-fundamentals-deep-dive.md#regularization-l1-l2-and-why-they-behave-differently)'s
regularization story: too much regularization pushed essentially every coefficient toward
zero, leaving a model no better than random guessing (`0.5` AUC) — the same bias/variance
tradeoff from that doc, now visible in a cross-validation grid rather than a single
before/after comparison.

## When Spark ML is (and isn't) the right call

- **Reach for Spark ML** when the training data itself doesn't fit in memory on one machine
  (or in one machine's practical working set) and is already living in a distributed
  store/format (Parquet/Delta on S3/HDFS) that Spark reads natively — the honest, primary
  reason to pay Spark's real operational complexity cost at all.
- **Reach for scikit-learn/XGBoost instead** once training data comfortably fits on one
  machine (a large but bounded dataset, or a sample of a larger one) — both offer a much
  broader algorithm catalog (real non-linear SVMs, exact k-NN, the full breadth of scikit-learn's
  ensemble/linear-model variety) and dramatically simpler local iteration than standing up
  or reasoning about a cluster.
- **A common, genuinely practical middle path**: use Spark for what it's unambiguously best
  at — distributed feature engineering and aggregation over the full, large raw dataset
  (exactly [`README.md`](README.md#worked-example-this-repos-databricks-batch-scoring-monitor)'s
  pattern) — then materialize the resulting, much smaller feature table via `.toPandas()` and
  train with scikit-learn/XGBoost on a single machine, getting the best of both: Spark's
  distributed data processing where the data genuinely is too large, and scikit-learn/XGBoost's
  broader algorithm flexibility and faster iteration where the (now feature-engineered,
  aggregated) data isn't.
- **XGBoost itself has a Spark integration** (`xgboost4j-spark` / `xgboost.spark` in recent
  Python releases) — worth knowing it exists specifically for cases that want XGBoost's
  specific tree-boosting quality *and* need to train directly against data that's already
  distributed in Spark, without a separate materialization step.

## Relationship to other tools in this repo

- **[`README.md`](README.md)** — the general Spark mechanics (partitioning, shuffles,
  Catalyst, AQE) this file assumes and builds directly on top of.
- **[scikit-learn](../scikit-learn/README.md) /
  [ml-fundamentals-deep-dive.md](../scikit-learn/ml-fundamentals-deep-dive.md)** — the same
  algorithms and theory, single-machine; read first for the "what and why" this file assumes.
- **[XGBoost](../xgboost/README.md)** — a sharper, more specialized alternative to Spark ML's
  `GBTClassifier` for tree boosting specifically, with its own Spark integration for cases
  that need both.
- **[`07_distributed_training_serving.md`](../../../../fundamentals/system_design_foundation/01_ml_system_design/07_distributed_training_serving.md)**
  — the genuinely different problem of distributing one large *neural network's* training
  across GPUs, not this file's problem of distributing classical ML training across a
  cluster because the *data* is large.
