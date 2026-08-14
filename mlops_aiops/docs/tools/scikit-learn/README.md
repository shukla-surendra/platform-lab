# scikit-learn

**Category:** ML modeling (classical/non-deep-learning algorithms, and the standard API
convention most of the Python ML ecosystem — including XGBoost's own Python wrapper —
deliberately imitates)

## What it is, and the one idea the whole library is built around

scikit-learn is a library of classical machine learning algorithms — linear/logistic
regression, decision trees, random forests, SVMs, k-means, PCA, and dozens more — built
directly on [NumPy](../numpy/README.md) arrays. Its actual contribution isn't any single
algorithm (most predate the library by decades); it's a **single, consistent object
interface** every algorithm implements, which is why learning scikit-learn's API pays off
far beyond scikit-learn itself:

- **`.fit(X, y)`** — learn from data. Every estimator, whatever it does internally, exposes
  this exact method signature.
- **`.predict(X)`** — produce predictions from a fitted model.
- **`.transform(X)`** (on preprocessing/dimensionality-reduction objects) — apply a learned
  transformation (scaling, encoding, projecting) to new data.
- **`.fit_transform(X)`** — fit and transform in one call, for convenience — but see the
  Pipeline section below for exactly where using this shortcut carelessly causes a real bug.

This convention is why XGBoost's Python API (`XGBClassifier`/`XGBRegressor`, covered in
[`../xgboost/README.md`](../xgboost/README.md)) deliberately mimics
`.fit()`/`.predict()`/`.predict_proba()` — it's designed to drop into the exact same
`Pipeline`, `GridSearchCV`, and cross-validation tooling covered below without modification.
Everything in this doc was actually run against scikit-learn 1.7.2, NumPy 2.2.6, and pandas
2.3.3.

## A minimal end-to-end example

```python
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)   # learn scaling params from TRAIN only
X_test_s = scaler.transform(X_test)          # apply the SAME params to test — never re-fit

model = LogisticRegression(random_state=42)
model.fit(X_train_s, y_train)
preds = model.predict(X_test_s)
print(accuracy_score(y_test, preds))
```
```
0.9333333333333333
```

`stratify=y` on `train_test_split` matters more than it looks — without it, a small or
imbalanced dataset can end up with a class split unevenly between train and test purely by
chance, which quietly biases evaluation. `stratify=y` preserves each class's original
proportion in both splits. The `fit_transform` on train / `transform`-only on test asymmetry
in the scaler is deliberate and important — covered next, because getting it backward is a
real, common, silent bug.

## `Pipeline` and `ColumnTransformer`: why they exist, not just what they do

### The bug they prevent: data leakage through preprocessing

Calling `.fit_transform()` on the **entire** dataset before splitting into train/test — or
even calling `.fit()` on the scaler using test data at all — leaks information about the
test set into training: the scaler's mean/standard deviation, computed partly from data the
model is never supposed to have seen, end up baked into the training features. The model's
reported test accuracy is then **optimistically biased** — it looks better than it would in
production, where genuinely unseen data has no way to have influenced any preprocessing
step. This is a real, easy mistake specifically because `fit_transform(X)` is one convenient
call that silently does the wrong thing if `X` is the whole dataset instead of just the
training split.

`Pipeline` doesn't just chain steps for convenience — it's what makes it *structurally hard*
to make this mistake: a `Pipeline`'s `.fit()` only ever calls `.fit()` on each inner step
using the data passed to the pipeline's own `.fit()` — and cross-validation tooling
(`cross_val_score`, `GridSearchCV`, below) calls `.fit()` on the *whole pipeline* once per
fold, meaning preprocessing gets correctly re-fit on each fold's own training portion only,
automatically. Preprocessing done manually, outside a `Pipeline`, before cross-validation
is a common way this leakage sneaks into an otherwise-careful project.

### `ColumnTransformer`: different preprocessing for different columns, as one step

Real tabular data is rarely all-numeric — a `ColumnTransformer` applies a different
preprocessing pipeline to different named columns, then concatenates the results into one
feature matrix, all as a single fittable/transformable unit:

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# df: a mix of numeric columns (age, income — with some real missing values)
# and categorical columns (city, plan)
X_train, X_test, y_train, y_test = train_test_split(df, y, test_size=0.2, random_state=42)

numeric_features = ["age", "income"]
categorical_features = ["city", "plan"]

numeric_pipeline = Pipeline([
    ("impute", SimpleImputer(strategy="median")),   # fill missing numeric values
    ("scale", StandardScaler()),
])
categorical_pipeline = Pipeline([
    ("onehot", OneHotEncoder(handle_unknown="ignore")),
])

preprocessor = ColumnTransformer([
    ("num", numeric_pipeline, numeric_features),
    ("cat", categorical_pipeline, categorical_features),
])

full_pipeline = Pipeline([
    ("preprocess", preprocessor),
    ("model", LogisticRegression(random_state=42)),
])

full_pipeline.fit(X_train, y_train)
preds = full_pipeline.predict(X_test)
print("accuracy:", accuracy_score(y_test, preds))
print(list(full_pipeline.named_steps["preprocess"].get_feature_names_out()))
```
```
accuracy: 0.7167
['num__age', 'num__income', 'cat__city_Austin', 'cat__city_Denver', 'cat__city_Seattle',
 'cat__plan_basic', 'cat__plan_enterprise', 'cat__plan_pro']
```

`handle_unknown="ignore"` on `OneHotEncoder` matters for the same reason as the leakage
discussion above: without it, a categorical value that appears in production data but never
appeared in training (a new city added after the model was trained, say) makes `.transform()`
**raise an error** rather than degrade gracefully — `"ignore"` instead encodes an unseen
category as all-zeros, letting the pipeline keep running rather than crashing a production
service the first time it sees a genuinely new category. `get_feature_names_out()` recovers
the actual column meaning of the transformed, now-numeric matrix — essential for feature
importance/coefficient inspection once the original column names have been split apart by
one-hot encoding into `cat__city_Austin`, `cat__city_Denver`, and so on.

## Core algorithms, hands-on

Deep theory (bias-variance, regularization mechanics, why gradient descent works, evaluation
metric selection) lives in
[`ml-fundamentals-deep-dive.md`](ml-fundamentals-deep-dive.md) — this section is the library
usage: what each estimator actually looks like fit and used, with real output.

### Decision tree and random forest (classification)

```python
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

tree = DecisionTreeClassifier(max_depth=3, random_state=42)
tree.fit(X_train, y_train)
print("tree accuracy:", tree.score(X_test, y_test))
print("tree feature importances:", tree.feature_importances_.round(3))

forest = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
forest.fit(X_train, y_train)
print("forest accuracy:", forest.score(X_test, y_test))
print("forest feature importances:", forest.feature_importances_.round(3))
```
```
tree accuracy: 0.9666666666666667
tree feature importances: [0.    0.    0.579 0.421]
forest accuracy: 0.9666666666666667
forest feature importances: [0.114 0.006 0.44  0.44 ]
```

Both reach the same accuracy on this dataset (iris is an easy, near-linearly-separable
problem), but notice the feature importances differ meaningfully: the single tree assigns
**zero** importance to the first two features (it only ever needed the last two to make its
splits), while the forest — because each of its 100 trees is built on a bootstrap-resampled
subset of rows and a random subset of features per split — spreads some importance onto the
first feature too, since it isn't always available for a given tree to (greedily) split on
first. This is the direct, observable mechanism behind why random forests are more robust to
any single feature's idiosyncrasies than one tree is — see
[`ml-fundamentals-deep-dive.md`](ml-fundamentals-deep-dive.md#ensemble-methods-bagging-vs-boosting)
and [`../xgboost/README.md`](../xgboost/README.md) for why (bagging vs. boosting, and the
bias/variance mechanism each one attacks).

### Support Vector Machine

```python
from sklearn.svm import SVC

svm = SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42)
svm.fit(X_train, y_train)
print("svm accuracy:", svm.score(X_test, y_test))
```
```
svm accuracy: 0.9666666666666667
```

`kernel="rbf"` (radial basis function) is what lets an SVM draw a **non-linear** decision
boundary without explicitly constructing non-linear features — the "kernel trick" computes
what the similarity between two points *would be* in an implicit, much higher-dimensional
feature space, without ever materializing that space directly. `C` is the regularization
strength (inverted — smaller `C` means *more* regularization, a common point of confusion
coming from other libraries where larger regularization parameters typically mean more
penalty); `gamma` controls how far a single training point's influence reaches in `rbf`'s
implicit feature space — small `gamma` means smooth, far-reaching influence (closer to
linear); large `gamma` means each point only influences its immediate neighborhood, closer
to memorizing individual training points (high variance, overfitting risk).

### Linear regression

```python
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.datasets import load_diabetes

Xd, yd = load_diabetes(return_X_y=True)
Xd_train, Xd_test, yd_train, yd_test = train_test_split(Xd, yd, test_size=0.2, random_state=42)

lr = LinearRegression()
lr.fit(Xd_train, yd_train)
preds = lr.predict(Xd_test)
print("R2:", round(r2_score(yd_test, preds), 4))
print("RMSE:", round(mean_squared_error(yd_test, preds) ** 0.5, 2))
```
```
R2: 0.4526
RMSE: 53.85
```

An `R²` of `0.45` means the model explains about 45% of the variance in the target — a
realistic, unremarkable number on a genuinely noisy real-world dataset (this is the classic
`load_diabetes` toy dataset), included specifically because a curated tutorial that only ever
shows `R² > 0.9` teaches an unrealistic expectation of what real tabular data looks like.
`mean_squared_error(..., squared=False)` is available for RMSE directly in most sklearn
versions; taking the square root explicitly here is equivalent and unambiguous across
versions.

### K-Means clustering

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

km = KMeans(n_clusters=3, random_state=42, n_init=10)
labels = km.fit_predict(X)
print("inertia:", round(km.inertia_, 2))
print("silhouette:", round(silhouette_score(X, labels), 4))
```
```
inertia: 78.85
silhouette: 0.5528
```

K-Means is **unsupervised** — `fit_predict` never sees `y` at all, just groups points by
proximity. `inertia_` is the sum of squared distances from each point to its assigned
cluster's center — it always *decreases* as `n_clusters` increases (more clusters can only
ever fit the data at least as well), which is exactly why it can't be used alone to *choose*
`k` — the "elbow method" (plotting inertia across a range of `k` and looking for where the
improvement rate flattens) is the common informal approach.
**`silhouette_score`** is the more principled metric: it measures, per point, how much closer
it is to its own cluster than to the nearest *other* cluster, averaged and bounded in
`[-1, 1]` — unlike inertia, it doesn't trivially favor more clusters, and can genuinely be
used to compare different values of `k` against each other.

### PCA (dimensionality reduction)

```python
from sklearn.decomposition import PCA

pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)
print("explained variance ratio:", pca.explained_variance_ratio_.round(4))
print("shape:", X_pca.shape)
```
```
explained variance ratio: [0.9246 0.0531]
shape: (150, 2)
```

The original iris data has 4 features; PCA's first 2 components alone capture `92.46% +
5.31% = 97.77%` of the total variance — a direct, quantified answer to "how much information
am I actually losing by projecting down to 2D for visualization or for a downstream model."
The mechanism (principal components as eigenvectors of the covariance matrix) is covered in
[`ml-fundamentals-deep-dive.md`](ml-fundamentals-deep-dive.md#dimensionality-reduction-pca),
building directly on [NumPy's `np.linalg.eig`](../numpy/README.md#linear-algebra-nplinalg).

## Cross-validation and hyperparameter search, as library calls

The theory of *why* cross-validation exists (and its failure modes) is in
[`ml-fundamentals-deep-dive.md`](ml-fundamentals-deep-dive.md#cross-validation-why-a-single-traintest-split-isnt-enough) — this is
what actually running it looks like:

```python
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier

scores = cross_val_score(RandomForestClassifier(n_estimators=50, random_state=42), X, y, cv=5)
print("5-fold scores:", scores.round(3))
print("mean +/- std:", round(scores.mean(), 4), round(scores.std(), 4))
```
```
5-fold scores: [0.967 0.967 0.933 0.967 1.   ]
mean +/- std: 0.9667 0.0211
```

`cross_val_score` handles the fold-splitting, per-fold fitting, and per-fold scoring
internally — the standard way to get a far more reliable performance estimate than a single
train/test split, since it reports both a mean *and* how much that estimate actually varies
across different subsets of the data (`std=0.0211` here — a tight, reassuring spread; a large
std would be a signal the model's performance is genuinely unstable depending on which rows
happen to land in training vs. evaluation).

```python
param_grid = {"n_estimators": [50, 100], "max_depth": [2, 3, 5]}
grid = GridSearchCV(RandomForestClassifier(random_state=42), param_grid, cv=5, scoring="accuracy")
grid.fit(X_train, y_train)
print("best params:", grid.best_params_)
print("best CV score:", round(grid.best_score_, 4))
print("test score:", round(grid.best_estimator_.score(X_test, y_test), 4))
```
```
best params: {'max_depth': 3, 'n_estimators': 50}
best CV score: 0.9583
test score: 0.9667
```

`GridSearchCV` exhaustively tries every combination in `param_grid` (here, `2 × 3 = 6`
combinations), cross-validating each one, and exposes the winning configuration directly —
`grid.best_estimator_` is already refit on the *full* training set using the winning
hyperparameters (the default `refit=True` behavior), ready to use or evaluate immediately,
no separate manual refit step required. For a large hyperparameter space where trying every
combination is too expensive, `RandomizedSearchCV` (same interface, samples a fixed number
of random combinations instead of every one) or a genuine Bayesian search (`scikit-optimize`,
Optuna) are the standard next steps — worth reaching for once a grid search's combinatorial
cost (which grows multiplicatively with every parameter added) becomes impractical.

## Persisting a fitted model

```python
import joblib

joblib.dump(grid.best_estimator_, "model.joblib")
loaded = joblib.load("model.joblib")
print(loaded.score(X_test, y_test))
```
```
0.9666666666666667
```

`joblib` (not the standard library's `pickle` directly, though it's pickle-based under the
hood) is scikit-learn's own recommended persistence mechanism — it's meaningfully more
efficient than raw `pickle` specifically for objects containing large NumPy arrays (a fitted
model's learned coefficients/tree structures), which is exactly what every scikit-learn
estimator is made of internally. The same caveat that applies to any pickle-based format
applies here: a model saved with one scikit-learn/NumPy version isn't guaranteed to load
cleanly on a very different version — pin dependency versions around a saved model in
production, or use [MLflow](../mlflow/README.md)'s model format (which wraps this same
`joblib` mechanism together with explicit environment/dependency metadata) for anything
beyond local experimentation.

## Relationship to other tools in this repo

- **[NumPy](../numpy/README.md)** — every estimator's `X` input is a 2D NumPy array (or
  something that converts cleanly to one); the shape/dtype/broadcasting rules there are the
  literal contract this entire API is built on.
- **[pandas](../pandas/README.md)** — the natural way real tabular data arrives before it
  reaches a `ColumnTransformer`; scikit-learn accepts a DataFrame directly and (since recent
  versions) can preserve column names through `.get_feature_names_out()` as shown above.
- **[XGBoost](../xgboost/README.md)** — a single, more heavily-optimized algorithm family
  (gradient-boosted trees) that deliberately implements this same `.fit()`/`.predict()`
  contract specifically so it drops into `Pipeline`/`GridSearchCV` unmodified — reach for it
  directly over `RandomForestClassifier`/`GradientBoostingClassifier` once tabular
  performance genuinely matters more than scikit-learn's broader algorithm variety.
- **[MLflow](../mlflow/README.md)** — tracks experiment parameters/metrics and versions the
  saved model artifact; scikit-learn itself has no experiment-tracking or model registry of
  its own.
- **[`ml-fundamentals-deep-dive.md`](ml-fundamentals-deep-dive.md)** — the theory this doc
  intentionally left out: bias-variance, regularization, gradient descent, evaluation
  metrics, feature engineering, and hyperparameter tuning strategy.
