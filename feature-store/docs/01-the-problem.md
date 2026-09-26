# 1. The problem a feature store solves

A feature store solves no *modeling* problem. Your model is exactly as good with
or without one. It solves **data-plumbing problems that appear once a model
leaves the notebook**, and it only earns its keep when those problems actually
hurt. This page is the case for each one — with a runnable demo — so you can
judge for yourself.

## The setup: what "a feature" is, and why it's harder than it looks

A **feature** is a number (or category, or vector) derived from raw data that a
model consumes: `avg_amount_30d`, `tickets_7d`, `days_since_last_login`.

A model needs that feature in **two places at two different times**:

| | Training | Serving (inference) |
|---|---|---|
| Question | "What was `avg_amount_30d` for customer 42 **on Feb 3**?" (for millions of historical rows) | "What is `avg_amount_30d` for customer 42 **right now**?" (one row) |
| Access pattern | Huge scan / join, minutes-to-hours is fine | Single-key lookup, single-digit milliseconds |
| Typical tech | Spark / SQL / pandas over a warehouse or data lake | A service reading a low-latency DB |

Same feature, two access patterns, two technology stacks. Everything below
follows from that split.

```
WITHOUT a feature store                       WITH a feature store

 raw data                                      raw data
   │        │                                    │
   ▼        ▼                                    ▼
 batch     service code            ┌──── ONE feature definition ────┐
 SQL/Spark (re-implemented)        │                                │
   │        │                      ▼                                ▼
   ▼        ▼                 offline store                    online store
 training   prediction        (full history,                   (latest value,
 set        request            time-travel)                     key-value)
   │        │                      │                                │
   ▼        ▼                      ▼                                ▼
 model  ≠?  model                training set  ◄── same values ──► prediction
```

## Problem 1 — Training/serving skew

Two implementations of "the same" feature drift apart. Not because anyone is
careless: the training pipeline is Spark over a lake, the serving path is a
Python service that can only afford a `LIMIT 30` query, and both were written
from a one-line description.

**Demo:** [`demos/01_training_serving_skew.py`](../demos/01_training_serving_skew.py)
compares "avg amount, last 30 days" as computed by a batch job (30 *days*,
refunds excluded) and by a serving-side re-implementation (last 30
*transactions*, refunds included):

```
differ by > 10%:                        79%
decision flips at the same threshold:   40%
```

Nothing crashes, no test fails, latency is great. The model receives inputs in
production it never saw in training, and accuracy silently erodes. Skew bugs
are found weeks later by someone asking "why did conversion drop?".

**What fixes it:** one feature definition, executed once, whose output feeds
*both* the offline and online stores. Not "be careful" — structurally
impossible to diverge.

## Problem 2 — Point-in-time correctness (label leakage)

To train, you attach features to labeled events. The subtle question is *which
value of the feature* you attach. It must be the value **that was knowable at
the event's timestamp** — not today's value, not a later snapshot.

Joining labels to a plain "current state" table silently uses future
information. **Demo:** [`demos/02_point_in_time_leakage.py`](../demos/02_point_in_time_leakage.py)
predicts churn from weekly support-ticket counts:

```
naive join (latest value):    AUC 0.979    ← looks phenomenal
point-in-time (as-of) join:   AUC 0.621    ← the honest number
```

The naive model "predicts" churn using the ticket flood that happens *after*
customers cancel. It's a bug you cannot see in the code — the join runs fine
and the metric looks great. You discover it in production, when the model is
mediocre.

The correct operation is an **as-of (point-in-time) join**: for each
`(entity, timestamp)` row, take the most recent feature value with
`feature_ts <= timestamp`. In pandas that's `merge_asof`. At scale, over many
feature tables, with TTLs and late-arriving data, it is fiddly and easy to get
subtly wrong — which is why every feature store makes it a first-class
operation.

## Problem 3 — Duplication and reuse

Team A builds `customer_lifetime_value`. Team B needs it, doesn't know A's
exists (or doesn't trust it), builds `clv_v2` with a different window. Now the
company has two definitions of CLV, two pipelines to maintain, and two numbers
in two dashboards. A **registry** (name, owner, description, source, schema,
lineage) makes features discoverable and shared.

This is real, but it's an *organizational* benefit that scales with the number
of models and teams. With one model and one team it's worth approximately
nothing. (See [page 2](02-do-you-need-one.md).)

## Problem 4 — Serving latency and the "feature pipeline you didn't want to write"

At request time you can't run the 30-day aggregation over the warehouse; you
need it precomputed and in a fast key-value store. Someone must build and
operate: the batch/stream job that computes it, the sync into the online DB,
the schema, the backfill, the freshness monitoring. A feature store is
largely a *packaged, opinionated version of that plumbing* (called
**materialization**).

If your model scores in batch (nightly, in the warehouse), this problem
doesn't exist for you.

## The summary you can hold in your head

| Problem | Symptom | Only matters when |
|---|---|---|
| Skew | Prod accuracy ≪ offline accuracy, no errors | Features are computed by different code in training vs serving |
| Leakage | Great offline metric, poor prod | Features change over time and you join by entity only |
| Duplication | Two "CLV" columns, nobody sure which is right | Multiple models/teams |
| Serving plumbing | Re-implementing aggregation in the request path | Real-time (online) inference |

Next: [Do you actually need one? →](02-do-you-need-one.md) (spoiler: often not.)
