# Calculus for Engineers: Rate of Change and Accumulation, Applied

This is not a math course. It's the two ideas underneath calculus, stripped of textbook
scaffolding, mapped directly onto things you already look at every day as a platform/MLOps
engineer: dashboards, alerts, model training, cost, SLAs. If you remember nothing else,
remember this pairing — everything below is a variation on it:

- **Differentiation asks: "how fast is this changing, right now?"** — a rate, a slope, a
  sensitivity.
- **Integration asks: "how much of this has accumulated, in total, over some stretch?"** —
  a sum, an area, a total.

They're inverses of each other. That single fact (the Fundamental Theorem of Calculus,
covered at the end) is why a Prometheus **counter** and its **rate** are two views of the
same data, and it's the most useful thing in this entire doc to actually internalize.

## Differentiation: rate of change

### The mental model

Forget `lim_{h→0}`. The derivative of a function at a point is just: **if I nudge the
input a tiny bit, how much does the output move, and in which direction?** That's it. A
derivative of `+3` means "a small increase in input produces roughly 3x that increase in
output, right here." A derivative of `0` means "right now, this output isn't moving no
matter what you do to the input" — you're at a flat spot (often a min, max, or saddle).

Formally: `f'(x) = lim_{h→0} [f(x+h) - f(x)] / h`. That's a slope — `(change in output) /
(change in input)` — evaluated over an infinitesimally small step so it captures the
*instantaneous* rate instead of an average over some coarse interval. Everything else
about differentiation is a set of shortcuts (power rule, product rule, chain rule) for
computing that slope symbolically instead of numerically. You will almost never do that by
hand in engineering work — software computes it for you — so what actually matters is
**recognizing when a question is a derivative question**, and reading the answer
correctly.

### Where you already use this, whether you name it or not

**1. Monitoring — `rate()` in PromQL is a derivative, computed numerically.**
Prometheus counters (`http_requests_total`, `errors_total`) only ever go up. On their own
they're nearly useless for alerting — "12,847,003 total errors" tells you nothing about
whether things are currently on fire. `rate(errors_total[5m])` estimates the derivative:
`(counter_now - counter_5min_ago) / 300s`, i.e. errors per second, right now. That's
exactly the `[f(x+h) - f(x)] / h` formula above with `h = 5 minutes` instead of an
infinitesimal step — a **finite-difference approximation** of a derivative, which is what
almost all real-world "differentiation" actually is once you leave a math class. See
[Prometheus](tools/prometheus/README.md) for the counter/gauge/histogram mechanics this
sits on top of.

The engineering payoff: alert on the *derivative*, not just the raw value, when what you
actually care about is "is this getting worse" rather than "is this currently high."
A slowly climbing memory usage and a memory usage that just jumped 40% in one minute can
have the same current value but very different derivatives — and very different urgency.

**2. Gradient descent — the derivative *is* the training algorithm.**
Every model in this repo that isn't a lookup table (linear/logistic regression, XGBoost,
neural nets) is fit by computing the derivative (gradient) of a loss function with respect
to each parameter, then nudging the parameter against that gradient — literally "which way
is loss increasing fastest, now go the other way, a little." This repo already has a
from-scratch, verified walkthrough of the mechanism, learning-rate failure modes, and
batch/SGD/mini-batch/Adam variants — see [`ml-fundamentals-deep-dive.md`
§"Gradient descent"](tools/scikit-learn/ml-fundamentals-deep-dive.md#gradient-descent-how-a-model-actually-learns-its-parameters);
this doc won't re-derive it. The one-sentence bridge: `grad_w`/`grad_b` in that walkthrough
are literally `∂loss/∂w` and `∂loss/∂b` — partial derivatives, the multi-input version of
the single-variable derivative above (hold every other parameter fixed, ask how loss moves
if you nudge just this one).

**3. Chain rule — how a change propagates through a pipeline.**
The chain rule (`d/dx f(g(x)) = f'(g(x)) · g'(x)`) says: if A feeds into B feeds into C,
the sensitivity of C to a change in A is the *product* of each stage's local sensitivity.
This is exactly **backpropagation** in a neural net (each layer's gradient is the next
layer's gradient times its own local derivative, chained backward through the network) —
but the same shape of reasoning applies to any multi-stage system: if upstream feature
drift shifts an input by X%, and each downstream transform amplifies or dampens that shift
by some local factor, the end-to-end sensitivity is the product of those factors, not a
guess. Useful for reasoning about blast radius in a pipeline (Feast feature transform →
model input → prediction) without having to trace every intermediate value by hand.

**4. Sensitivity / feature importance — a derivative you already compute.**
"How much does the model's output change if I nudge this one feature?" is literally a
partial derivative of model output with respect to that feature. SHAP values (already
covered in [`xgboost/README.md` §"Feature importance and
SHAP"](tools/xgboost/README.md#feature-importance-and-shap)) are a more principled,
game-theoretic version of this same question, but the intuition is identical: derivative
= local sensitivity of output to one input, everything else held fixed.

**5. Control loops and autoscalers — the derivative term stops overshoot.**
A classic PID controller has three terms: **P**roportional (react to current error),
**I**ntegral (react to accumulated past error — see below), **D**erivative (react to how
fast the error is currently changing). The D term exists specifically to dampen — if error
is shrinking fast, ease off the correction even though error is still nonzero, so the
system doesn't overshoot and oscillate. This is the same failure mode as a learning rate
set too high in gradient descent (both diverge/oscillate for the same underlying reason:
reacting to a signal without accounting for its rate of change causes overcorrection) — an
autoscaler that only looks at "CPU is at 85% right now" and not "CPU has been climbing 10
points/minute" will consistently scale too late and then overshoot.

### The heuristic

**When you find yourself asking "is X getting better/worse," "how sensitive is Y to Z," or
"how fast is this moving" — that's a derivative question, whether or not the tool you use
to answer it (`rate()`, `.diff()`, `np.gradient`, a trained model's gradient) ever says the
word "calculus."**

## Integration: accumulation

### The mental model

The integral of a function over some interval is the **total accumulated amount**,
computed by imagining you chop the interval into a huge number of tiny slices, multiply
the function's value in each slice by the slice's (tiny) width, and add all those products
up. That sum-of-tiny-rectangles is called a **Riemann sum**, and the integral is what that
sum converges to as the slices get infinitesimally thin. Geometrically, that's "the area
under the curve." Practically, it's "rate × time, added up across every moment, even when
the rate isn't constant."

Crucially: **almost every integral an engineer actually computes is a Riemann sum, full
stop** — not a symbolic antiderivative. Your monitoring system doesn't have a closed-form
formula for your error rate over time; it has samples, every 15 or 60 seconds, and it sums
`value × interval_width` across them. That's not an approximation you settle for because
calculus is hard — that's the actual computation, and knowing that demystifies most of
what "integration" means in production systems.

### Where you already use this

**1. Monitoring — `increase()` / `sum_over_time()` are integrals of a rate.**
Where `rate()` differentiates a counter, `increase(errors_total[1h])` does the reverse: it
estimates the *total number of errors accumulated* over the last hour by summing up the
rate across that window — an integral, computed as a Riemann sum over however many scrape
samples fell in that hour. "How many errors happened during the incident" is an
integration question; "is the error rate climbing" is a differentiation question about the
exact same underlying counter. Same metric, two different questions, two different
operators.

**2. AUC-ROC / PR-AUC — literally, by name, an area under a curve.**
This repo's fraud-detection pipeline evaluates every model with exactly this metric —
[`evaluate.py`](../projects/fraud-detection-xgboost/src/fraud_detection/evaluate.py)
computes both:

```python
"pr_auc": average_precision_score(y_test, y_pred_proba),
"roc_auc": roc_auc_score(y_test, y_pred_proba),
```

Both metrics work by sweeping the classification threshold from 0 to 1, computing a
(precision, recall) or (true-positive-rate, false-positive-rate) point at each threshold,
tracing out a curve, and then **integrating under that curve** — literally a Riemann sum
over discrete threshold steps, same mechanism as `increase()` above, just over a threshold
axis instead of a time axis. "AUC" is not a metaphor; it's the actual operation. See
[`xgboost/README.md` §"Why PR-AUC, not accuracy, on imbalanced
data"](tools/xgboost/README.md#why-pr-auc-not-accuracy-on-imbalanced-data) for why this
particular integral is the right metric to optimize on this repo's ~0.17%-positive-rate
data.

**3. Cost and billing — cost is the integral of a rate.**
Cloud cost is (almost) never a flat number you look up — it's `$/hour × hours run`,
accumulated across every resource, every hour, over a billing period. A GPU that costs
`$4/hr` and ran for a fluctuating number of hours across a month has a total cost equal to
the integral of "GPU-hours running" over the month — which is exactly what a cost-explorer
dashboard is computing when it draws a cumulative-spend line, and exactly what
`sum_over_time()` or a running `.cumsum()` over per-hour spend gives you if you're building
that dashboard yourself.

**4. SLA / error-budget burn — the integral *and* its derivative, together.**
An SLO error budget (e.g. "we're allowed 43 minutes of downtime this month") is consumed by
**accumulating** bad events over time — that's an integral: total badness so far. A "burn
rate" alert (a standard SRE pattern: page if the budget will be exhausted in under N hours
at the *current* rate) is the **derivative** of that same accumulation — how fast the
budget is being consumed right now. This is the single cleanest real-world example of
derivative and integral used *together*, deliberately, in one alerting strategy: the
integral tells you how much budget is gone, the derivative tells you how urgently you
should care about how fast it's still going.

### The heuristic

**When you find yourself asking "how much total X happened," "what's the cumulative Y," or
"how much of the budget/cost/error-allowance is used up" — that's an integration question,
whether the tool is `increase()`, `.cumsum()`, `np.trapz`, or an AUC metric.**

## The Fundamental Theorem of Calculus, in engineer terms

The FTC says differentiation and integration are inverse operations: if you integrate a
rate, you get the total; if you differentiate a total, you get back the rate. This isn't
an abstract symmetry — it's a pairing you interact with constantly:

| Accumulated / "integral" view | Rate / "derivative" view | Where you've seen this |
|---|---|---|
| Prometheus **counter** (`errors_total`) | Prometheus **rate()** of that counter | Monitoring |
| Cumulative cost-to-date | `$/hour` burn rate | Billing dashboards |
| Total error-budget consumed | Burn-rate alert | SRE / SLOs |
| `pandas.Series.cumsum()` | `pandas.Series.diff()` | Any time-series dataframe |
| Position | Velocity | Physics, but also: total requests served vs. requests/sec |
| Model's total loss over an epoch | Per-parameter gradient at a step | Training |

The one caveat worth knowing, because it's the thing that actually bites people in
practice: this clean inverse relationship assumes a **continuous, well-behaved** function.
Real counters aren't — they **reset** (a process restarts, the counter goes back to 0).
`rate()` in Prometheus has special-cased logic to detect a counter reset (a value that
drops instead of rising) and correct for it rather than reporting a nonsensical huge
negative rate. That's the practical, production version of the same edge case a first
calculus course handles by requiring functions to be "continuous and differentiable" before
the theorem applies cleanly — discontinuities break the theory, and in your systems, a
pod restart is a discontinuity.

## The actual day-to-day trigger list

You will essentially never hand-derive a symbolic derivative or integral in this work. What
you need is the reflex to recognize which question you're being asked, so you reach for the
right tool:

| You're asking... | That's... | Reach for |
|---|---|---|
| "Is this getting worse, and how fast?" | Derivative | `rate()`, `irate()`, `.diff()`, `np.gradient` |
| "How sensitive is the output to this input?" | Partial derivative | Gradients, SHAP, `.feature_importances_` |
| "How much total X happened in this window?" | Integral | `increase()`, `sum_over_time()`, `.cumsum()` |
| "What's the total cost / downtime / error count?" | Integral | Cost-explorer cumulative views, error-budget math |
| "How good is this classifier across all thresholds, not just one?" | Integral (area under a curve) | `roc_auc_score`, `average_precision_score` |
| "How should a model's parameters update to reduce loss?" | Derivative (gradient) | `.backward()` / autograd, or the from-scratch version in [`ml-fundamentals-deep-dive.md`](tools/scikit-learn/ml-fundamentals-deep-dive.md) |
| "Will this control loop overshoot?" | Derivative term missing/misweighted | PID tuning, autoscaler cooldown/stabilization windows |

If a metric, alert, or design question feels like it's really about "is this moving too
fast" or "how much has piled up," it *is* a calculus question — you're just answering it
numerically, from samples, with a library function, instead of symbolically with a pencil.
That reframe is the actual point of this doc.
