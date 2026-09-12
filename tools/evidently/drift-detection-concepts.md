# Drift detection: your custom pattern vs. Evidently

A runnable companion notebook builds a small, isolated example of every
drift type covered below and shows exactly which Evidently metric/preset
catches each one:
[`projects/evidently-monitoring-demo/drift_types_with_evidently.ipynb`](../../../projects/evidently-monitoring-demo/drift_types_with_evidently.ipynb).

## Your mental model, restated

The pattern described: at training time you capture a **model benchmark**
(reference statistics/performance from training or a held-out set); at
inference time you **capture a sample of inference results** (inputs and
predictions); once **actual/ground-truth outcomes arrive**, you compare the
captured results against the actual outcomes to detect drift.

That's a real, well-established pattern — it's usually called **outcome-based
drift monitoring** or **concept drift monitoring**, and it's exactly what a
custom implementation reaching for "compare predictions to reality" naturally
converges on. Nothing wrong with it. But it's only half of what "drift
detection" usually means in tools like Evidently — and the missing half is
the more valuable one to add, because it doesn't need to wait for anything.

## Widely accepted types of drift

Before mapping your pipeline onto Evidently, it helps to have the standard
vocabulary — drift is usually classified along two independent axes: **what
changes**, and **how it unfolds over time**.

### What changes

| Type | Definition | Example |
|---|---|---|
| **Data drift** (covariate shift) | Input feature distribution P(X) changes; the input→output relationship stays the same | An e-commerce model trained on desktop-heavy traffic sees a sudden surge in mobile users after a marketing push — the feature mix shifted, but "what makes someone buy" hasn't |
| **Label drift** (prior probability shift) | The distribution of the target variable P(Y) itself changes | A fraud model sees fraud rate jump from 1% to 4% of transactions during a holiday shopping surge — nothing about *how* fraud looks changed, just how *often* it occurs |
| **Concept drift** | The actual relationship between inputs and outputs, P(Y\|X), changes — the same input now means something different | A credit-risk model: a borrower profile that predicted low default risk pre-recession no longer does, because the economic relationship between income/job-type and default changed |
| **Prediction drift** | The distribution of the model's *own outputs* changes | A churn model that historically predicted ~5% churn starts predicting ~20% churn on new traffic — a downstream symptom that something upstream shifted, detectable without knowing true outcomes yet |

Data and label drift are sometimes grouped as **"virtual drift"** (the world
looks different but the model's learned rule could still be valid), while
concept drift is **"real drift"** (the rule itself is now wrong). The
distinction matters because virtual drift might not hurt accuracy at all,
while real drift always eventually does.

### How it unfolds over time

| Type | Definition | Example |
|---|---|---|
| **Sudden / abrupt drift** | An instant regime change at a clear point in time | COVID-19 lockdowns instantly changing retail/travel demand patterns overnight |
| **Gradual drift** | Slow transition where old and new patterns overlap for a while before the new one dominates | Customer browsing shifting from desktop to mobile over several months, with both patterns coexisting during the transition |
| **Incremental drift** | Continuous small steps with no single transition point — the change is the accumulation, not any one moment | Inflation slowly raising what counts as a "normal" transaction amount, month over month, gradually invalidating fixed fraud thresholds |
| **Recurring / seasonal drift** | The concept cycles back and forth predictably | Retail demand spiking every holiday season then reverting — a "drift" by definition, but a predictable, cyclical one |

A monitoring setup ideally names drift along both axes at once — e.g.
"gradual concept drift in the risk model" tells you both what to fix (the
label/prediction relationship) and how urgently. This is also why a single
point-in-time `Report` isn't enough on its own: it can tell you *that*
something drifted between two snapshots, but only a sequence of runs over
time (the trend-history table discussed in the [main
README](README.md#worked-example-xgboost-batch-classifier-scored-every-4-hours))
reveals *which kind* — sudden, gradual, incremental, or recurring.

## The distinction that matters: two different drift problems

| | Needs ground truth? | When can it run? | What it catches |
|---|---|---|---|
| **Covariate / feature drift** | No — compares input feature distributions only | Immediately, the moment you have a batch of inference inputs | Upstream data changes: a source system changing units, a new user segment showing up, a broken ETL job silently changing a column's range |
| **Prediction drift** | No — compares the *model's own output distribution* over time | Immediately | The model behaving differently on new inputs even before you know if it's right — often the earliest warning sign |
| **Concept / performance drift** | Yes — needs the actual outcome to compare against the prediction | Delayed, until ground truth catches up (hours/days/weeks depending on your labeling lag) | Confirmed accuracy/error degradation — the "did it actually get worse" answer |

**Your custom implementation covers only the third row.** That's not a
criticism — it's the row that answers the question people actually care
about ("is the model still accurate"). But it also means every signal you
get is inherently delayed by however long it takes ground truth to arrive.
If that lag is days or weeks, you find out about a problem days or weeks
after it started.

Evidently's `DataDriftPreset` and the prediction-drift metrics inside it
cover the first two rows **for free, with no ground truth required at
all** — run them the moment `current_data` (your captured inference sample)
exists, same as you already do for capture, just without waiting for the
outcome step. This is the concrete thing you'd gain by adopting it: an
earlier, label-free warning that something changed, on top of whatever
your existing ground-truth comparison already tells you.

## How Evidently mechanizes the comparison

Structurally, Evidently's inputs are exactly the two artifacts you already
have — it doesn't ask you to change how you capture anything:

- **`reference_data`** = your model benchmark. A pandas DataFrame: the
  training/held-out data, its features, and (for the performance side) the
  model's own predictions and true labels on it.
- **`current_data`** = your captured inference sample. Same shape: features,
  predictions, and — once available — the actual outcome column.

What Evidently adds is the *comparison machinery* in between:

- **Per-column statistical test selection.** Rather than one fixed
  comparison method applied to every column (e.g. a single PSI calculation,
  or a mean/std z-score check), Evidently infers each column's type
  (numerical, categorical, text) and picks an appropriate test by default —
  Wasserstein distance or KS-test for numerical columns depending on sample
  size, chi-squared/PSI for categorical columns — and lets you override the
  test per column explicitly if you want a specific one (PSI, KS, etc.) If
  your custom implementation hardcoded one method across all columns, this
  is the generalization of that.
- **A drift score and drift verdict per column**, then a **dataset-level
  aggregate** (`dataset_drift`) based on what *share* of columns are
  individually flagged as drifted (default: more than 50%). This is worth
  internalizing on its own — see the note in the [main
  README](README.md#change-log) about a single drifted column not tripping
  the dataset-level flag; it's intentional, and it means per-column results
  usually matter more than the single aggregate boolean.
- **Full metric suites for the performance side**, not a single number.
  `ClassificationPreset()`/`RegressionPreset()` compute confusion matrices,
  per-class precision/recall, ROC curves, calibration, and a "quality by
  feature" breakdown (which feature values correlate with the model doing
  worse) — reference vs. current, in one call. If your custom comparison
  step computes one delta (e.g. accuracy dropped by X%), this is
  substantially more diagnostic surface for the same delayed-feedback step
  you already have.
- **`TestSuite` as the declarative version of your alerting logic.** If
  your custom code has an `if drift_measure > threshold: alert` branch
  somewhere, `TestSuite` is the same idea made explicit and reusable —
  e.g. `TestAccuracyScore(gte=0.8)`, `TestShareOfDriftedColumns(lt=0.3)` —
  pass/fail assertions you can run in CI or a scheduled job instead of
  bespoke conditional logic.

## Direct mapping: your pieces to Evidently's pieces

| What you built | Evidently equivalent | What changes |
|---|---|---|
| Model benchmark captured at training time | `reference_data` | Same artifact and purpose — this already *is* a reference dataset. Keep the raw feature values (not just summary stats) so Evidently's tests have something to compare against. |
| Captured portion of inference results | `current_data` | Same artifact — Evidently is indifferent to how you sampled or stored it. |
| Waiting for actual outcomes before comparing | Only required for `ClassificationPreset`/`RegressionPreset` | `DataDriftPreset` (features + predictions) does **not** need to wait — run it the moment `current_data` exists. Your existing "wait for ground truth" step maps onto the performance presets only, run later once the outcome column is populated. |
| Custom "compare captured vs. actual" function | `ClassificationPreset()` / `RegressionPreset()` inside a `Report` | Replaces hand-written metric-delta code with a standard, broader metric suite and a defined drift/degradation verdict. |
| Whatever threshold decided "yes, this is drift" | `TestSuite` with per-metric thresholds, or `Report`'s built-in drift-share default | Turns ad hoc thresholds scattered in code into declarative, versioned config that reads like a spec. |

## What Evidently does not replace

To be direct about the boundary, since it matters for deciding how much of
the custom implementation to keep:

- **The capture/sampling mechanism itself** — how much inference traffic
  to log, where it's stored, retention — is still entirely your pipeline's
  job. Evidently only consumes the DataFrame you hand it.
- **The ground-truth joining/labeling pipeline** — matching outcomes back
  to the original predictions — stays yours.
- **Historical trend storage across runs.** A `Report`/`TestSuite` run is a
  single point-in-time comparison; it has no memory of previous runs. You
  still append results to your own store to get a trend line (see the
  Delta-table pattern in the [Databricks worked
  example](README.md#worked-example-xgboost-batch-classifier-scored-every-4-hours)).
- **Domain-specific comparisons Evidently doesn't ship**, e.g. a
  business-metric-based drift check (revenue impact, downstream conversion
  rate). If your custom implementation checks something like that alongside
  statistical drift, keep it — Evidently is a replacement for the standard
  statistical layer, not for every check you might want.
- **Deciding when to refresh the benchmark/reference set.** Whether the
  reference stays fixed at training time or gets periodically rebased is a
  policy call Evidently doesn't make for you.

## How you'd have used this, concretely

Overlaying Evidently onto the pipeline as described:

1. **Training step (unchanged):** wherever the benchmark currently gets
   computed, also persist the underlying DataFrame (features + the model's
   own predictions + true labels on the held-out set) as `reference_data` —
   a file, table, or Delta table, whatever your existing capture mechanism
   already writes to.
2. **Inference capture step (unchanged):** keep capturing the sampled
   portion of inference results — features + predictions — into
   `current_data`, exactly as today.
3. **New, immediate step — no longer waiting on anything:** as soon as a
   batch of `current_data` exists, run
   `Report(metrics=[DataDriftPreset()])` comparing it to `reference_data`.
   This is a step your custom implementation doesn't currently have at
   all, and it's the earliest possible signal — same-batch, not
   same-outcome-lag.
4. **Ground-truth arrival step (where your custom comparison lives today):**
   once actual outcomes land and get joined into the captured batch, run
   `Report(metrics=[ClassificationPreset()])` (or `RegressionPreset()`) in
   place of the custom compare-to-actual function. Wrap the specific
   thresholds your custom alerting logic used today as `TestSuite`
   assertions instead, so the "is this bad enough to page someone" decision
   lives in one declarative place.
5. **Trend + alerting (still your job either way):** append each run's
   headline numbers to your own history table and wire alerting off of it —
   this part of your existing infrastructure doesn't change, Evidently just
   becomes what computes the numbers you're appending, instead of your
   custom comparison function.

The runnable version of steps 3–4 (minus the ground-truth join, since it
uses synthetic labels already present) is in
[`projects/evidently-monitoring-demo/evidently_xgboost_monitoring.ipynb`](../../../projects/evidently-monitoring-demo/evidently_xgboost_monitoring.ipynb);
the same structure with real Delta tables and a 4-hour schedule is in
[`examples/databricks_xgboost_batch_monitoring.py`](examples/databricks_xgboost_batch_monitoring.py).
For each individual drift type from the taxonomy above, isolated and
demonstrated on its own,
[`projects/evidently-monitoring-demo/drift_types_with_evidently.ipynb`](../../../projects/evidently-monitoring-demo/drift_types_with_evidently.ipynb)
builds a minimal example per type — including a deliberate demonstration
of concept drift going completely undetected by covariate-only monitoring
while model accuracy collapses. Verified with real numbers, not just
asserted: `DataDriftPreset` stays completely quiet (0 drifted columns)
while accuracy drops from 0.997 to 0.497 — the sharpest illustration of
why step 3 alone isn't sufficient.

The same data-drift-vs-concept-drift pair, turned into a reusable batch
pipeline (persisted model + reference data, separate train/predict/
generate-drift/monitor stages you can run independently later, not one
notebook run top to bottom) instead of a one-off demonstration:
[`projects/batch-drift-detection-xgboost/`](../../../projects/batch-drift-detection-xgboost/).
Same real-number result, reproduced by that project's own code: 0 drifted
columns while accuracy collapses from 1.000 to 0.487.
