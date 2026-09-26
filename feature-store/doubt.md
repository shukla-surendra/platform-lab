# Doubts — feature store Q&A

A running log. Add a question under a new `## Qn`, and the answer goes right
below it. Answers point to the docs/demos where the idea is shown in code.

Format: **Short answer** first, then the reasoning, then "still unsure if…"
for follow-ups worth asking next.

---

## Q1. Is a feature store only created to avoid recalculating features for training?

**Short answer: No.** Avoiding recomputation is a real benefit, but it's the
*smallest* of the reasons, and on its own it wouldn't justify the system. If
that were the only goal, a cached table would do.

### Where "avoid recalculation" is true
Compute a feature once (say a 90-day aggregate over billions of rows), store it,
and every training run, experiment and model reuses it instead of re-running the
expensive job. That is genuine savings when:

- the computation is expensive, and
- several models/experiments/teams want the same feature.

For one model retrained monthly on a cheap query, this saves you nearly nothing.
That's one reason a feature store feels unnecessary in small projects.

### Why "just cache it" is not enough
A plain cache or materialized table stores **the value**. Training needs
something a cache doesn't give you:

| What's needed | Plain cache / table | Feature store |
|---|---|---|
| Value **as it was at each past timestamp** (history, not just latest) | ✗ usually holds only the latest value | ✓ offline store keeps full time-versioned history |
| Attach the right historical value to each label without leaking the future | ✗ you write the join, easy to get wrong | ✓ point-in-time (as-of) join is the core read |
| Identical values for **training and live prediction** | ✗ serving still re-implements the logic | ✓ one definition feeds both stores |
| Millisecond lookup by key at request time | ✗ | ✓ online store |
| Know what exists, who owns it, which models use it | ✗ | ✓ registry |

So the real value isn't "compute less"; it's **"compute once, correctly, and
serve the same values to training and serving."**

### The three things it does that recalculation-avoidance doesn't
1. **Consistency (skew).** Same feature, same code, same numbers in training and
   production → [demo 1](demos/01_training_serving_skew.py): two "identical"
   implementations disagreed for 79% of customers and flipped 40% of decisions.
2. **Time correctness (leakage).** Training rows get the value that was true *at
   that time* → [demo 2](demos/02_point_in_time_leakage.py): AUC 0.98 with the
   leaky join vs 0.62 honest.
3. **Online serving.** A precomputed latest-value key-value store, kept in sync
   with the history → [demo 3](demos/03_mini_feature_store.py).

### A way to remember it
> Recalculation-avoidance saves **compute cost**.
> Feature stores exist to prevent **wrong models**.

Compute savings are a nice side effect of "compute once, use in both places".
The reason big teams adopt one is that skew and leakage bugs are silent and
expensive, not that the Spark bill was high.

### Where this answer is weakest / honest caveats
- If you have **one batch-scored model**, recalculation savings and everything
  else on the list are small, so "not needed" is a valid conclusion
  ([docs/02](docs/02-do-you-need-one.md)).
- The "compute once" guarantee only holds if the store's users actually feed it
  from one pipeline. Feast and SageMaker FS only *store* features; they don't
  force you to compute them once ([docs/03](docs/03-core-concepts.md#the-single-most-important-principle-transform-once)).

### Follow-ups worth asking next
- If the offline store keeps every historical value, isn't that a lot of storage? (yes — see the cost discussion in [docs/02](docs/02-do-you-need-one.md))
- Why not just recompute features from raw data at every training run with a correct as-of query?
- Who computes the feature in SageMaker/Databricks — the store or me?

---

## Q2. I built features for one model from 10 tables, and they're useful only for that model, not for any other. Do I still need a feature store?

**Short answer: not necessarily — but "not reusable" only removes one of the
reasons. The other reasons depend on *how the model is served*, and ten source
tables actually makes two of them worse.**

### What "only useful for my model" does and doesn't remove
From [Q1](#q1-is-a-feature-store-only-created-to-avoid-recalculating-features-for-training)
and [docs/01](docs/01-the-problem.md), a feature store addresses four problems:

| Problem | Removed by "only my model uses it"? |
|---|---|
| Duplication / discoverability across teams | **Yes** — nobody else is consuming it. |
| Skew (train code ≠ serving code) | **No** — one model still has a training path and a serving path. |
| Point-in-time leakage | **No** — and see below, it gets *riskier* with 10 tables. |
| Online serving plumbing | **No** — depends on whether you serve online. |

So you lose the *sharing* argument, which is the weakest one anyway. The
decision now hangs on the other three.

### Why ten tables raises the stakes
Every source table has its **own notion of time**: an orders table with
`created_at`, a profile table that is overwritten in place, a payments table
with `settled_at`, a table with only a load date. To build a correct training
set you need each feature *as of the label's timestamp*, which means ten
as-of joins, each with its own timestamp semantics. One "current state" table
in the mix (like the profile table that only holds today's value) leaks the
future, and it is invisible in code review ([demo 2](demos/02_point_in_time_leakage.py):
AUC 0.98 vs 0.62).

At serving time it's worse: a live request can't query ten tables, so
somebody must precompute the features into a fast store and keep it in sync —
and re-implement the logic there if it isn't shared ([demo 1](demos/01_training_serving_skew.py)).

### The decision, by how the model runs

| How the model scores | What you need | Feature store? |
|---|---|---|
| **Batch** (nightly/hourly, same pipeline that trains it) | One feature pipeline that outputs a **timestamped wide table**, used for both training (as-of join) and scoring | **No** |
| **Online**, but all inputs come in the request | Nothing to look up | **No** |
| **Online**, needs aggregates from those 10 tables | Precompute → key-value store → same logic in training | You need the *pattern* (compute once, write to offline + online). A managed feature store is one way; a job that writes the same output to a warehouse table and Redis/DynamoDB is another. |
| Several models will *later* share parts of it | Registry + shared definitions | Reconsider then, not now. |

### What to do for a single model (recommended default)
1. **Write the feature logic once** — one function/SQL/dbt model — and have training
   and scoring both call it. That alone kills skew.
2. **Output one table keyed by entity + event timestamp** (the "feature table"). Make
   the as-of join a small tested helper. That handles leakage.
3. **Have a test for it:** assert no feature timestamp is later than its label
   timestamp (demo 3 does this: `rows with a feature from the future: 0`).
4. **Only if you serve online**, add a job that writes the latest row per entity to a
   key-value store, and, if scale/governance justifies it, use a managed store for
   steps 2–4.

This is "a feature store without the product": the same architecture as
[`demos/mini_feature_store.py`](demos/mini_feature_store.py), minus a system
to operate.

### A caution about model-specific features inside a shared store
If you *do* adopt a feature store later, don't dump every model-specific feature
into the shared registry. Registered features carry a maintenance promise
(owner, schema stability, backfills). Common practice: put stable,
broadly useful entity features (customer activity, merchant risk) in the store;
keep one-off, model-specific transformations in the model's own pipeline
code — still written once and shared between training and serving.

### Where this answer is weakest
- If the model is online and latency-critical, the "no product" route means you
  build and operate the sync, freshness monitoring and backfills yourself;
  a managed store may be cheaper in total effort than that.
- "Only my model uses it" is often true on day one and false in a year. If you
  expect a second model soon, define the features cleanly now (entity +
  timestamp + owner) so migrating is cheap.

### Follow-ups worth asking next
- How do I detect leakage in an existing 10-table pipeline?
- What does the online sync job look like without a feature store product?
- When *is* a feature "shared enough" to belong in the registry?

---

## Q3. What does sklearn's `ColumnTransformer` do, and can it be used with a feature store?

**Short answer:** `ColumnTransformer` applies *different* preprocessing to *different columns* in one
object (one-hot the categoricals, scale the numerics, pass the rest through). It is a **model-side**
component, so it normally lives *next to the model*, not inside the feature store — though the two
work together: the store supplies **raw** features, the fitted `ColumnTransformer` turns them into
model inputs.

### What it does
```python
ct = ColumnTransformer([
    ("ohe",   OneHotEncoder(handle_unknown="ignore"), ["channel"]),
    ("ord",   OrdinalEncoder(...),                    ["merchant"]),
    ("scale", StandardScaler(),                       ["amount"]),
    ("keep",  "passthrough",                          ["txn_count_30d"]),
])
ct.fit(train_df)          # LEARN state from training data
ct.transform(any_df)      # APPLY that state; same output columns every time
```
Run [`demos/04_column_transformer_boundary.py`](demos/04_column_transformer_boundary.py) to see it.
The important word is **fit**: after `fit`, the object holds *learned state* — category lists,
means/standard deviations, category→integer maps. `transform` then reuses that state and never
re-learns it.

### The rule that decides where a transformation lives

| | Stateless | Stateful (learned from training data) |
|---|---|---|
| Depends on | only the row | the training set |
| Examples | `log(amount)`, `amount / avg_30d`, fixed buckets, date parts | one-hot / ordinal / frequency encoding, scaling, mean imputation |
| Belongs in | **feature definition** (feature store / feature pipeline) — compute once, share | **the model bundle** (`Pipeline([ColumnTransformer, model])`), versioned with the model |
| Why | same result for every consumer | different training windows give different results (demo: same raw row → different inputs) |

So a `ColumnTransformer` can't be *the* feature definition, because its output depends on which
training data it was fitted on. Storing its *encoded output* as a shared feature would silently tie
every consumer to one model's training window.

### How they fit together
```
raw data ─► feature pipeline ─► FEATURE STORE (raw, shareable features)
                                        │  point-in-time join / online lookup
                                        ▼
                        ┌──── model bundle (one versioned unit) ────┐
                        │  ColumnTransformer (fitted)  →  model     │
                        └───────────────────────────────────────────┘
```
- **Training:** read raw features from the store → `fit` the `ColumnTransformer` on the *training*
  rows only → train → save transformer **and** model together (e.g. one sklearn `Pipeline`, or both
  artifacts under one MLflow model).
- **Serving:** read raw features → the *saved* transformer's `transform` (never `fit`) → model.

### Product notes (verify against current docs)
- **Databricks / SageMaker / Feast** store features; they don't own fitted preprocessing. Keep the
  transformer in the model artifact (an sklearn `Pipeline` containing the `ColumnTransformer` is the
  usual approach; Databricks packages feature lookups with the logged model).
- Some platforms (e.g. Hopsworks) have first-class "model-dependent transformations" that record
  training statistics for you; Feast's on-demand feature views are for *stateless* request-time
  transforms.

### Pitfalls this creates (all skew-shaped)
- Transformer and model saved separately → wrong pair loaded at serving.
- `fit` accidentally run on scoring data (or on train+test) → leakage or drifting codes.
- Unseen categories: `OneHotEncoder(handle_unknown="ignore")` gives all-zeros; `OrdinalEncoder(unknown_value=-1)` gives `-1`.
  Decide deliberately, and test it.
- Encoded columns saved back into the shared store → not reusable, and stale after retraining.

### Follow-ups worth asking next
- Should the transformer be a `Pipeline` with the model, or a separate artifact?
- How do I test that training and serving produce identical model inputs?
- When is a scaler/encoder better replaced by a tree model's native handling?

---

## Q4. If we use an online feature store, do the created feature rows also get added to the offline store?

**Short answer: they should, but only if the write path puts them there.** The rule to hold onto:

> **Offline is the system of record (every value, with its timestamp). Online is a serving copy (latest value only).**
> A feature row that reaches only the online store is invisible to training.

### The three write paths

```
PATH 1  batch → offline → materialize → online        (offline written FIRST; online is derived)
        pipeline ──► OFFLINE (history) ──copy latest──► ONLINE (latest)

PATH 2  streaming / push → BOTH                       (dual write; online overwritten, offline appended)
        event ──► compute ──┬──► ONLINE  (overwrite latest)
                            └──► OFFLINE (append new version)

PATH 3  streaming / push → ONLINE ONLY                (the trap)
        event ──► compute ────► ONLINE   ✗ never recorded offline
```

Run [`demos/05_online_offline_writes.py`](demos/05_online_offline_writes.py) (uses the mini store's new `push()`):

| Path | Online value | Can training reproduce it? |
|---|---|---|
| 1 batch + materialize | latest offline row | Yes — it *is* an offline row |
| 2 push to both | `200.0` (latest only) | Yes — offline as-of t1 returns `100.0`, as-of t2 returns `200.0`; history kept |
| 3 push online-only | `100.0` served | **No** — a training set gets `40.99` (the old batch value); the pushed value never existed offline |

Path 3 is silent training/serving skew *created by the write path*. Nothing errors, and once the online
value is overwritten, what the model saw is gone permanently.

### Two facts that follow
- **Online keeps one value per entity** (each write overwrites). **Offline keeps every version.** So "the rows are in both"
  never means "both stores hold the same amount": offline is the full history, online is its latest slice.
- **Offline being written is not the same as offline being *fresh*.** Streaming features may reach online in
  milliseconds and offline minutes or hours later (batched file writes). Training only sees what has landed offline.

### How real products map (verify against current docs)
| Product | Behaviour |
|---|---|
| Feast | Batch: offline source is the truth; `materialize` copies the latest to online (Path 1). Push/streaming ingestion can write online, offline, or both — you choose. |
| SageMaker Feature Store | One `PutRecord` call updates the online store and (if the feature group has an offline store) appends to the offline store (Path 2). Online-only or offline-only groups are also possible. |
| Databricks | The offline Delta table is the source; online tables are synced *from* it (Path 1). |

### Rules of thumb
- Prefer **Path 1 or 2**; treat online-only writes as a bug unless you deliberately log the served features somewhere else.
- If a feature is only ever computed at request time and never stored, record what was served (a **feature log**) so training can replay it.
- Test it: for a sample of entities, the online value at time *t* must equal the offline as-of value at *t* (demo 3 does this for the batch path).

### Follow-ups worth asking next
- Streaming features: how do the online and offline paths stay identical when they're computed separately?
- What's the lag between an online write and it appearing offline, and does training care?
- Feature logging vs. recomputation for reproducing what a model saw.

---

## Q5. The online store won't have the "actuals" at serving time. How do values sync when the actuals arrive?

*(Reading "actuals" as ground-truth outcomes / labels that are confirmed days or weeks after the prediction. The last
section covers the other reading: late-arriving source data.)*

**Short answer: they don't sync into the online store.** Labels never live there. Serving writes a **log**; actuals are joined to
that log later, **offline**. The only place actuals reach the online store is indirectly, through
**features built from past outcomes** — and those need care.

### 1. The label path (offline, delayed)
```
request ──► online features ──► model ──► prediction
                │                            │
                └──────────► SERVING LOG ◄───┘   (entity, event_id, timestamp,
                                  │                features served, prediction, model version)
   ... days/weeks later ...       │
   actuals (outcome, outcome_ts) ─┴──► JOIN on event_id ──► labelled rows ──► training / evaluation / monitoring
```
Nothing is "synced": it's a batch join keyed by an id. Demo 6 shows the consequence — labels mature slowly:

```
events aged   0-15  days:  13% labelled
events aged  15-30  days:  50% labelled
events aged  30-60  days:  89% labelled
events aged  60+    days: 100% labelled
```
so the most recent data can't be trained on yet. Log **what was served**, because it is the only faithful record of the inputs.

### 2. The one place actuals DO reach features: label-derived features
Some features are computed *from* past outcomes ("share of this customer's previous cases that were violations").
When new actuals arrive, that feature's true value changes, so the **feature pipeline recomputes it and pushes/materializes it online**
(the same offline→online path as any feature; see Q4).

The trap is timing. At prediction time only *confirmed* outcomes exist. If training builds the feature from **today's**
outcomes, it sees a more mature history than production ever will. In demo 6:

```
training value differs from served value:   48% of events
avg prior cases counted, served / naive:    5.8 / 7.0
```
The fix is to compute the training value from outcomes **known at event time** (`outcome_ts <= event_ts`). An independently
written training-side computation then matches the served value for 100% of events. This needs the source to record **when each
outcome became known**. A feature store can't invent that history; it only makes the as-of join easy once it exists.

### 3. Related situations
| Situation | What to do |
|---|---|
| New entity, no value yet | Online lookup returns nothing/`None`; the model needs a default or missing-value path. TTL does the same for stale values. |
| Late-arriving *source data* (an old transaction shows up, a value is corrected) | Recompute and write **offline** with the correct event time (backfill), then re-materialize / re-push online. Online keeps latest-event-time-wins, so an older late row must not overwrite a newer value (`push()` in the mini store does this). |
| "What did we know when we trained model v3?" | Keep an **ingestion time** next to event time (bitemporal), or a feature log. Event time alone can't reproduce past knowledge after a correction. |
| Model evaluation / drift | Join the serving log to actuals as they mature; report metrics by label age, not just overall. |

### Follow-ups worth asking next
- Where should the serving log live, and how much does logging every request cost?
- How do I handle delayed labels in training-window and holdout design?
- Bitemporal features: event time vs. ingestion time in practice.

---

## Q6. ML data has two things, features and labels. Are both present in an offline feature store?

**Short answer: features always; labels usually not.** By convention the feature store holds **features** (with timestamps),
and **labels live in a separate table** that you join to the features when you build a training set. Some products let you
store a label column too, but that's a convenience, not the norm.

### The picture
```
FEATURE STORE (offline)                    LABEL / EVENTS TABLE (yours)
entity  feature_ts   avg_amount_30d ...    entity  event_ts   label
7       Mar 01       40                    7       Mar 10     1      ← "what happened" for this event
7       Mar 08       52   ◄── as-of ──     7       Mar 10     1
7       Mar 12       80                                            
                       └──────── training set = labels ⟕ features as of event_ts ────────┘
```
Demo 3 already does exactly this: `labels` is a DataFrame of `(customer_id, event_ts, label)`, and
`store.get_historical_features(labels, FEATS)` attaches the as-of features. The store never sees the label.

### Why labels are kept out
| Reason | Detail |
|---|---|
| **Different timeline** | A feature has an *event time* (when it was true). A label has an *outcome time* (when it became known, often weeks later — see [Q5](#q5-the-online-store-wont-have-the-actuals-at-serving-time-how-do-values-sync-when-the-actuals-arrive)). Mixing them in one row hides which is which. |
| **Different lifecycle** | Features are recomputed on a schedule; labels arrive late and can be revised (a case reopened, a chargeback). |
| **Reuse** | The same features feed several models with **different labels** (fraud, churn, LTV). One table can't hold all of them cleanly. |
| **Serving** | Labels don't exist at prediction time and must never be served online. Keeping them out of the store makes accidental leakage harder. |
| **Ownership** | The label defines *the model's problem*; features are shared assets. |

The training set is therefore built from **(entity, event_ts, label)** as the spine and features joined onto it by point-in-time join.
The spine is called the *entity dataframe* in Feast, the *training DataFrame with a label column* in Databricks, and the *base
dataframe* when building a dataset in SageMaker.

### When a label does live alongside features (and its costs)
- **A labelled training-snapshot table** — features + `TARGET` in one denormalised table, one per model. Common, simple and fine for a single model.
  Costs: not reusable across models, and the label must be kept fresh as outcomes mature (an upsert that misses late/revised outcomes leaves stale labels).
- **A label as its own feature group** (e.g. Hopsworks lets you declare label columns in a feature view; SageMaker can hold a label column in a feature group).
  Fine when the label is stable and shared, *as long as it has its own timestamps and is never materialized to the online store.*
- **Label-derived features** — past outcomes aggregated into features (Q5) *are* legitimate features, but must be computed from outcomes known at event time.

### Rules of thumb
1. Store **features** in the feature store; keep **labels** in a separate labelled-events table (or a view over your outcomes).
2. Build training sets as `labels ⟕ features (as-of event_ts)`.
3. Never let the label or anything derived from post-event outcomes reach the online path.
4. Watch label maturity: the newest events aren't labelled yet, so hold out by *outcome-known* date, not event date.

### Follow-ups worth asking next
- How do I design the training-window and holdout when labels arrive weeks late?
- What should the labelled-events table look like (keys, event time, outcome time, label version)?
- When is a denormalised training-snapshot table better than feature store + label join?

---

## Q7. Does a feature store support joins?

**Short answer: yes, but a specific kind.** It joins **feature views onto a table of `(entity keys, event_ts)` rows, point-in-time
correct**. It is *not* a general relational join engine. Joins across your **source tables** happen earlier, inside the feature computation.

### Three different things called "join"

| # | Join | Where it happens | Supported by a feature store? |
|---|---|---|---|
| 1 | **Combining source tables** (transactions ⟕ merchants ⟕ customers …) to *compute* a feature | Feature pipeline (Spark/SQL/dbt) | **No** — this is the job of your transformation code, *before* the store |
| 2 | **Features ⟕ spine** at training time: attach each feature to `(keys, event_ts)` rows with an **as-of** join | Offline store read (`get_historical_features`, `create_training_set`, dataset builder) | **Yes — the core operation** |
| 3 | **Feature view ⟕ feature view** in one request: several views (even for *different entities*) onto one spine | Same read; you list the features you want | **Yes** — provided the spine carries each view's join key |

### What demo 7 shows (two entities, one spine)
[`demos/07_joins.py`](demos/07_joins.py): `customer` stats and `merchant` stats (different entity keys) are joined onto rows that carry both
`customer_id` and `merchant_id`. Each view is joined **on its own key** and **as-of** the event time:
```
customer_id  merchant_id  event_ts   cust__feature_ts  cust_avg_30d  merch__feature_ts  merch_avg_30d
67           13           Feb 10     Feb 10            34.93         Feb 10             40.39
192          0            Feb 11     Feb 07            44.68         Feb 11             39.21   ← each view has its own as-of timestamp
```
Result: 0 values from the future in either view, and an independent recomputation matched for 60 sampled rows.

### What it does NOT do
- **No arbitrary joins.** Only "entity key = key" plus "latest at-or-before event time". No joining feature views on arbitrary columns, no many-to-many, no range joins on non-time columns.
- **No join on the online path.** Online is a key-value lookup: to combine customer and merchant features you do **one lookup per entity** and merge them in the caller
  (demo 7's last block). Each extra entity is another lookup and more latency; keep the number of entities per request small.
- **Multi-hop entity relations aren't resolved for you.** If the request only has `transaction_id`, *you* must first fetch its `customer_id` and `merchant_id`,
  or include them in the request.

### The subtle bit: as-of is inclusive, and the spine row may be the event itself
In demo 7 the spine rows are transactions, so for 175 of 196 rows the customer feature's timestamp **equals** the event time: the feature already
includes the very transaction being scored. If the label depends on that event, use a **strictly-before** join or exclude the event from the feature.
Most stores let you control this (or make you build it into the feature definition); check the default.

### Practical notes (verify against current docs)
| Product | Join surface |
|---|---|
| Feast | `get_historical_features(entity_df, features=[...])` joins any number of feature views; `entity_df` must carry every join key + a timestamp. |
| Databricks | `create_training_set(df, feature_lookups=[FeatureLookup(..., lookup_key=..., timestamp_lookup_key=...)])`; features are Delta tables, so ordinary SQL joins also work. |
| SageMaker | Dataset builder with a base dataframe plus several feature groups, or query the offline store (Athena) and write your own SQL join. |

Because the offline store is usually just tables in a lake/warehouse, you *can* always fall back to plain SQL against it — you give up the
store's guarantees (point-in-time correctness, TTL) when you do.

### Follow-ups worth asking next
- How do I design entity keys when a prediction involves several entities (user + merchant + device)?
- How should the spine handle events that were themselves in the feature window (inclusive vs strictly-before)?
- When is it better to precompute a joined feature ("user × merchant" pair feature) than to join two views at request time?

---

## Q8. What purpose does the separate label table (and the join) serve? Is it just a separate storage for labels?

**Short answer: no — where labels are stored is incidental. The purpose is to keep the *label's timeline* separate from the
*features' timeline*, so each training example can be assembled as "features as they were at prediction time + the outcome
that came later." The join is what puts them back together.**

### The idea in one line
A training example is a statement about **two different moments**:

```
        features known here                 outcome known here
  ────────────────●──────────────────────────────────●────────────►  time
              event_ts (prediction)              outcome_ts (label)
```
The features belong to `event_ts`; the label belongs to `outcome_ts`. If you store them separately, the **join** lets you choose
*which* feature snapshot goes with *which* label, instead of that choice being frozen when the data was written.

### What the separation buys you

| Benefit | Example |
|---|---|
| **One feature table, many label sets** | `customer_stats` feeds a fraud model (label: chargeback within 60 days) and a churn model (label: cancels within 30 days). Each model has its own label table/spine; the features are computed **once**. |
| **Change the question without recomputing features** | New label definition, different prediction horizon, new training cutoff → edit the *spine* and re-join. No feature recomputation. |
| **Labels can be corrected** | A case is reopened or a chargeback reverses → update the label table only. |
| **Right time for each side** | The as-of join uses `event_ts` to pick features, so the future never leaks in (Q1–Q2). |
| **Nothing label-shaped near the online path** | Serving reads features only (Q6). |

### What you lose if labels and features sit in one denormalised table
It's fine for one model, but the choices are baked in at write time: **one label definition, one prediction time per row, features frozen
to the moment the row was built**. Changing any of them means rebuilding the table (recomputing features), and the table can't be reused by a second model.

### So is it "just separate storage"?
Separate storage is a *consequence*, not the goal. What matters is that **features are keyed by (entity, feature time)** and **labels by
(entity, event time, outcome time)**, and a join combines them **as-of** the event. You could keep both in the same database; you still want them as two logical tables.

### Follow-ups worth asking next
- What columns should the label table have (entity, event_ts, outcome_ts, label, label_version)?
- How do I rebuild a training set for a new horizon (e.g. 30 → 60 days) without recomputing features?
- When is a denormalised training-snapshot table the pragmatic choice anyway?

---

## Q9. The computed features may not be enough for several models. Do models read from the feature store and add a few other features of their own?

**Short answer: yes, that is the normal pattern.** The store is the *common layer*, not the model's entire input. A model's input is
assembled from four sources:

```
                     ┌─ shared feature views      (in the store, computed once, many consumers)
model input  =       ├─ its own feature views      (in the store or its own pipeline, one consumer)
                     ├─ on-demand features         (need the live request; computed at request time)
                     └─ fitted preprocessing       (encoders/scalers; ships with the model — Q3)
```

### Demo
[`demos/08_composing_models.py`](demos/08_composing_models.py): one store, two models.

```
model_a: cust_avg_30d, cust_txn_30d, merch_avg_30d                    (all shared)
model_b: cust_avg_30d, night_share_30d, amount_vs_avg                 (1 shared + 1 own view + 1 on-demand)

cust   once   model_a, model_b   (shared)
merch  once   model_a            (single consumer)
night  once   model_b            (single consumer)
```
Each model declares the features it consumes (a *feature service* / training-set spec). Both are served from the same store; only the
extra pieces differ. Serving `model_b` from stored + own + on-demand features matched the offline build: 600 values, 0 mismatches.

### The kinds of "extra" features and where each belongs

| Extra feature | Example | Where it should live |
|---|---|---|
| **Another shared feature** | merchant stats a second model also needs | Shared feature view in the store |
| **Model-specific aggregate** | share of night-time activity, only one model uses it | Its own feature view (own pipeline/namespace/owner) — or the model's pipeline until a second consumer appears |
| **Request-time feature** | `amount / cust_avg_30d` needs the live request amount | **On-demand** transform: one function shared by training and serving |
| **Fitted encoding/scaling** | one-hot merchant, standardised amount | Model bundle (Q3) — never the shared store |
| **Label-derived feature** | prior outcomes of this customer | A view, with the as-known-at-t rule (Q5) |

### How this stays safe (and where it doesn't)
- **On-demand features must share code with training.** In the demo one function (`amount_vs_avg`) is called by both paths. If serving re-implements it,
  you have reintroduced skew (demo 1). Feature stores that support on-demand transforms (e.g. Feast on-demand feature views, Databricks feature functions) exist to enforce this.
- **Only stateless on-demand transforms belong there.** Anything that must be *learned* from training data is preprocessing (Q3).
- **A model-specific feature isn't automatically "shared".** In the demo the derived usage table can only say "single consumer"; calling a feature
  *private* or promoting it to *shared* is a governance decision, not something code can decide. A common rule: keep it with the model until a second model wants it, then promote it (with an owner, definition and tests).
- **Cost of composing:** every extra entity/view is another lookup online (Q7), and every model-specific view is more pipelines to maintain.

### Follow-ups worth asking next
- When exactly should a model-specific feature be promoted to the shared store?
- How do I test that on-demand transforms are identical in training and serving?
- Should feature services be versioned together with the model?

---

## Q10. I have never seen a feature store actually shared across multiple models. Are there real examples?

**Short answer: yes, but almost all public examples are very large organisations, and your experience is the common one.**
Shared feature stores appear where **dozens of teams** build models on the **same entities**. Most companies' "feature store" is
per-model or per-team, which is why it can feel pointless (see [docs/02](docs/02-do-you-need-one.md)).

### Public examples (evidence strength noted)

| Company / system | What they say about sharing | Evidence |
|---|---|---|
| **LinkedIn — Feathr** | "Dozens of applications use Feathr to define features, compute them for training, deploy them in production, and share them across teams"; feature pipelines "in hundreds of model workflows" (Search, Feed, Ads). Concrete sharing: several **search and recommendation systems that use job-posting data** could not share features under application-specific pipelines, but did with Feathr. Some large projects cut time to add/experiment with a feature "from weeks to days". | **Primary** (LinkedIn Engineering blog, 2022) |
| **Uber — Michelangelo Palette** | Palette was "built to better manage and share feature pipelines across teams", supports batch and near-real-time features, and "hosts more than 20,000 features that can be leveraged out-of-box for Uber teams to build robust ML models". | **Primary** (Uber Engineering blog) |
| **Airbnb — Zipline, later Chronon** | Declarative feature definitions with a feature library for search and sharing across teams; consistent offline backfill and online serving. Chronon was open-sourced with Stripe as an early adopter/co-maintainer. | **Secondary** (search summaries + project pages; not read in detail) |
| **DoorDash — Redis-based feature store behind the Sibyl prediction service** | A centralised prediction service reading a shared Redis feature store; most of DoorDash's ML applications use it. | **Secondary** (primary posts were not retrievable; figures come from third-party summaries, so not quoted here) |

Notes on the evidence: these are company blog posts, so numbers are **self-reported and dated** (LinkedIn's post is from 2022), and they
describe successes, not failed adoptions. Treat them as existence proofs, not benchmarks.

### What these examples have in common
1. **Scale in teams, not just data** — dozens of teams and hundreds of models, so duplicated feature work is expensive.
2. **A shared entity** — LinkedIn's example is *job postings*: several systems consume the same entity's features. Sharing rarely happens across unrelated entities.
3. **Real-time and offline needs together** — Uber and Airbnb emphasise batch + streaming + online serving from one definition.
4. **A platform team** to own the store — sharing is an organisational capability, not a library.

### What this means for you
- If your models each use **their own event history** (different entities, labels and windows), there is little to share, and a per-model
  table is a reasonable design. Sharing shows up when a **second model wants the same entity's features**.
- Cheaper ways to get most of the reuse: shared SQL/feature *definitions* (a template per feature family), a common naming/ownership convention,
  and promoting a feature to a shared view only when a second consumer appears (Q9).
- A useful test: list your models' inputs and count features consumed by **≥2 models on the same entity**. If the count is near zero, you don't have a sharing problem yet.

### Follow-ups worth asking next
- How do those platforms decide who owns a shared feature and how changes are rolled out?
- What did teams do *before* the store (the pain that justified it)?
- Are there smaller-company examples (tens, not thousands, of features) where sharing paid off?

Sources: [LinkedIn — Open sourcing Feathr](https://www.linkedin.com/blog/engineering/open-source/open-sourcing-feathr--linkedin-s-feature-store-for-productive-m) ·
[Uber — From Predictive to Generative: How Michelangelo Accelerates Uber's AI Journey](https://www.uber.com/us/en/blog/from-predictive-to-generative-ai/) ·
[Airbnb — Chronon is now open source](https://medium.com/airbnb-engineering/chronon-airbnbs-ml-feature-platform-is-now-open-source-d9c4dba859e8) ·
[DoorDash — Building a gigascale ML feature store with Redis](https://careersatdoordash.com/blog/building-a-gigascale-ml-feature-store-with-redis/) (not retrievable at time of writing)

---

## Q11. What are the common access patterns of a feature store (offline and online), with use cases?

**Short answer:** the two you named are the core ones — offline reads by **entity + timestamp** (point-in-time) or **time range**, and online
reads by **key** — but there are a few more worth knowing. Run [`demos/09_access_patterns.py`](demos/09_access_patterns.py) to see each one.

### A note on your `event_id` observation: two data models
| Model | Row means | Key | "Latest value" exists? | Typical use |
|---|---|---|---|---|
| **Entity-timeline** (the standard feature-store model) | "customer 7's features as of time t" | `(entity_id, feature_ts)` | Yes — the newest row per entity | Real-time and batch scoring, shared features |
| **Event-scoped** | "the feature vector for *this* event, frozen at its time" | `event_id` (often with a tenant/entity prefix) | **No** — rows are immutable | Alert/case scoring, audit, reproducible training |

Event-scoped tables are a legitimate pattern (a spine joined with as-of features and saved), but they don't need an online store because
nothing asks for "the current value of event 123's features".

### Offline patterns

| # | Pattern | Access | Use cases |
|---|---|---|---|
| 1 | **Point-in-time join onto a spine** | spine of `(entity keys, event_ts)` → as-of features | Training and evaluation sets; the core operation |
| 2 | **Time-range scan** | `event_ts` (or partition/date) between A and B | Bulk training windows, drift baselines, backfill validation, monitoring |
| 3 | **Snapshot as of a date** | latest row per entity at/before *t*, TTL applied | Batch scoring ("score everyone as of the run date"), daily/monthly jobs |
| 4 | **Lookup by event id / key list** | `event_id IN (...)` or entity list | Event-scoped features, audit and debugging ("what did the model see for case X?") |
| 5 | **Incremental read by ingestion time** | rows written since watermark | Materialising to the online store, downstream syncs |
| 6 | **Time travel by ingestion time** | table version / "as known at" | Reproducing what a past training run saw after corrections (bitemporal, Q5) |

### Online patterns

| # | Pattern | Access | Use cases |
|---|---|---|---|
| 1 | **Single-key get** | `entity_id → feature vector` | Fraud check on a card, credit decision, personalised page for one user |
| 2 | **Multi-get (batch of keys)** | list of keys, one round trip | **Ranking/recommendation:** one user + hundreds of candidate items |
| 3 | **Multi-entity get** | one lookup per entity type, merged by the caller (Q7) | Fraud (card + merchant + device), ads (user + ad + advertiser) |
| 4 | **Composite / bucketed key** | `(user_id, merchant_id)`, `(geohash, hour)` | Pair features; ETA/pricing keyed by location cell and time bucket |
| 5 | **Fetch by id for large values** | id → embedding or list | Embedding/vector features, recent-event sequences |
| 6 | **Missing / stale handling** | key absent or older than TTL → `None` | Cold start, inactive users: the model needs a default path |

Online stores are key-value systems, so they are **not** designed for range scans, ad-hoc filters or joins; anything needing those is an offline job.

### Use case → pattern cheat-sheet

| Use case | Training (offline) | Serving |
|---|---|---|
| **Real-time fraud** | PIT join (1) with streaming features backfilled | single/multi-entity get (1, 3) with fresh windowed aggregates |
| **Recommendations / search ranking** | PIT join over impression logs (1) | multi-get of candidate features (2) + user get (1) |
| **ETA / dynamic pricing** | PIT join by location + time bucket (1, 4) | bucketed-key get (4) |
| **Credit / risk scoring** | PIT join (1), often event-scoped for audit | single get (1) *or* batch snapshot (3) |
| **Churn / monthly batch models** | range scan or snapshot (2, 3) | none: batch snapshot only |
| **Case / alert scoring** (event-scoped) | lookup by event/key list (4) + range scan (2) | none online |
| **Monitoring & audit** | range scan (2), time travel (6) | n/a |

### Rules of thumb
- Start from the **question the reader asks**: "as of this event" → PIT join; "everyone as of today" → snapshot; "what's true right now for this key" → online get.
- Pick the **key** for the access pattern (entity, composite, bucket), because online stores can't be re-queried by another attribute.
- Partition offline tables by **date/time** so range scans and snapshots stay cheap.
- Make the different reads **agree**: demo 9 asserts the snapshot equals a PIT join at the same instant, as demo 3 does for online vs offline.

### Follow-ups worth asking next
- How do I choose keys and partitioning so offline range scans and online gets are both fast?
- How do sequence/list features (last N events) work in a key-value online store?
- How should batch-scoring snapshots handle entities with no fresh value?

---

## Q12. How is adding/removing a feature managed? If I train a model today and 30 days later two features are dropped and three added, how do I keep reproducibility and traceability? What is this called, and what are the conventions?

**Short answer:** this is **schema evolution** plus **feature lifecycle management (versioning and deprecation)**, and the reproducibility
side is called **training-data lineage / provenance** (with **time travel** as one tool for it). The convention is: **never change a feature in place;
add new versions, deprecate old ones on a schedule, and make every model record exactly what it was trained on.**

### The vocabulary
| Term | Meaning |
|---|---|
| **Schema evolution** | Changing the set/shape of features. *Additive* (new feature) is usually backward-compatible; *removal, rename, or type/definition change* is **breaking**. |
| **Feature versioning** | A changed definition gets a new name/version (`avg_amount_30d_v2`), it does not overwrite the old one. |
| **Deprecation / lifecycle** | active → deprecated (warn) → frozen → archived → deleted, with a notice period and a check that no model still uses it. |
| **Model–feature contract / feature spec** | The list of feature names + versions a model was trained on and needs at serving. |
| **Lineage / provenance** | The recorded chain: model → feature spec → feature versions → source data + code version. |
| **Time travel / bitemporal data** | Querying a table as it was at an earlier version or "as known at" an earlier ingestion time. |
| **Expand–contract (parallel change)** | Migration technique: *expand* (add the new alongside the old), migrate consumers, then *contract* (remove the old). |

### What happens in your scenario (demo 10)
[`demos/10_feature_evolution.py`](demos/10_feature_evolution.py) trains on 4 features, then drops 2 and adds 3 "30 days later":

```
strategy                                        can reproduce the day-0 training set?
A  in-place redefinition of the view            FAILS (KeyError: the 2 dropped features are gone)
B  versioned views (v1 frozen, v2 added)        True
C  versioned, but source history expired        False   ← recompute differs once raw history is gone
D  training snapshot stored with the model      True

Serving the day-0 model after the change:
  in-place : FAILS (the deployed model asks for a feature that no longer exists)
  versioned: works
```
1. **The new features don't affect the old model.** It requests features *by name* and keeps working. The three new features matter only to a **new model version** trained on them.
2. **Removing a feature a live model uses breaks serving and retraining.** Hence deprecation, not deletion: a feature stays computed until every model that pins it is retired or retrained.
3. **New features have no history before they were created** unless you **backfill** them. Training a new model on an old window needs that backfill.
4. **"Dropped from the store" ≠ "data gone".** Normally the feature is removed from the active registry/serving while the offline data stays for a retention window. Reproducibility breaks when the *data* is actually deleted or expires.

### The three ways to make a training run reproducible
| Level | How | Survives feature removal? | Survives raw-data expiry? | Cost |
|---|---|---|---|---|
| **1. Recipe** | Record feature spec (names + versions), spine/query, as-of times, code version; recompute later | Only if old versions are kept | **No** | Low |
| **2. Time travel** | Query the offline table at the recorded version / timestamp | Yes, *while history is retained* | **No** (retention-limited) | Low–medium |
| **3. Snapshot** | Persist the exact training rows (versioned dataset) + hash with the model | **Yes** | **Yes** | Storage |

Audit- and regulation-grade work uses **level 3 (with level 1 metadata alongside)**. Demo 10's snapshot check is an integrity check: the stored rows still hash to the recorded value. Note it proves the *stored copy* is intact, not that the pipeline could regenerate it.

**Gotcha: time travel is not long-term storage.** In Delta Lake the default log retention is **30 days** (`delta.logRetentionDuration`) and the default retention of deleted data files is
**7 days** (`delta.deletedFileRetentionDuration`); `VACUUM` permanently removes older files. So a "30 days later" retrain may already be past what you can query, and the history may show versions whose data files are gone.
Raise retention deliberately, or snapshot/clone what you must reproduce.

### Conventions that work
1. **Additive by default.** Adding a feature is safe; consumers ask for features by name, not "all columns".
2. **Never redefine in place.** Changed logic → new name or version. Keep the old computing until consumers migrate.
3. **Deprecate, don't delete.** Mark deprecated, notify owners, block deletion while any registered model depends on it (needs the model→feature lineage), then freeze/archive after a notice period.
4. **Pin the contract to the model.** Store the feature spec (names, versions, table/view versions, transformer, code version) as a model artifact/tag.
5. **Snapshot or hash the training set** for anything you must reproduce, and record the ingestion-time cutoff.
6. **Backfill new features** before training on historical windows; record whether values are backfilled or organic.
7. **Test in CI:** every registered model's feature spec must still resolve in the store; fail the deprecation if not.
8. **Retrain to adopt changes.** New features → new model version → shadow/A-B → retire the old version → then contract.

### How real products handle it (verify against current docs)
| Product | Notes |
|---|---|
| **SageMaker Feature Store** | You can **add** features to an existing feature group (`UpdateFeatureGroup`), but added features **cannot be removed**, and adding a feature does **not** backfill existing records. Breaking changes mean a **new feature group**. |
| **Databricks** | Feature tables are Delta tables: columns can be added/dropped like any table, and Delta time travel is retention-limited (above). Logged models carry their feature lookups, so a removed column breaks scoring until retrained. |
| **Feast / Hopsworks / Tecton** | Feature views/groups are versioned in different ways (Hopsworks has explicit feature-group, feature-view and training-dataset versions); check how your version handles renames and removals. |

### Follow-ups worth asking next
- How do I block the deletion of a feature that a live model depends on (a lineage check in CI)?
- What should the model's feature-spec artifact contain, and where should it be stored?
- How long should training snapshots be retained, and how do I keep their cost down?

Sources: [Databricks — Work with table history](https://docs.databricks.com/aws/en/tables/history) ·
[Delta Lake — table utility commands (VACUUM)](https://docs.delta.io/delta-utility/) ·
[AWS — Add features and records to a feature group](https://docs.aws.amazon.com/sagemaker/latest/dg/feature-store-update-feature-group.html) ·
[AWS — UpdateFeatureGroup API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_UpdateFeatureGroup.html)

---

<!-- Add the next question below:

## Q13. <your question>

**Short answer:** …
-->
