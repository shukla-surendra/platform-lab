# XGBoost

**Category:** ML modeling (gradient-boosted decision trees)

## What it is

XGBoost ("eXtreme Gradient Boosting") is a library that builds a predictive
model as an **ensemble of decision trees trained sequentially**, where each
new tree is fit to correct the errors of the ensemble built so far, rather
than being trained independently. It's a specific, heavily optimized
implementation of gradient boosting: second-order (Newton) gradient
descent in function space, L1/L2 regularization on leaf weights, and a
tree-building algorithm designed to run fast on both a single machine and
distributed clusters. Available as a Python/R/C++/Java library and as a
standalone CLI; the Python API is what's used in this repo.

## The problem it solves, and why boosting instead of one big model

A single decision tree is a poor predictor on its own: shallow trees
underfit (high bias — they can't capture the real decision boundary), deep
trees overfit (high variance — they memorize noise in the training data).
Two different ensemble strategies fix this in different ways:

- **Bagging** (random forest): train many *independent* deep trees on
  bootstrap-resampled data/features, then average their predictions. This
  reduces variance — no single tree's overfitting dominates the average —
  but each tree is still built without knowledge of what the others got
  wrong, so bagging can't fix bias.
- **Boosting** (XGBoost, LightGBM, CatBoost, sklearn's
  `GradientBoostingClassifier`): train trees *sequentially*, where tree
  `k+1` is fit to the **residual error** left by trees `1..k`. Each tree is
  intentionally shallow/weak (a "weak learner"), but the sum of the
  sequence converges toward the true function. This directly attacks bias,
  and regularization (shrinkage via `learning_rate`, tree depth limits, L1/L2
  penalties) keeps variance in check as more trees are added.

XGBoost specifically improves on plain gradient boosting (as in
`sklearn.ensemble.GradientBoostingClassifier`) in a few concrete ways:

- Uses the **second-order Taylor expansion** of the loss function (gradient
  *and* Hessian) to choose splits, not just the gradient — a better local
  approximation of "which split actually reduces loss," so it converges in
  fewer trees.
- Adds an explicit **regularization term** on the number of leaves and the
  leaf weights directly into the objective it optimizes, not just as an
  external hyperparameter — overfitting control is part of the loss
  function itself, not a heuristic bolted on afterward.
- **Histogram-based split finding** (`tree_method="hist"`, the default
  since XGBoost 2.0): buckets continuous features into a fixed number of
  bins before searching for the best split, turning an O(n log n) sort per
  feature per node into a single O(n) histogram build — the main reason
  XGBoost is fast enough to be practical on datasets with hundreds of
  thousands to millions of rows.
- Handles **missing values natively** — at each split, it learns which
  direction (left/right) missing values should default to, rather than
  requiring imputation upfront.
- Supports **sparse data** and column subsampling efficiently, which matters
  for high-cardinality one-hot-encoded categoricals.

## What it's used for

- Tabular classification/regression where the signal is mostly non-linear
  interactions between a moderate number of engineered features — the
  dominant winning approach on tabular Kaggle competitions and a common
  default before reaching for a neural net.
- **Imbalanced binary classification** (fraud, churn, rare-disease
  detection): the `scale_pos_weight` parameter and threshold-independent
  metrics (PR-AUC) make it a strong fit when the positive class is rare —
  this is exactly the setup in `projects/fraud-detection-xgboost/` in this
  repo (~0.17% positive rate).
- Ranking (`rank:pairwise`, `rank:ndcg` objectives) — search result / feed
  ranking.
- Feature importance / explainability work as a byproduct of training —
  split-based importance and SHAP values both come from the same fitted
  model, useful for debugging *why* a model makes a prediction, not just
  whether it's accurate.

## Alternatives

| Library | How it differs |
|---|---|
| **LightGBM** | Also histogram-based gradient boosting, but grows trees **leaf-wise** (best-loss-reduction leaf first) instead of XGBoost's level-wise growth — usually faster and sometimes more accurate on large data, but more prone to overfitting on small data since leaf-wise growth can produce deep, asymmetric trees without care. |
| **CatBoost** | Built around **native categorical feature handling** (ordered target encoding internally, no manual one-hot/label encoding needed) and symmetric ("oblivious") trees, which trade some flexibility for faster inference and less overfitting on categorical-heavy data. |
| **sklearn `GradientBoostingClassifier`** | The same core boosting idea, pure Python/Cython, first-order gradients only, no histogram optimization — much slower on non-trivial data, but zero extra dependency; mostly useful as a teaching baseline, which is why it's `train_baseline_logreg.py`'s conceptual cousin in this repo (that file actually uses logistic regression as the baseline, not sklearn GBM, but same role: a simple reference point below XGBoost). |
| **Random Forest** (`sklearn.ensemble.RandomForestClassifier`) | Bagging, not boosting (see above) — trees are independent and parallelizable, generally more robust to noisy/mislabeled data and less prone to overfitting out of the box, but typically loses to well-tuned boosting on clean tabular data with real signal. |
| **Neural nets (tabular)** (TabNet, FT-Transformer, etc.) | Competitive on very large tabular datasets or when combining tabular data with text/image features in one model, but usually need much more data and tuning to beat a well-tuned XGBoost model on a mid-sized, purely-tabular problem. |

## Core concepts

### The objective function

XGBoost minimizes: `training loss (e.g. log loss for binary classification) + regularization term (tree complexity)`, evaluated *additively* as trees are added — at boosting round `t`, it asks "which tree, added to everything built so far, most reduces this objective," using the gradient and Hessian of the loss at the current predictions to approximate that answer without literally trying every possible tree.

### Key hyperparameters

| Parameter | What it controls | Practical guidance |
|---|---|---|
| `n_estimators` | Number of boosting rounds (trees) | More trees = more capacity, but also more overfitting risk without shrinkage/early stopping; pair with `early_stopping_rounds` rather than guessing a fixed number. |
| `learning_rate` (`eta`) | Shrinkage — how much each new tree's prediction is scaled before being added to the ensemble | Lower (e.g. 0.01–0.1) needs more trees but generalizes better; this is the main bias/variance knob alongside tree count. |
| `max_depth` | Max depth of each tree | Shallow (3–6) is typical for tabular data — deep trees overfit fast in a boosting context since errors compound across rounds. |
| `min_child_weight` | Minimum sum of instance Hessian weight needed in a leaf to allow a further split | Higher values = more conservative splits, a direct overfitting control especially on small/noisy leaves. |
| `subsample` | Fraction of training rows sampled (without replacement) per tree | <1.0 (e.g. 0.8) adds randomness like bagging does, reducing variance. |
| `colsample_bytree` / `colsample_bylevel` / `colsample_bynode` | Fraction of features sampled at tree/level/split-node granularity | Same idea as `subsample` but on the feature axis; also speeds up training. |
| `gamma` (`min_split_loss`) | Minimum loss reduction required to make a further split | Higher = more conservative (prunes marginal splits); a direct complexity penalty per split. |
| `reg_alpha` / `reg_lambda` | L1 / L2 regularization on leaf weights | `reg_lambda` (L2) is on by default (1.0); `reg_alpha` (L1) pushes some leaf weights to exactly zero, effectively sparse. |
| `scale_pos_weight` | Multiplier on the gradient for positive-class examples in binary classification | The standard fix for class imbalance — set to `count(negative) / count(positive)` so a rare positive class isn't drowned out by trivially predicting "negative" for everything (see `train.py` example below). |
| `objective` | The loss function being optimized | `binary:logistic` (binary classification, outputs probabilities), `multi:softprob` (multiclass), `reg:squarederror` (regression), `rank:pairwise`/`rank:ndcg` (ranking). |
| `eval_metric` | Metric(s) tracked on the eval set during training (for logging/early stopping) | Should match what you actually care about, not just what's convenient — e.g. `aucpr` (PR-AUC) instead of `error`/accuracy on imbalanced data, since accuracy is trivially gamed by predicting the majority class. |
| `tree_method` | Split-finding algorithm | `hist` is the default and fastest for CPU; `gpu_hist`/`device="cuda"` for GPU training on large data. |

### Two APIs: sklearn wrapper vs. native Booster

XGBoost ships two interchangeable-ish interfaces:

1. **sklearn wrapper API** — `xgb.XGBClassifier`, `xgb.XGBRegressor`. Drop-in
   compatible with sklearn's `.fit()`/`.predict()`/`.predict_proba()`
   convention, works inside `Pipeline`, `GridSearchCV`, etc. This is what
   `train.py` in this repo uses — the natural choice when the rest of the
   pipeline (train/test split, metrics) is already sklearn-based.
2. **Native `Booster` API** — lower-level, built around `xgb.DMatrix` (an
   internal optimized data structure) and `xgb.train(params, dtrain, ...)`.
   Slightly more control (e.g. custom objective/eval functions, `xgb.cv`
   for built-in cross-validation without sklearn's `cross_val_score`), and
   is what the sklearn wrapper calls under the hood anyway. Reach for this
   when you need something the wrapper doesn't expose, not by default.

Both produce the same underlying model; a `Booster` can be pulled out of a
fitted `XGBClassifier` via `model.get_booster()` if native-API features
(like plotting or dumping the tree structure as text/JSON) are needed
after training with the sklearn wrapper.

## Usage

### Installation

```bash
pip install xgboost
# or, in a uv-managed project (as in this repo):
uv add xgboost
```

GPU support requires the CUDA-enabled build, which is what `pip install
xgboost` ships by default on Linux/Windows with a compatible GPU detected
at import time — no separate package needed as of recent releases.

### Minimal end-to-end example (sklearn API)

```python
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(
    objective="binary:logistic",
    eval_metric="aucpr",
    max_depth=5,
    learning_rate=0.1,
    n_estimators=200,
    random_state=42,
)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False,
)

y_pred_proba = model.predict_proba(X_test)[:, 1]
print(roc_auc_score(y_test, y_pred_proba))
```

### Real worked example: this repo's fraud-detection pipeline

`projects/fraud-detection-xgboost/src/fraud_detection/train.py` is a
complete, runnable version of the pattern above, extended with the pieces
that matter for a real (if small/practice-scale) pipeline:

```python
# scale_pos_weight fix for a ~0.17% positive rate — without this the model
# trivially minimizes loss by predicting "not fraud" for every row.
scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

params = {
    "objective": "binary:logistic",
    "eval_metric": "aucpr",          # PR-AUC, not accuracy — see below
    "scale_pos_weight": float(scale_pos_weight),
    "max_depth": 5,
    "learning_rate": 0.1,
    "n_estimators": 200,
    "random_state": RANDOM_SEED,
}

model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train)

y_pred_proba = model.predict_proba(X_test)[:, 1]
```

Full file: [`train.py`](../../../projects/fraud-detection-xgboost/src/fraud_detection/train.py).
Companion file [`evaluate.py`](../../../projects/fraud-detection-xgboost/src/fraud_detection/evaluate.py)
shows the separate "is the currently-registered model still good?" check —
it reloads the model via `mlflow.xgboost.load_model("models:/<name>/latest")`
rather than reusing the in-memory `model` object from training, which is
the more realistic shape of a monitoring/evaluation job that runs on a
schedule against whatever is actually deployed.

### Why PR-AUC, not accuracy, on imbalanced data

With a 0.17% fraud rate, a model that predicts "not fraud" for every single
row is 99.83% accurate and completely useless. Two metrics that don't have
this failure mode:

- **ROC-AUC** — probability that a random positive example is ranked above
  a random negative one. Threshold-independent, but can look
  deceptively good on heavy imbalance because the huge number of true
  negatives dominates the false-positive-rate axis.
- **PR-AUC** (`average_precision_score` in sklearn, `aucpr` as XGBoost's
  `eval_metric`) — area under precision vs. recall, which only looks at
  how the model does on the positive class and its false positives; far
  more sensitive to imbalance and generally the better metric to optimize
  and report when positives are rare, as they are here.

### Early stopping

Rather than guessing `n_estimators` upfront, let XGBoost stop once the
eval metric stops improving:

```python
model = xgb.XGBClassifier(
    n_estimators=1000,           # generous upper bound
    early_stopping_rounds=20,    # stop if no improvement for 20 rounds
    eval_metric="aucpr",
)
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],   # a genuine held-out validation set, not X_test
)
print(model.best_iteration, model.best_score)
```

Note: the eval set used for early stopping should be a validation split
distinct from the final test set — stopping based on test-set performance
leaks test information into model selection.

### Cross-validation with the native API

```python
dtrain = xgb.DMatrix(X_train, label=y_train)
cv_results = xgb.cv(
    params={"objective": "binary:logistic", "eval_metric": "aucpr", "max_depth": 5},
    dtrain=dtrain,
    num_boost_round=500,
    nfold=5,
    early_stopping_rounds=20,
    seed=42,
)
print(cv_results.tail())  # per-round mean/std of train and test metric
```

### Feature importance and SHAP

```python
# Built-in importance (fast, but biased toward high-cardinality features
# when using the default "weight" (split count) importance type):
importances = model.feature_importances_          # gain-based by default in recent versions
xgb.plot_importance(model.get_booster(), importance_type="gain")

# SHAP values (slower, but additive/consistent per-prediction attribution —
# the standard for "why did the model predict this for this specific row"):
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test)
```

Built-in importance answers "which features did the trees split on most /
most usefully, on average" (a global, model-level view). SHAP answers "how
much did each feature push *this specific prediction* away from the
baseline" (a local, per-row view) — reach for SHAP when debugging an
individual misclassification, and built-in importance for a quick global
sanity check.

### Handling missing values and categoricals

- **Missing values**: pass `np.nan` directly — no imputation needed.
  XGBoost learns the optimal default split direction for missing values at
  each node during training.
- **Categorical features**: as of XGBoost 1.6+, native categorical support
  exists via `enable_categorical=True` on the sklearn wrapper combined with
  pandas `category` dtype columns — XGBoost then handles the
  encoding internally (similar in spirit to CatBoost) instead of requiring
  manual one-hot/label/target encoding beforehand. Before that feature,
  the standard approach (and still common in mixed pipelines) is to
  one-hot or target-encode categoricals upstream, which is closer to what
  `features.py` does in this repo's pipeline.

### Persistence and MLflow integration

Two ways to save a model, with different tradeoffs:

```python
# Native XGBoost format (JSON or UBJ) — portable across XGBoost versions
# and languages (Python/R/C++), no pickle version-compatibility risk.
model.save_model("model.json")
model = xgb.XGBClassifier()
model.load_model("model.json")

# MLflow — wraps the native format plus environment/dependency metadata,
# and (as used in this repo) integrates with the model registry:
import mlflow.xgboost
mlflow.xgboost.log_model(model, artifact_path="model", registered_model_name="fraud-xgboost")
loaded = mlflow.xgboost.load_model("models:/fraud-xgboost/latest")
```

See [MLflow](../mlflow/README.md) for the registry/versioning side of this
— that doc's "Model registry, end to end" section walks through this exact
train → register → reload-and-evaluate flow using this repo's pipeline as
the worked example.

### GPU training

```python
model = xgb.XGBClassifier(tree_method="hist", device="cuda")  # XGBoost >= 2.0
# older versions: tree_method="gpu_hist"
```

Worth it once a dataset is large enough that CPU histogram building is the
bottleneck (roughly hundreds of thousands of rows and up, depending on
feature count) — for the dataset sizes in this repo's practice projects,
CPU `hist` is already fast enough that GPU training isn't necessary.

## Relationship to other tools in this repo

- **[MLflow](../mlflow/README.md)** — tracks every training run's
  params/metrics and registers the resulting model; XGBoost itself has no
  experiment-tracking or versioning of its own.
- **[Evidently](../evidently/README.md)** — computes data/prediction drift
  and performance reports on an XGBoost model's inputs/outputs after
  deployment; XGBoost has no monitoring capability of its own once a model
  is serving.
- **[Feast](../feast/README.md)** — `train_with_feast.py` in the
  fraud-detection project pulls the same engineered features from a Feast
  feature store instead of computing them ad hoc in-process, so training
  and serving use identical feature logic.
