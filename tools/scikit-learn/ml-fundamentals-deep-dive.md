# ML Fundamentals, Deep Dive: Bias-Variance, Regularization, Gradient Descent, Evaluation

Part of [`README.md`](README.md)'s scikit-learn section, but this file is about the theory
underneath the library, not the library API. [`../xgboost/README.md`](../xgboost/README.md)
already covers ensemble methods (bagging vs. boosting), regularization, and second-order
gradient descent **specifically as they apply to gradient-boosted trees** — this file covers
the same concepts in general, and is meant to be read alongside that one, not instead of it.
Every number below was actually computed against real (if synthetic, where noted) data using
scikit-learn 1.7.2 and NumPy 2.2.6 — nothing here is asserted without a verified run backing
it.

## The bias-variance tradeoff

### The problem, concretely

A model's total prediction error on new data can be decomposed into three sources: **bias**
(error from a model too simple to capture the real pattern — it's systematically wrong in
the same direction, regardless of which training sample it saw), **variance** (error from a
model so flexible it fits the specific noise in *this* training sample — it would produce a
substantially different fit on a different sample of the same underlying data), and
irreducible noise (randomness in the data itself that no model can predict). The tradeoff is
structural, not a limitation of any particular algorithm: **reducing bias by adding model
flexibility almost always increases variance, and reducing variance by constraining a model
almost always increases bias.** There is no free lunch here — the practical skill is finding
where, for a specific dataset, that tradeoff is best balanced, not eliminating the tradeoff.

### Seeing it directly

Fitting polynomials of increasing degree to noisy data generated from a true
`sin(1.5πx)` function:

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(0)
X = np.sort(rng.uniform(0, 1, 60)).reshape(-1, 1)
y = np.sin(1.5 * np.pi * X.ravel()) + rng.normal(0, 0.2, X.shape[0])
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

for degree in [1, 4, 15]:
    model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
    model.fit(X_train, y_train)
    train_mse = mean_squared_error(y_train, model.predict(X_train))
    test_mse = mean_squared_error(y_test, model.predict(X_test))
    print(f"degree={degree:2d}  train_mse={train_mse:.4f}  test_mse={test_mse:.4f}")
```
```
degree= 1  train_mse=0.2083  test_mse=0.3549
degree= 4  train_mse=0.0393  test_mse=0.0367
degree=15  train_mse=0.0316  test_mse=0.0785
```

Read across the three rows and the whole tradeoff is visible in six real numbers:

- **`degree=1`** (a straight line trying to fit a curve): both train *and* test error are
  high — the model is too simple to capture the pattern even on data it was trained on. This
  is **high bias / underfitting**.
- **`degree=4`**: both errors are low and close to each other — the model has enough
  flexibility to capture the real curve without chasing individual noisy points. This is the
  best-balanced point in this specific example.
- **`degree=15`**: train error is the *lowest* of the three (`0.0316`) — the model can nearly
  interpolate the exact training points — but test error is *worse* than `degree=4`'s
  (`0.0785` vs `0.0367`). The gap between train and test error, which barely exists at
  `degree=4`, has reopened. This is **high variance / overfitting**: the model has started
  fitting the specific noise in this particular training sample, which doesn't generalize.

**The diagnostic this generalizes into**: a large gap between training performance and
validation/test performance is the direct, measurable signature of high variance; both
training and validation performance being poor *together* is the signature of high bias. This
single check — "is my train score good and my validation score bad" vs. "are both scores
bad" — is the first, most important diagnostic question to ask about any underperforming
model, before reaching for any specific fix.

## Regularization: L1, L2, and why they behave differently

Regularization addresses variance directly: it adds a penalty term to the loss function that
discourages large coefficient values, trading a small amount of bias for a (usually larger)
reduction in variance.

```python
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(1)
n, p = 100, 10
X = rng.normal(0, 1, (n, p))
true_coef = np.array([3.0, -2.0, 0.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0])  # only 3 features matter
y = X @ true_coef + rng.normal(0, 1, n)
X_scaled = StandardScaler().fit_transform(X)

lr = LinearRegression().fit(X_scaled, y)
ridge = Ridge(alpha=5.0).fit(X_scaled, y)
lasso = Lasso(alpha=0.3).fit(X_scaled, y)

print("true coef:  ", true_coef)
print("plain LR:   ", lr.coef_.round(2))
print("ridge:      ", ridge.coef_.round(2))
print("lasso:      ", lasso.coef_.round(2))
```
```
true coef:   [ 3.  -2.   0.   0.   1.5  0.   0.   0.   0.   0. ]
plain LR:    [ 3.37 -1.72 -0.07  0.12  1.4  -0.08 -0.1  -0.01 -0.03  0.18]
ridge:       [ 3.22 -1.67 -0.07  0.12  1.34 -0.09 -0.09 -0.   -0.05  0.17]
lasso:       [ 3.19 -1.45 -0.    0.    1.15 -0.   -0.   -0.   -0.    0.  ]
```

Only 3 of the 10 features actually matter for generating `y` — the other 7 have a true
coefficient of exactly zero. Plain linear regression assigns small but genuinely nonzero
weight to every one of those 7 irrelevant features, because with finite, noisy data it has no
way to distinguish "genuinely zero" from "very small but real" — it fits whatever pattern,
including pure noise, happens to exist in this particular sample. **Lasso (L1 penalty)
zeroed out exactly the 7 irrelevant features**, recovering the true sparsity pattern almost
exactly — this isn't a coincidence of this example, it's the actual mechanical behavior L1
regularization produces: the L1 penalty's geometry (a diamond-shaped constraint region in
coefficient space, with sharp corners sitting exactly *on* the axes) means the loss-minimizing
point frequently lands exactly on a corner — a coefficient of precisely zero — rather than
merely close to zero. **Ridge (L2 penalty)** shrinks every coefficient toward zero
proportionally but essentially never produces an exact zero (L2's constraint region is a
smooth circle/sphere with no corners for the optimum to land on) — it reduces variance without
performing feature selection.

**The practical implication**: reach for **Lasso** when you have reason to believe many
features are genuinely irrelevant and want the model to perform feature selection as part of
fitting; reach for **Ridge** when you believe most features carry at least some real signal
and just want to control the *magnitude* of every coefficient (common with correlated
features, where Lasso's sharp all-or-nothing selection can be unstable — it may arbitrarily
pick one of two highly correlated features and zero the other). **`ElasticNet`** blends both
penalties (a weighted sum of the L1 and L2 terms) specifically to get some sparsity while
being more stable than pure Lasso under correlated features — the standard practical default
when you're not sure which of the two pure penalties is the better fit. For the tree-specific
version of this same idea (L1/L2 regularization on leaf weights, not linear coefficients),
see [`../xgboost/README.md`](../xgboost/README.md)'s `reg_alpha`/`reg_lambda` coverage — same
underlying goal (controlling variance), a mechanically different target.

## Ensemble methods: bagging vs. boosting

Covered in depth, with the tree-specific mechanism, in
[`../xgboost/README.md`](../xgboost/README.md#the-problem-it-solves-and-why-boosting-instead-of-one-big-model)
— the short version, stated generally rather than tree-specifically: **bagging** (random
forests) trains many independent, high-variance models on resampled data and averages them,
which cancels out variance without touching bias (each individual model is still just as
prone to overfitting its own bootstrap sample; averaging many *independent* overfits mostly
cancels out, the way averaging many independent noisy measurements converges toward the true
value). **Boosting** trains models sequentially, each one correcting the previous ensemble's
residual error, which directly attacks bias — but because each new model is chasing whatever
error remains, unconstrained boosting can eventually start fitting noise, which is exactly
why boosting algorithms lean so heavily on regularization (shrinkage/learning rate, tree
depth limits, explicit L1/L2 penalties) to keep the variance side of that bias-reduction
trade in check as more rounds are added. This is the general bias/variance framing the
`RandomForestClassifier` feature-importance example in
[`README.md`](README.md#decision-tree-and-random-forest-classification) is an instance of.

## Gradient descent: how a model actually learns its parameters

### The mechanism, from scratch

Most of the models in this doc (linear/logistic regression, and — via backpropagation — every
neural network) are fit by iteratively adjusting parameters in the direction that reduces a
loss function, one small step at a time:

```python
import numpy as np

rng = np.random.default_rng(42)
n = 200
X = rng.normal(0, 1, (n, 1))
true_w, true_b = 4.0, -1.0
y = true_w * X.ravel() + true_b + rng.normal(0, 0.5, n)

def gradient_descent(X, y, lr, n_iters=50):
    n = len(y)
    w, b = 0.0, 0.0
    for i in range(n_iters):
        y_pred = w * X.ravel() + b
        error = y_pred - y
        grad_w = (2 / n) * np.sum(error * X.ravel())
        grad_b = (2 / n) * np.sum(error)
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b

for lr in [0.001, 0.1, 1.5]:
    w, b = gradient_descent(X, y, lr)
    print(f"lr={lr:<6} -> w={w:.3f}, b={b:.3f}   (true: w=4.0, b=-1.0)")
```
```
lr=0.001 -> w=0.298, b=-0.105   (true: w=4.0, b=-1.0)
lr=0.1   -> w=3.959, b=-0.991   (true: w=4.0, b=-1.0)
lr=1.5   -> w=-301790343602310.562, b=2271566175857117.000   (true: w=4.0, b=-1.0)
```

The mechanism, made concrete: `grad_w`/`grad_b` are the loss function's partial derivatives
with respect to each parameter — the direction of *steepest increase* in loss. Subtracting a
small multiple of that gradient (`lr`, the learning rate) moves the parameters in the
direction that *decreases* loss. All three runs use the identical algorithm and identical
data — only `lr` differs, and the outcome is qualitatively different in each case:

- **`lr=0.001`** — after 50 steps, `w` has only crawled to `0.298`, nowhere near the true
  `4.0`. Too small a learning rate wastes computation taking steps that are individually too
  timid to converge within a reasonable number of iterations.
- **`lr=0.1`** — converges to `w=3.959, b=-0.991`, close to the true values. A well-chosen
  learning rate.
- **`lr=1.5`** — the parameters don't converge, they **diverge to astronomically large
  values**. A learning rate too large causes each update to overshoot the minimum by more
  than the previous step's error, and each overshoot gets *larger*, not smaller — a real,
  common failure mode, not a hypothetical one, and the direct reason training loss suddenly
  becoming `NaN` or `inf` partway through a real training run is almost always a
  too-large-learning-rate problem, not a data problem.

### The practical variants

- **Batch gradient descent** (shown above) — computes the gradient using the *entire*
  training set on every single step. Accurate, but a single parameter update requires a full
  pass over all data — impractical once a dataset is large.
- **Stochastic Gradient Descent (SGD)** — computes the gradient from a **single** random
  example per step. Each individual step is a noisy, imprecise estimate of the true
  gradient, but steps are enormously cheaper, and that noise is often a genuine *benefit*,
  not just a cost — it can help the optimizer escape shallow local minima that batch gradient
  descent would get stuck in.
- **Mini-batch gradient descent** — the practical default nearly everything actually uses:
  compute the gradient from a small batch (commonly 32–256 examples) per step, balancing
  batch GD's stability against SGD's per-step cheapness and its noise-driven ability to
  escape poor local minima.
- **Momentum / Adam and other adaptive optimizers** — augment plain gradient descent with a
  running average of past gradients (momentum, which accelerates consistent movement and
  dampens oscillation) and, in Adam's case, a per-parameter adaptive learning rate derived
  from the recent magnitude of each parameter's own gradients. These exist specifically to
  reduce sensitivity to the exact learning-rate-selection problem demonstrated above — Adam
  is the practical default for training neural networks for exactly this reason.

For the second-order (Newton's method — using the *curvature*, not just the slope, to choose
a smarter step) variant XGBoost specifically uses when building trees, see
[`../xgboost/README.md`](../xgboost/README.md#the-objective-function).

## Cross-validation: why a single train/test split isn't enough

### The problem, seen directly

```python
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

X, y = make_classification(n_samples=120, n_features=15, n_informative=6, n_redundant=4,
                            flip_y=0.1, class_sep=0.7, random_state=7)

single_split_scores = []
for seed in range(6):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=seed)
    scaler = StandardScaler().fit(X_train)
    model = LogisticRegression(max_iter=5000).fit(scaler.transform(X_train), y_train)
    single_split_scores.append(model.score(scaler.transform(X_test), y_test))

print("single-split scores across 6 random seeds:", [round(s, 4) for s in single_split_scores])
print("range:", round(max(single_split_scores) - min(single_split_scores), 4))

cv_scores = cross_val_score(LogisticRegression(max_iter=5000), StandardScaler().fit_transform(X), y, cv=5)
print("5-fold CV scores:", cv_scores.round(4))
print("CV mean/std:", round(cv_scores.mean(), 4), round(cv_scores.std(), 4))
```
```
single-split scores across 6 random seeds: [0.5, 0.6667, 0.6667, 0.5333, 0.6333, 0.6333]
range: 0.1667
5-fold CV scores: [0.75   0.625  0.6667 0.6667 0.5417]
CV mean/std: 0.65 0.0677
```

**The exact same model, the exact same data, evaluated with a single `train_test_split`,
reports anywhere from `0.50` to `0.6667` accuracy depending purely on which random seed
happened to be used** — a `0.1667` swing on a modestly-sized dataset, purely from which rows
happened to land in the test set. Reporting any single one of those numbers as "the model's
accuracy" is reporting noise as if it were signal. **k-fold cross-validation** (`cv=5` here)
splits the data into `k` folds, trains on `k-1` of them and evaluates on the held-out fold, `k`
times, rotating which fold is held out — every row gets used for evaluation exactly once,
across the full run. The result isn't just a more reliable *mean* estimate (`0.65` here) — the
**std** (`0.0677`) is itself real, useful information: it directly quantifies how much this
specific model/dataset combination's performance estimate should be trusted, which a single
train/test split has no way to report at all.

`StratifiedKFold` (what `cross_val_score` uses by default for a classifier) additionally
preserves each class's proportion within every fold — the classification analogue of the
`stratify=y` argument on `train_test_split` covered in [`README.md`](README.md), and matters
for the identical reason: without it, a fold could end up with a wildly different class
balance than the overall dataset purely by chance, especially on a small or imbalanced
dataset.

## Evaluation metrics: the accuracy trap, made concrete

```python
import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (confusion_matrix, precision_score, recall_score, f1_score,
                              roc_auc_score, average_precision_score, accuracy_score)

X, y = make_classification(n_samples=2000, n_features=10, n_informative=5,
                            weights=[0.95, 0.05], flip_y=0.02, random_state=42)
print("positive rate:", round(y.mean(), 4))

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
scaler = StandardScaler().fit(X_train)
model = LogisticRegression(max_iter=2000).fit(scaler.transform(X_train), y_train)
preds = model.predict(scaler.transform(X_test))
proba = model.predict_proba(scaler.transform(X_test))[:, 1]

print("accuracy:", round(accuracy_score(y_test, preds), 4))
print("confusion matrix:\n", confusion_matrix(y_test, preds))
print("precision:", round(precision_score(y_test, preds), 4))
print("recall:", round(recall_score(y_test, preds), 4))
print("roc-auc:", round(roc_auc_score(y_test, proba), 4))
print("pr-auc:", round(average_precision_score(y_test, proba), 4))
```
```
positive rate: 0.0605
accuracy: 0.9383
confusion matrix:
 [[563   1]
 [ 36   0]]
precision: 0.0
recall: 0.0
roc-auc: 0.7583
pr-auc: 0.2032
```

Read this output carefully, because it's a genuinely dramatic, real result: the model reports
**93.83% accuracy** — a number that sounds like a clear success — while its **precision and
recall are both exactly `0.0`**. The confusion matrix explains why: at the default 0.5
probability threshold, the model predicted a positive outcome for only **one single row in
the entire 600-row test set**, and got even that one wrong (`0` true positives). Because
positives make up only 6% of this data, a model that essentially always predicts "negative"
is *right* on accuracy nearly all the time — and a model that trivially predicts "negative"
for literally everything scores **94.0% accuracy**, actually *higher* than this trained
model's default-threshold accuracy, while being obviously useless.

**This is why accuracy is the wrong metric to report or optimize on imbalanced data, full
stop** — not a caveat, a disqualifying flaw for this use case. The two metrics that reveal
what accuracy hides:

- **ROC-AUC (`0.7583`)** — the probability a randomly chosen positive example is ranked
  above a randomly chosen negative one by the model's predicted probabilities. Genuinely
  threshold-independent (it doesn't depend on the 0.5 cutoff that made precision/recall look
  like `0`), and `0.7583` shows the model *has* learned real signal — it just isn't being
  surfaced by the default classification threshold.
- **PR-AUC (`0.2032`)** — area under the precision-recall curve, looking only at how the
  model does specifically on the positive class. It's low here, appropriately — precision-
  recall tradeoffs are much harder to make look good on rare positives than ROC-AUC is,
  because ROC-AUC's false-positive-rate axis is diluted by the huge number of true negatives
  that are trivial to get right. **This divergence between a decent ROC-AUC and a much less
  flattering PR-AUC is itself the diagnostic signal**: whenever the two disagree this much,
  trust PR-AUC as the more honest picture of real-world usefulness on rare-positive data. See
  [`../xgboost/README.md`](../xgboost/README.md#why-pr-auc-not-accuracy-on-imbalanced-data)
  for this same conclusion reached independently in a tree-based-model, real-fraud-detection
  context.

**Regression metrics**, for comparison, don't have this specific trap (there's no "class
imbalance" to hide behind) but do differ in what they emphasize: **MSE** (mean squared
error) penalizes large errors disproportionately (squaring amplifies outliers); **MAE** (mean
absolute error) treats every unit of error equally, making it more robust to a few extreme
outliers dominating the metric; **RMSE** (√MSE) converts back to the target's original units
for interpretability while keeping MSE's large-error sensitivity; **R²** expresses the
fraction of the target's variance the model explains, `1.0` being a perfect fit and `0.0`
being no better than always predicting the mean — see
[`README.md`](README.md#linear-regression)'s real `R²=0.4526` example for what an honest,
unremarkable-but-real number looks like on genuinely noisy data.

## Feature engineering: scaling is not optional for every algorithm

```python
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

X, y = make_classification(n_samples=500, n_features=10, random_state=3)
X[:, 0] = X[:, 0] * 1000   # one feature on a wildly different scale than the rest
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

svm_unscaled = SVC().fit(X_train, y_train)
print("SVM, unscaled features:", round(svm_unscaled.score(X_test, y_test), 4))

scaler = StandardScaler().fit(X_train)
svm_scaled = SVC().fit(scaler.transform(X_train), y_train)
print("SVM, scaled features:  ", round(svm_scaled.score(scaler.transform(X_test), y_test), 4))
```
```
SVM, unscaled features: 0.5133
SVM, scaled features:   0.9067
```

**Identical data, identical model, identical hyperparameters — the only difference is
whether the features were scaled to comparable ranges first — and accuracy moves from
`51.33%` (barely better than a coin flip on this roughly-balanced problem) to `90.67%`.**
The mechanism: `SVC`'s `rbf` kernel (and k-nearest-neighbors, k-means, and any other
algorithm whose core operation is a **distance** or **dot product** between feature vectors)
treats every feature's raw numeric scale as directly meaningful — a feature ranging in the
thousands mechanically dominates the distance calculation over features ranging in single
digits, regardless of which feature is actually more *informative*. `StandardScaler`
(subtract the mean, divide by the standard deviation — putting every feature on a comparable
scale) removes this artifact entirely. **The rule this implies**: any algorithm built on
distance, dot products, or gradient descent over raw feature values (SVMs, k-NN, k-means,
linear/logistic regression, neural networks) needs scaled input to behave sensibly; tree-based
models (decision trees, random forests, gradient boosting) are a genuine exception — a tree
split threshold like `feature > 1500` works identically well whether that feature is scaled
or not, since trees only ever compare a feature to a threshold, never combine multiple
features' raw magnitudes together the way a distance or dot product does.

Feature *selection* — reducing which features are used at all, not just their scale — is
covered under regularization above (Lasso) and can also be done directly via
`SelectKBest`/`RFE` (recursive feature elimination) when a filter- or wrapper-based approach
is preferred over relying on a specific model's built-in regularization.

## Imbalanced data: `class_weight` and the precision/recall tradeoff

```python
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score

# same imbalanced dataset and split as the evaluation-metrics section above
model = LogisticRegression(max_iter=2000, class_weight="balanced").fit(
    scaler.transform(X_train), y_train
)
preds = model.predict(scaler.transform(X_test))
print("confusion matrix:\n", confusion_matrix(y_test, preds))
print("precision:", round(precision_score(y_test, preds), 4))
print("recall:", round(recall_score(y_test, preds), 4))
```
```
confusion matrix:
 [[403 161]
 [  9  27]]
precision: 0.1436
recall: 0.75
```

`class_weight="balanced"` reweights the loss function so mistakes on the rare (positive)
class count proportionally more than mistakes on the common (negative) class — mechanically,
it multiplies each class's contribution to the gradient by a factor inversely proportional to
that class's frequency. The effect, measured directly: **recall jumps from `0.0` to `0.75`
— the model now correctly catches 75% of true positives it previously caught none of** — at
the direct cost of precision dropping to `0.1436` (161 false positives, vs. only 1 before).
**This is a real tradeoff, not a strict improvement** — which side of it is worth taking
depends entirely on the actual cost of each error type in the specific problem (a missed
fraud case vs. a false fraud alert have very different real costs, and that cost ratio, not
a default setting, is what should actually decide how aggressively to reweight). Beyond
`class_weight`, the other standard levers are **resampling** (oversampling the minority
class — SMOTE being the standard synthetic-oversampling technique — or undersampling the
majority class) and **threshold tuning** (moving the classification cutoff away from the
default `0.5` using the precision-recall curve to pick a threshold matching the actual
cost tradeoff, rather than accepting scikit-learn's default cutoff as though it were
meaningful for every problem).

## Hyperparameter tuning: grid search's real cost, and why random search works

```python
import time
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier

X, y = load_breast_cancer(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
param_grid = {"n_estimators": [50, 100, 150], "max_depth": [3, 5, 7, None], "min_samples_leaf": [1, 2, 4]}
# 3 x 4 x 3 = 36 combinations

t0 = time.perf_counter()
grid = GridSearchCV(RandomForestClassifier(random_state=42), param_grid, cv=3, n_jobs=-1).fit(X_train, y_train)
t_grid = time.perf_counter() - t0
print(f"grid search:   36 combos, best={grid.best_score_:.4f}, time={t_grid:.2f}s")

t0 = time.perf_counter()
rand = RandomizedSearchCV(RandomForestClassifier(random_state=42), param_grid, n_iter=10, cv=3,
                           random_state=42, n_jobs=-1).fit(X_train, y_train)
t_rand = time.perf_counter() - t0
print(f"random search: 10 combos, best={rand.best_score_:.4f}, time={t_rand:.2f}s")
```
```
grid search:   36 combos, best=0.9626, time=2.09s
random search: 10 combos, best=0.9560, time=0.27s
```

Grid search's cost grows **multiplicatively** with every hyperparameter added (3 values × 4
values × 3 values = 36 fits here, each one also multiplied by the number of CV folds) — add
one more hyperparameter with 3 candidate values and the total jumps to 108, not 39. Random
search, sampling a **fixed** number of combinations regardless of how large the underlying
grid is, found a score within `0.007` of grid search's best result using only `10/36 ≈ 28%`
of the fits, in about **8x less wall-clock time** — a real, measured example of the general
principle that most hyperparameters in a typical grid contribute far less to final
performance than one or two dominant ones, so exhaustively covering every combination of the
*unimportant* ones is largely wasted computation. For a genuinely large or expensive search
space, the next step beyond random sampling is **Bayesian optimization** (Optuna,
scikit-optimize) — using the results of already-tried combinations to intelligently choose
which combination to try next, rather than grid search's exhaustiveness or random search's
obliviousness to what's already been learned.

## Dimensionality reduction: PCA

[`README.md`](README.md#pca-dimensionality-reduction) shows PCA's *usage* — this is the
mechanism behind those numbers. PCA finds a new set of axes (**principal components**),
ordered by how much of the data's total variance each one captures, such that projecting
onto the first few captures as much of the original information as possible in as few
dimensions as possible. Mechanically, those axes **are the eigenvectors of the data's
covariance matrix**, and each component's captured variance is exactly its corresponding
**eigenvalue** — built directly on
[NumPy's `np.linalg.eig`](../numpy/README.md#linear-algebra-nplinalg), covered there. This is
why `README.md`'s iris example reporting `[0.9246, 0.0531]` as `explained_variance_ratio_`
is a precise, principled number and not a heuristic: it's the literal proportion of total
variance each eigenvector accounts for, which is exactly what makes PCA a genuine, quantified
answer to "how much information would be lost" rather than a black-box dimensionality
reduction trick.
