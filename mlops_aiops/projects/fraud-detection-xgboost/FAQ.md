# fraud-detection-xgboost — FAQ

Interview-style questions and answers about this specific project, ordered
easy → very hard. Every answer refers to the actual code in this repo, not
generic textbook material — file paths are given so you can go verify each
claim against the source.

## Tools & technologies used

| Layer | Tool | Where it shows up |
|---|---|---|
| Model | **XGBoost** (`xgboost.XGBClassifier`) | `src/fraud_detection/train.py` |
| Baseline model | **scikit-learn** `LogisticRegression` + `ColumnTransformer`/`Pipeline` | `train_baseline_logreg.py` |
| Data manipulation | **pandas** / **numpy** | throughout |
| Metrics | **scikit-learn** (`average_precision_score`, `roc_auc_score`, `confusion_matrix`, `classification_report`) | `train.py`, `evaluate.py` |
| Experiment tracking + model registry | **MLflow** (SQLite backend) | `train.py`, `evaluate.py`, `serve.py` |
| Feature store | **Feast** (`Entity`, `FeatureView`, `FeatureService`, local provider/SQLite online store) | `feature_repo/`, `feast_features.py`, `train_with_feast.py` |
| Drift monitoring | **Evidently** (`Report`, `DataDriftPreset`, `Dataset`, `RemoteWorkspace`) | `monitor.py` |
| Serving | **FastAPI** + **Pydantic** + **Uvicorn** | `serve.py` |
| Data ingestion | **requests** against Zenodo's public REST/file API | `data.py` |
| Testing | **pytest** + `unittest.mock` | `tests/` |
| Environment/dependency management | **uv** (`pyproject.toml` + `uv.lock`) | project root |
| Optional deployment target | **Kubernetes + Helm** (`k8s/k8s_mlops/practice/evidently_stack`) — `monitor.py` can push reports there via `RemoteWorkspace` | `../../../k8s/k8s_mlops/` |
| Environment quirk fix | `NLTK_DISABLE_IMPORT_SECURITY=1` — NLTK 3.10+'s import-security guard false-positives on Evidently's transitive NLTK dependency under uv/Jupyter | see `docs/tools/evidently/README.md` |

---

## Tier 1 — Foundations

### What does this project actually do, end to end?

Downloads a real (if imperfect — see Tier 2) fraud dataset, trains an
XGBoost classifier on it, tracks the run in MLflow, registers the resulting
model, evaluates whatever's currently registered, generates an Evidently
drift report comparing the training period against a later period, and
serves predictions over HTTP. Every stage is a separate, independently
runnable module (`data.py`, `features.py`, `train.py`, `evaluate.py`,
`monitor.py`, `serve.py`) rather than one monolithic script — deliberately,
so each concern (ingest, train, evaluate, monitor, serve) can be run,
tested, and reasoned about on its own.

### Why XGBoost specifically, and not logistic regression or a neural net?

**This answer used to be wrong, asserted without a measured comparison —
corrected once one actually existed.** The original reasoning (trees handle
mixed scales without normalization, capture non-linear feature
interactions, and `scale_pos_weight` gives a clean imbalance lever) is
real, standard reasoning for *why gradient-boosted trees are a defensible
choice for tabular fraud data in general*. But "defensible in general" and
"actually better on this dataset" are different claims, and only the
first one had been checked. Once `train_baseline_logreg.py` (see Tier 3B)
was actually built and run, logistic regression scored **PR-AUC 0.9252**
against XGBoost's **0.6758** on the identical chronological split — the
simpler model won, clearly, not by a rounding error. The honest answer is
now: XGBoost was a reasonable default to reach for first, but on *this*
dataset it's currently the wrong choice, and that was only knowable by
actually building the comparison, not by reasoning about tree properties
in the abstract. See Tier 3B for why this might be true (the `v1`-`v28`
features are PCA components — linear combinations by construction — which
plausibly makes a linear decision boundary a genuinely good fit here) and
what would need to happen before trusting either number long-term
(hyperparameter tuning, cross-validation given only ~40 fraud cases per
test split). XGBoost itself comes from Chen & Guestrin's 2016 KDD paper,
*"XGBoost: A Scalable Tree Boosting System"* (arXiv:1603.02754) — verified
directly, not assumed; being a real, well-founded algorithm doesn't make
it the right one for every dataset.

### Walk through the pipeline stage by stage.

`data.py` downloads the raw CSV from Zenodo into a git-ignored `data/`
directory, caching it so repeat runs don't re-download. `features.py`
splits the raw dataframe into a leakage-free `X`/`y` pair and produces a
*chronological* train/test split. `train.py` fits an `XGBClassifier` with
`scale_pos_weight` set from the training split's actual imbalance ratio,
logs params/metrics/the model to MLflow, and registers it under the name
`fraud-xgboost`. `evaluate.py` independently reloads whatever's registered
(not necessarily what `train.py` just produced) and scores it against a
fresh test split. `monitor.py` builds an Evidently `Report` comparing the
train-period feature distributions against the test-period ones. `serve.py`
loads the registered model once at startup and exposes it over a FastAPI
`/predict` endpoint.

---

## Tier 2 — Data & Feature Engineering

### Why this dataset over the other four you were given?

Of the five, only three have fraud labels at all — UK Government Purchase
Card doesn't, so it's structurally unusable for supervised classification
regardless of any other quality. Of the remaining three (this one, Credit
Card Fraud (ULB), PaySim, IEEE-CIS), this is the only one with a public,
no-authentication download URL — the other two are Kaggle-hosted and need
an API token, which is friction this project's "don't store/commit
anything, keep it reproducible from source" goal doesn't need.

### What did you find when you actually inspected the raw file, and why does it matter?

Two things, found by `curl`-ing the file directly rather than trusting the
Zenodo abstract: first, the row structure isn't uniform — some rows carry
dense `v1`–`v28` PCA-like features matching the well-known ULB Credit Card
Fraud schema almost exactly (same value ranges, even the same famous
`amount=149.99` example transaction), while other rows have `v1`–`v28`
mostly zero with a PaySim-style balance pattern instead. That's not what
you'd expect from one homogeneous live production feed, and it's a
legitimate reason to be skeptical of the dataset's "live production system"
framing. Second — more actionable — `fraud_probability`, `risk_level`,
`confidence`, and `recommendation` are the *source* system's own outputs,
not independent signal. This matters because a resume-line claim of
"deployed a fraud model" is worthless if the model secretly cheated by
reading its own answer key; catching this before it reaches the model is
the actual skill being tested here, not the training loop itself.

### Explain the leakage mechanism concretely — how would a model exploit `risk_level` if you left it in?

`risk_level` in the raw data is `"HIGH"` almost exactly when `is_fraud=1`
and `"LOW"`/`"MEDIUM"` otherwise (verified directly on the sample rows in
the raw file). One-hot-encode that column and hand it to any classifier,
and it will learn a near-perfect decision rule — "if `risk_level_HIGH == 1`,
predict fraud" — that has nothing to do with the actual transaction
features. Offline metrics would look outstanding (because the label
appears twice, once as itself and once relabeled as a categorical
"feature"). In real production, this model would never see `risk_level` at
prediction time — it doesn't exist until *after* a fraud-detection system
(possibly this very model) has already run — so the trained model would
collapse to near-random performance the moment it hit real traffic.
`config.LEAKAGE_COLUMNS` and `features.build_feature_matrix` exist
specifically to prevent this, and `tests/test_features.py` asserts none of
the four leakage columns ever reach `X`.

### Why a chronological split instead of a random one? What actually breaks with a random split here?

Two independent things break. First, information leakage: fraud patterns
evolve over time (new attack techniques, seasonal spending shifts); a
random 70/30 split lets "future" transactions — with future-only patterns —
appear in training, giving the model information it couldn't have had in a
real deployment and inflating offline metrics relative to what you'd see in
production. Second, and specific to this project: `monitor.py`'s entire
premise is comparing a "reference" (training) period against a "current"
(test) period for drift. If that split were random, both halves would be
statistically identical samples of the same overall distribution by
construction — there would be no real temporal drift for Evidently to find,
and a clean drift report would be a false negative, not evidence of
stability. `features.temporal_train_test_split` sorts by `timestamp` first
(guaranteed by `data.load_dataset`) and splits by position specifically to
avoid both problems.

### "Don't store/commit the data" — how is that actually enforced, not just written in a README?

Three concrete mechanisms, not just a promise: (1) `data.py`'s
`RAW_DATA_PATH` points inside `data/`, and `.gitignore` lists `data/`
explicitly — verified directly with `git check-ignore -v
data/banking_fraud_raw.csv`, which confirmed the file is excluded, not just
assumed to be. (2) The dataset is fetched from its public Zenodo URL at
run time, not vendored into the repo at all — delete `data/` and rerun, and
it reproduces from source. (3) `mlflow.db`, `evidently_report.html`, and
`mlruns/` — all of which could otherwise leak a copy of the data via
logged artifacts — are also git-ignored for the same reason.

---

## Tier 2B — Feature Store (Feast)

### Why does this project use Feast at all, and why IP address as the entity?

Feast solves **training/serving skew**: a naive setup computes "features"
once in a training script and again, separately, in serving code, and the
two implementations quietly drift apart over time. Feast gives one shared
definition, retrieved two different ways — a point-in-time-correct
historical join for training, a latest-value lookup for serving. This
dataset has no persistent customer/account ID at all, so `ip_address` is
the only column that legitimately *recurs* across transactions (most of
56,965 distinct IPs appear once; a few are reused dozens to hundreds of
times — verified directly against the raw file) — exactly the shape Feast
is built for. A `transaction_id`-keyed entity would technically work but
would demonstrate nothing about Feast's actual value: a one-off event ID
never recurs, so there'd be no "history" for a point-in-time join to
retrieve.

### Walk through the leakage-safety mechanism in `build_ip_velocity_source` precisely.

`df.groupby("ip_address")["amount"].shift(1)` shifts each IP's amount
series down by one position *within that group* — so the value now aligned
with row *i* is row *i-1*'s amount, not row *i*'s own. Only after that
shift does `.expanding().mean()` run, so the running mean at row *i*
covers rows `0..i-1`, never row *i* itself. The first occurrence of any IP
has nothing to shift into position 0, so it's `NaN`, explicitly
`fillna(0)`'d to a documented sentinel meaning "no prior history" — the
same semantic `ip_prior_txn_count=0` already carries via `cumcount()`,
which is 0-indexed by construction and needs no shift at all. This was
verified empirically, not just reasoned about: run against IP
`185.75.225.22` (reused 425 times), `ip_prior_txn_count` increments
`0, 1, 2, ..., 424` in exact timestamp order, and `ip_prior_fraud_count`
only increases at the timestamps of that IP's *actual* prior fraud labels.

### Is using `ip_prior_fraud_count` — a fraud label from other rows — leakage?

No, and the distinction matters: using the **current row's own** `is_fraud`
as an input feature would be leakage (predicting the label from itself).
Using **other, strictly earlier** transactions' confirmed labels from the
same recurring entity is a completely different, legitimate thing — it's
the "this IP has a fraud history" signal real fraud systems actually use
("reputation" or "prior offense count" features). The requirement is
exactly the one enforced above: the label being read must be *causally
available before* the row being predicted, never the row's own label.

### What actually happens, mechanically, in `get_historical_features()`'s point-in-time join?

For every `(ip_address, event_timestamp)` pair in the entity dataframe
handed to it, Feast finds, in the `ip_velocity_stats` `FileSource`, the
most recent row for that same `ip_address` with an `event_timestamp` at or
before the requested one, and returns its feature values — never a later
row, even if one exists in the source. In `train_with_feast.py`, the
entity dataframe *is* `train_df[["ip_address", "timestamp"]]` — i.e. every
transaction asks "what were my own IP's stats as of my own timestamp,"
which (because the underlying source was itself built with the
strictly-prior `shift(1)` logic above) correctly excludes that very
transaction from its own feature values twice over — once by construction
in the source, once by the point-in-time join only ever looking backward.

### You reported *zero* measurable improvement from adding these features. Isn't that a failure?

It's a real, honestly-reported empirical result, and a more valuable one
than a cherry-picked improvement would have been. Verified directly: the
dominant IP-reuse burst (425 occurrences of one IP) is concentrated
2026-04-10 to 2026-04-13, but the 70%-by-*row-count* split boundary lands
at 2026-01-22 — three months earlier — because transaction density is
wildly non-uniform across the 4-month span (dense in January, sparse
after). Net effect: **all 429 nonzero feature occurrences in the entire
dataset landed in the test split; zero in training.** The model correctly
learned to ignore three constant-zero training columns — that's not a
bug in Feast, in the feature design, or in the model; it's a genuine
methodological mismatch between "split by row count" and "split by
calendar time" when event density isn't uniform. This is exactly the kind
of failure a real MLOps team discovers *after* deploying a feature that
tested fine offline — this project surfaced it before deployment instead,
which is the entire point of actually running the pipeline rather than
just writing the code.

### Given that finding, what would you actually change — and is that in scope for this project?

The fix is a **calendar-time split** (e.g. "train on Jan–Mar, test on
Apr", or repeated rolling-origin splits across several calendar windows)
instead of a row-count-based one — that would put earlier occurrences of
reused IPs into training, giving the model real, non-degenerate exposure
to the feature during fitting. That's a deliberate scope boundary, not an
oversight: the ask here was "implement Feast," which this does correctly
and verifiably end-to-end (point-in-time join, materialization, and a live
online-store lookup all confirmed working); *re-deriving the train/test
split methodology* is a separate, `features.py`-level change with its own
knock-on effects on every already-reported baseline number in this
README/FAQ, and changing it silently alongside an unrelated feature-store
request would risk conflating two different decisions.

### `train_with_feast.py` registers a *separate* model (`fraud-xgboost-feast`) instead of replacing `train.py`'s. Why?

So the comparison is honest and reproducible. If `train.py` were modified
in place to add Feast features, the previously-reported baseline numbers
(PR-AUC 0.6758, the 96.4%/67.5% precision/recall breakdown) would silently
become unverifiable — there'd be no way to re-run "the exact thing that
produced those numbers" anymore. Two separate registered models means
`evaluate.py`/`serve.py` can load either one explicitly, and the
"identical PR-AUC" finding above is a real A/B comparison between two
models that both actually exist, not an inference from a diff.

---

## Tier 3 — Modeling & Evaluation

### The fraud rate is 0.17%. What's wrong with accuracy here, and what did you use instead?

A model that predicts "not fraud" for every single transaction scores
99.83% accuracy while catching zero fraud — accuracy is dominated entirely
by the majority class at this imbalance ratio, so it can't distinguish a
useless model from a good one. This project uses two fixes on two
different sides of the same problem: on the *training* side,
`scale_pos_weight` (ratio of negative to positive examples in the training
split) tells XGBoost's loss function to weight a missed fraud case roughly
as heavily as it would weight ~580 missed non-fraud cases, so the optimizer
can't win by ignoring the minority class. On the *evaluation* side, the
headline metric is PR-AUC (`sklearn.metrics.average_precision_score`), not
accuracy or even plain ROC-AUC — PR-AUC is far more sensitive to
performance specifically on the rare positive class, which is the class
that actually matters for fraud.

### What does `scale_pos_weight` actually do inside XGBoost's objective function?

It's a multiplicative weight applied to the gradient and Hessian of
positive-class examples during boosting, effectively telling the loss
function "a false negative on this example costs `scale_pos_weight` times
as much as a false positive would." This project computes it as
`(y_train == 0).sum() / (y_train == 1).sum()` — the actual imbalance ratio
observed in the training split, not a hand-picked constant — so it adapts
automatically if the class balance shifts between retrains (e.g. if a newer
Zenodo version of this dataset has a different fraud rate).

### Explain precisely how `average_precision_score` differs from "area under the PR curve," and why that distinction is deliberate.

This is a real, easy-to-miss subtlety and worth stating exactly.
Scikit-learn's own docs define AP as
`AP = Σₙ (Rₙ − Rₙ₋₁) · Pₙ` — a weighted sum of precision at each observed
threshold, weighted by the *increase* in recall since the previous
threshold — and state explicitly: *"This implementation is not interpolated
and is different from computing the area under the precision-recall curve
with the trapezoidal rule, which uses linear interpolation and can be too
optimistic."* The reason interpolation is misleading here: unlike an ROC
curve, precision is not guaranteed to be achievable at intermediate recall
values by linear interpolation between two real operating points — a
naive trapezoidal AUC-PR can report a value higher than any threshold you
could actually deploy at. This project's README calls the metric "PR-AUC"
loosely (matching how most practitioners talk about it); precisely, it's
average precision, and the two are close but not identical by definition,
not just by numerical coincidence.

### You got 96% precision / 67% recall at the default 0.5 threshold. Is 0.5 the right threshold for fraud? How would you actually choose it?

Almost certainly not, and 0.5 was never chosen deliberately here — it's
`predict_proba(...) >= 0.5`, the default anyone gets by not thinking about
it. The right threshold depends on a real cost trade-off this project
doesn't model: what does one missed fraud case cost the bank (the fraud
amount, plus reputational/regulatory cost) versus what does one false
positive cost (a blocked legitimate transaction, customer friction,
support-ticket load)? In a real deployment you'd sweep the threshold across
the precision-recall curve, pick the point matching the bank's actual cost
ratio (often recall-favoring, since a missed six-figure fraud usually costs
more than a handful of annoyed customers), and — critically — that
threshold decision belongs to risk/fraud-ops stakeholders, not to whoever
trained the model.

### You had a real false negative in your own demo — the duplicated $149.99 transaction. What does that tell you, and how would you investigate it?

Concretely: several rows in the raw file share byte-identical feature
values (`amount=149.99`, the exact same 28 `v` values) and are all labeled
fraud, and a live `/predict` call reproducing that exact pattern came back
`fraud_probability: 0.0`. Two hypotheses, and the honest answer is "I
didn't fully resolve which": either (a) this exact repeated pattern landed
overwhelmingly in the *training* split under the temporal sort (its
`time_value=0` suggests it's early in the timeline), so the *test*-period
evaluation genuinely never got to test the model's behavior on it and this
one call just happened to hit a pattern the model wasn't stress-tested on;
or (b) it's a real model shortcoming on a specific, narrow attack pattern.
To actually distinguish these, the next step is a **model debugging**
exercise (not a training-loop change): pull every row matching this exact
duplicated pattern, check which split each fell into, and if several
occurrences are in the test set and the model missed all of them, use
Evidently's or XGBoost's own feature-importance/SHAP tooling to see which
specific `v` features are driving the model away from flagging it.

---

## Tier 3B — Baseline Comparison & ColumnTransformer

### Why does `ColumnTransformer` show up in the logistic regression baseline but nowhere in `train.py`/`train_with_feast.py`?

Because it would do nothing there, verified rather than assumed: training
XGBoost on raw `amount` vs. `log1p(amount)` produced **byte-identical
predictions** (max absolute difference `0.0`) — decision trees split on
`feature <= threshold`, and any strictly monotonic transform of one
feature just relabels the threshold; the partition of the data is
unchanged. Scaling has the same non-effect for the same reason (trees don't
compare magnitudes *across* features the way a dot product does).
Logistic regression has no such invariance — it fits a linear decision
boundary in whatever coordinate space you hand it, so both the *scale* and
the *shape* of each feature's distribution matter to what it can learn.
`amount` ranges from $0.02 to $659,035 with a skew of ~74; without
addressing that, a linear model either needs an enormous coefficient to
react to rare large values or effectively ignores small ones.
`ColumnTransformer` is precisely the tool for "treat this one column
differently, treat the rest uniformly" — `log1p` + `StandardScaler` on
`amount` alone, plain `StandardScaler` on everything else, in one
`Pipeline` object.

### Walk through exactly what `build_pipeline` does, column by column.

`ColumnTransformer`'s `"log_amount"` branch is itself a two-step
sub-`Pipeline` — `FunctionTransformer(np.log1p)` then `StandardScaler()` —
applied only to `["amount"]`. Its `"scale_rest"` branch is a plain
`StandardScaler()` applied to every other numeric feature column
(`time_value`, `v1`–`v28`, and — when run via the Feast-augmented
features — the three IP-velocity columns too, since `build_pipeline`
takes the actual column list at call time rather than a hardcoded one).
`ColumnTransformer` concatenates both branches' outputs back into one
matrix in a fixed column order, which is what `LogisticRegression` then
fits on. Nothing here special-cases the Feast columns differently from
the raw ones — they'd all just get `StandardScaler`, the same as
`time_value`, since none of them share `amount`'s skew problem.

### Why put the whole thing in a `Pipeline` and log *that* to MLflow, instead of scaling manually before calling `.fit()`?

This is the training/serving-skew fix flagged as a gap back in Tier 8 for
the XGBoost path, actually closed here: `mlflow.sklearn.log_model(pipeline,
...)` persists the fitted `ColumnTransformer` (its learned means/variances
from `StandardScaler`, not just the `LogisticRegression` coefficients) as
part of one artifact. Anything that loads `models:/fraud-logreg-baseline/latest`
and calls `.predict_proba()` on a raw, unscaled dataframe gets correct
results automatically — there is no separate scaler object to keep in sync,
version, or accidentally skip at serving time. Compare this to `serve.py`'s
current `/predict`/`/predict_feast`, which work only because their models
happen to need zero preprocessing; the moment either needed one, those
endpoints would be exposed to exactly the skew risk this pipeline avoids.

### You measured logistic regression beating XGBoost. Is that the final word — should the registry's `champion` alias (Tier 4) point at it now?

No, and saying otherwise would repeat the same mistake this section just
corrected — trading one unverified claim for another. Two things need
checking before trusting this result long-term, not just accepting the
better number: **first**, neither model's hyperparameters were tuned —
`LogisticRegression`'s defaults (aside from `class_weight="balanced"`) and
`XGBClassifier`'s reasonable-but-arbitrary `max_depth=5`/`learning_rate=0.1`
were never searched, so this is "sklearn defaults vs. one arbitrary XGBoost
config," not "the best linear model vs. the best tree ensemble." **Second**,
the test period has only ~40 fraud examples (Tier 3's evaluate.py numbers)
— a metric computed on 40 positive examples has enough variance that a
single chronological split isn't strong enough evidence to retire XGBoost
from consideration. The right next step is the same one already proposed
in Tier 8 for a different reason: repeated rolling-origin splits, for both
models, before any alias points at either one with confidence.

---

## Tier 4 — MLOps: Tracking & Registry

### What's the difference between MLflow "tracking" and the "model registry" in this codebase specifically?

Tracking is the append-only experiment log — every call to
`mlflow.log_params`/`log_metrics`/`log_model` inside `train.py`'s
`with mlflow.start_run()` block writes to it, and it's what
`mlflow ui --backend-store-uri sqlite:///mlflow.db` browses. The registry
is a separate, named, versioned pointer *on top of* tracking — the single
line `registered_model_name="fraud-xgboost"` in `train.py`'s
`mlflow.xgboost.log_model(...)` call is what creates version 1, version 2,
etc. of a model named `fraud-xgboost`, independent of how many total
training runs exist in the tracking log. `evaluate.py` and `serve.py` never
touch the tracking log at all — they only ever ask the registry for
`models:/fraud-xgboost/latest`, which is the actual point of having a
registry: consumers don't need to know which specific run produced the
model they're loading.

### Why SQLite instead of the default MLflow backend?

Current MLflow versions put the plain filesystem tracking store
(`file:./mlruns`) into maintenance mode and refuse to use it by default —
verified directly against a real run earlier in this project's history, not
assumed from older tutorials that still show `file:` URIs. `sqlite:///mlflow.db`
is MLflow's own currently-recommended local store, and it's also a
practical requirement here specifically: the **model registry** (used by
this project) has never been supported by the plain file store at all — it
needs a real backing database, even a lightweight one like SQLite.

### `evaluate.py` and `serve.py` both load `models:/fraud-xgboost/latest`. What's actually wrong with that in a real production setting?

`"latest"` means "the highest version number ever registered" — full stop.
It carries zero information about whether that version passed any quality
gate, was reviewed, or is even better than the version before it; a bad
training run that got registered last would become "latest" immediately
and both `evaluate.py` and `serve.py` would happily load it. This is real,
verified behavior in this project — it still works exactly as coded — but
it's not what MLflow itself currently recommends: MLflow deprecated the old
Staging/Production **stages** model back in 2.9 in favor of **aliases**
(`models:/fraud-xgboost@champion`), which are just as easy to query
(`models:/<name>@<alias>`) but are only ever *moved* onto a version by an
explicit action — meaning nothing becomes "champion" by accident the way
everything automatically becomes "latest."

### How would you implement a real promotion gate here — train, evaluate, only then mark as deployable?

Add a step after `train.py` registers a new version, before anything treats
it as servable: run `evaluate.py`'s scoring logic against that *specific*
new version (not `"latest"`), compare its PR-AUC against the PR-AUC of
whatever version currently holds the `champion` alias, and only call
`MlflowClient().set_registered_model_alias("fraud-xgboost", "champion",
new_version)` if it's actually better (or, more realistically for fraud,
if it passes an absolute minimum bar — e.g. recall above some floor at an
acceptable precision — set by risk/fraud-ops, not just "better than
before"). `serve.py` and `evaluate.py` would then both load
`models:/fraud-xgboost@champion` instead of `.../latest`, so a bad training
run simply never reaches production regardless of when it was registered.

---

## Tier 5 — Monitoring

### Why is reference=train / current=test a meaningful comparison, and what would be wrong with reference=random-half / current=other-random-half?

Because the split is chronological, "reference vs. current" here actually
means "the period the model was trained on vs. a later period it wasn't" —
exactly the comparison a real deployed model faces every day (was the world
still like this when I trained, or has it moved?). A random 50/50 split
would produce two samples of the *same* underlying distribution by
construction (no time ordering preserved), so any drift Evidently reported
would be sampling noise, not a signal about anything real — and worse, it
would give false confidence that "there's no drift" when the real question
(has anything changed since training) was never actually asked.

### `monitor.py` only runs `DataDriftPreset`. What kind of drift would this setup miss entirely, and why?

**Concept drift** — the relationship between features and the label
changing, independent of whether the feature distributions themselves
moved. `DataDriftPreset` compares `X_train` against `X_test` feature-by
-feature; it has no visibility into `is_fraud` at all in this project's
usage (only features are passed to `Dataset.from_pandas`, not the label).
If fraudsters started using a *new pattern within the same feature ranges*
already present in training — say, previously-benign combinations of `v`
values start being used for fraud — the feature distributions could look
completely stable while the model's real-world accuracy silently collapses.
Catching that would require comparing prediction/label distributions
over time (a `ClassificationPreset`-style comparison, once ground-truth
labels are available), not feature drift alone — a real limitation of this
project's current `monitor.py`, not something it already handles.

### Mechanically, what actually happens when `monitor.py` pushes a report to a remote Evidently server?

`Report([DataDriftPreset()]).run(current, reference)` computes the whole
report **locally, inside this project's process** — no network call yet.
Only afterward does `RemoteWorkspace(server_url).create_project(...)` and
`.add_run(project.id, snapshot, include_data=False)` make HTTP calls: the
first creates (or reuses) a project via the server's API, the second
serializes the already-computed `Snapshot` and `POST`s it to the server,
which stores it in its own workspace (backed by whatever storage that
particular server was configured with — see
`k8s/k8s_mlops/practice/evidently_stack`'s PVC-backed `/workspace`) and renders it in its
UI. The compute-vs-storage split matters: `include_data=False` means the
underlying `X_train`/`X_test` rows themselves are never uploaded, only the
report's computed statistics — relevant given this project's whole premise
of not letting the raw data leave this machine unnecessarily.

---

## Tier 6 — Serving & Production Readiness

### Walk through exactly what happens from `curl POST /predict` to the JSON response.

FastAPI validates the request body against the `Transaction` Pydantic
model — if any of the 30 required floats is missing or the wrong type, the
request is rejected with a 422 before `predict()` even runs, without any
extra code needed for that check. `get_model()` returns the module-level
`_model` global, loading it via `mlflow.xgboost.load_model(...)` on the
*first* call only (a deliberate cold-start-once pattern — reloading from
the registry on every request would be needlessly slow). `transaction.model_dump()`
turns the validated Pydantic object back into a plain dict, which
`pd.DataFrame([...])` wraps into a single-row dataframe — mirroring the
exact column shape `build_feature_matrix` produces during training, which
is what actually matters here, not the dict-to-DataFrame conversion itself.
`model.predict(X)` (an XGBoost `Booster`, not a scikit-learn wrapper) is
called, and its single float output is returned directly.

### Why does `model.predict()` here return a probability directly, without needing `predict_proba`?

`mlflow.xgboost.load_model` returns a native `xgboost.Booster` (verified by
reading MLflow's own `xgboost` flavor source directly) — not the
scikit-learn-API `XGBClassifier` used in `train.py`. A `Booster` has no
`predict_proba` method at all; for a model trained with
`objective="binary:logistic"`, its single `.predict()` method already
returns the sigmoid-activated probability of the positive class directly,
by definition of that objective. This is a real, sharp edge worth knowing:
the *training*-side model object and the *serving*-side model object are
different Python types with different APIs, even though they represent
the same underlying trained model.

### What's actually missing here to call this "production ready"?

Concretely, in the order they'd bite first at real scale: (1) no
authentication/authorization on `/predict` at all — anyone reaching the
port can query the fraud model; (2) no request logging of inputs/outputs,
which means there's no way to build tomorrow's "current" dataset for
`monitor.py` from real traffic — this project's monitoring only ever
compares two slices of the *same static historical dataset*, never live
predictions; (3) no model hot-reload — a newly promoted `champion` version
requires restarting the process, there's no polling/webhook to pick up a
change; (4) no input-range validation beyond "is it a float" — a
`v1=1e300` is currently accepted and fed straight to the model; (5) no
latency/throughput testing at all, despite fraud detection typically
needing sub-second (often sub-100ms) response times in a real payment flow.

### How would you close the loop so predictions from `serve.py` become the "current" data `monitor.py` compares against?

Log every `(features_in, prediction_out, timestamp)` from `/predict` to
somewhere durable — a database table or an append-only file, not just
process memory — then change `monitor.py`'s "current" argument from
`test_df` (a static historical slice) to a query over that live-prediction
log for, say, the last 24 hours. This converts drift monitoring from "did
the historical test period differ from the historical training period"
(a one-time, backward-looking check, which is all this project currently
does) into "is *today's real traffic* drifting from training" — the
actually useful form of the same tool in a live deployment.

---

## Tier 7 — Testing

### Why does `test_train.py` mock `load_dataset` and use synthetic data instead of hitting the real Zenodo download?

Three separate reasons, each sufficient on its own: determinism (a network
call can fail or the remote file can change, making the test flaky for
reasons unrelated to the code being tested), speed (downloading and
training on all 57k real rows on every test run is unnecessarily slow for
what should be a fast feedback loop), and isolation (a unit test for
"does the training function run correctly" shouldn't also be a test for
"is Zenodo reachable right now" — those are different failure modes that
deserve different tests, or in this project's case, only the first is
tested at all).

### You found a real bug in your own test — `run.info.status`. Explain exactly why that assertion was wrong.

`mlflow.start_run()` returns an `ActiveRun` object whose `.info` is a
**snapshot taken at the moment the run started**, not a live view — it is
never refreshed afterward, including after the `with` block's `__exit__`
actually ends the run in the tracking store. So `run.info.status` reads
`"RUNNING"` forever on that specific object, even though the real run
genuinely finished (confirmed independently: the model was successfully
registered and metrics were computed, visible in the captured stdout). The
fix — `mlflow.get_run(run.info.run_id).info.status` — re-fetches from the
tracking store instead of trusting the stale in-memory object, and
correctly reads `"FINISHED"`. This is a good example of a subtle
distinction between "an object that represents a run" and "the run's
actual current state," which don't automatically stay in sync just because
they're related.

### How would you test `data.py`'s download/caching logic without hitting the network in CI?

Mock `requests.get` (e.g. with `unittest.mock.patch("fraud_detection.data.requests.get")`
returning a fake `Response` with known `.content`) and assert three
behaviors separately: that a fresh call with no cached file writes to
`RAW_DATA_PATH` and calls `requests.get` exactly once; that a second call
with the file already present does *not* call `requests.get` again unless
`force=True`; and that `force=True` re-downloads even when a cached file
exists. None of that requires a real network call or the real 21MB file —
the caching *logic* is what's under test, not Zenodo's availability.

---

## Tier 8 — Systems Design / Principal-Level Curveballs

### This dataset gets new versions over time on Zenodo. Design a retraining pipeline around that fact.

A trigger (scheduled, e.g. weekly, or event-driven via a Zenodo webhook if
one existed) checks the record's version/DOI for a new release, and if
found: (1) downloads the new version into a *separate* path so the current
serving data isn't disturbed mid-check; (2) retrains via `train.py` against
combined old+new data (or just new, depending on whether older patterns
still matter — a real judgment call, not a technical one); (3) runs the
promotion gate from Tier 4's registry question — evaluate the new candidate
against the current `champion`'s bar before it's eligible; (4) only on
passing, reassigns the `champion` alias; (5) critically, **keeps the
previous champion's alias assignment recorded** (MLflow's registry
naturally supports this — aliases just move, they don't delete history) so
a rollback is "move the alias back," not "retrain from scratch under
pressure."

### How would you detect training-serving skew specifically for this pipeline — not just data drift?

Data drift (what `monitor.py` currently checks) asks "do live feature
distributions look like training ones." Training-serving skew is a
narrower, code-level question: "does the *exact feature computation* at
serving time match what happened at training time." Concretely here: does
`serve.py`'s `pd.DataFrame([transaction.model_dump()])` produce columns in
the same dtype and order as `features.build_feature_matrix` did during
training? A cheap, concrete test: log the feature vector actually sent to
the model on every `/predict` call, periodically replay a sample of
*training* rows through the exact same `/predict` code path, and diff the
model's live-served prediction against the offline prediction
`evaluate.py` computes for the identical row — any nonzero difference on
identical input is skew, by definition, regardless of what the data itself
looks like.

### If this had to run at real bank scale — millions of transactions/day, sub-100ms p99 — what in this codebase wouldn't survive?

Ranked by how quickly it would break: (1) `serve.py`'s
`mlflow.xgboost.load_model` call under lazy `if _model is None` global
state is not thread-safe or multi-worker-safe as written — under real
concurrency (multiple Uvicorn workers), each process independently loads
its own copy, which is fine for the model itself but means a `champion`
alias change requires restarting every worker, with no coordinated rollout;
(2) there's no batching — one HTTP round-trip and one `Booster.predict`
call per transaction is fine at demo scale, but a real payment processor
would want a gRPC or in-process SDK path with request batching to hit
sub-100ms reliably at volume; (3) SQLite as the MLflow backend is
explicitly a local/single-writer choice — a real deployment needs a real
database (Postgres/MySQL) behind MLflow, which is documented as
MLflow's own production recommendation, not a gap specific to this project's
code.

### Your own EDA found this dataset might be synthetic/mixed rather than genuinely homogeneous production traffic. What governance risk does that create if this model were actually deployed?

If a bank deployed a model trained on data whose actual provenance doesn't
match its documented provenance, that's a direct violation of the model
documentation and validation expectations laid out in **SR 11-7** (the
Federal Reserve/OCC's 2011 model risk management guidance) — specifically
its requirement that a model's *conceptual soundness* be evaluated,
including whether the data used to build it is representative of the
population it will be applied to. A model quietly trained on a blend of a
famous public benchmark and synthetic PaySim-style patterns, then deployed
under the assumption it learned genuine live production behavior, would
fail that representativeness check the moment an internal model-risk review
actually inspected the training data — which is precisely why this
project's README states the provenance concern explicitly rather than
letting it surface later, in a real audit, as a much more expensive
surprise.

### What single decision in this project would you defend hardest in a design review, and what's the strongest argument against it?

The chronological train/test split. It's the right call for the reasons in
Tier 2 and Tier 5 — it's what makes the drift-monitoring story coherent at
all, and it avoids look-ahead bias. The strongest real counter-argument:
with only 98 total fraud cases across the whole dataset, a chronological
split risks an unlucky test period containing very few (or unusually many)
fraud examples purely by when they happened to occur — `evaluate.py`'s test
period here has only 40, and any metric computed on 40 examples has wide
enough variance that a single differently-timed split could shift PR-AUC
by a meaningful amount. A defensible response: this project reports a
single split's numbers as a demonstration, not a claim of measured
production performance — a real deployment would want repeated
*rolling-origin* time-series cross-validation (multiple chronological
splits at different points) specifically to get a confidence interval
around PR-AUC, not a single point estimate from one arbitrarily-placed cut.
