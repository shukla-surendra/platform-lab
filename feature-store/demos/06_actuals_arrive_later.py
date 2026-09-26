"""Ground-truth "actuals" arrive AFTER the prediction. How do they meet the features?

1. The online store never holds labels. Serving writes a LOG; actuals are joined
   to that log later, offline.
2. Actuals DO change some features - ones built from past outcomes (e.g. "share of
   this customer's previous cases that turned out to be violations"). Those must be
   computed from outcomes KNOWN AT THAT TIME, or training and serving disagree.

Run:  uv run python demos/06_actuals_arrive_later.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(3)
N_CUST, DAYS = 300, 240
START = pd.Timestamp("2026-01-01")

# ---- ground truth: cases (events) with an outcome that is confirmed LATER ------
rows = []
for c in range(N_CUST):
    risk = rng.beta(2, 6)
    for _ in range(rng.poisson(12)):
        ts = START + pd.Timedelta(days=float(rng.uniform(0, DAYS)))
        rows.append(
            {
                "customer_id": c,
                "event_ts": ts,
                "label": int(rng.random() < risk),  # the "actual"
                "outcome_ts": ts + pd.Timedelta(days=float(rng.uniform(3, 45))),  # when it becomes known
            }
        )
ev = pd.DataFrame(rows).sort_values("event_ts").reset_index(drop=True)
ev["event_id"] = ev.index

# ---- 1. The serving log: what was served, when. Labels are NOT in it. ---------
# A label-derived feature: share of the customer's PREVIOUS events that were violations.
served_rate, final_rate, n_known, n_prior = [], [], [], []
for _, g in ev.groupby("customer_id"):
    g = g.sort_values("event_ts")
    for _, e in g.iterrows():
        prior = g[g.event_ts < e.event_ts]
        known = prior[prior.outcome_ts <= e.event_ts]  # outcomes confirmed by prediction time
        served_rate.append((e.event_id, known.label.mean() if len(known) else np.nan))
        final_rate.append((e.event_id, prior.label.mean() if len(prior) else np.nan))
        n_known.append((e.event_id, len(known)))
        n_prior.append((e.event_id, len(prior)))

ev = ev.set_index("event_id")
ev["served_rate"] = pd.Series(dict(served_rate))  # what the online store could have held
ev["final_rate"] = pd.Series(dict(final_rate))  # what you get by joining "current" outcomes
ev["n_known"] = pd.Series(dict(n_known))
ev["n_prior"] = pd.Series(dict(n_prior))

print("=== The serving log has features + predictions, but no labels yet ===")
serving_log = ev[["customer_id", "event_ts", "served_rate"]]
print(serving_log.head(3).to_string(), "\n")

# ---- 2. Actuals arrive later: join them to the log -------------------------------
print("=== Actuals arrive late: share of logged events that can be labelled, by age ===")
TODAY = START + pd.Timedelta(days=DAYS)
age = (TODAY - ev.event_ts).dt.days
labelled = ev.outcome_ts <= TODAY
for lo, hi in [(0, 15), (15, 30), (30, 60), (60, 400)]:
    m = (age >= lo) & (age < hi)
    print(f"events aged {lo:>3}-{hi:<3} days: {labelled[m].mean():5.0%} labelled ({int(m.sum())} events)")
print("-> recent events cannot be trained on yet; the label join is a delayed, offline job.\n")

# ---- 3. The label-derived feature: served vs. 'join today's outcomes' -------------
both = ev.dropna(subset=["served_rate", "final_rate"])
diff = (both.served_rate - both.final_rate).abs()
print("=== Label-derived feature: value the model was SERVED vs. value a naive training join produces ===")
print(f"events compared:                           {len(both)}")
print(f"training value differs from served value: {(diff > 1e-9).mean():.0%}")
print(f"avg prior cases counted, served / naive:   {both.n_known.mean():.1f} / {both.n_prior.mean():.1f}")
print(
    "Naive training uses outcomes that were still unconfirmed when the prediction was made,\n"
    "so it sees a more 'mature' history than production ever will.\n"
)

# ---- 4. The fix: an as-known-at-t training value ---------------------------------
# Independent implementation (a self-join, as a batch training job would write it) of the
# rule "previous events whose outcome was already known at event_ts".
r = ev.reset_index()[["event_id", "customer_id", "event_ts", "label", "outcome_ts"]]
pairs = r[["event_id", "customer_id", "event_ts"]].merge(
    r.rename(columns={"event_id": "prior_id", "event_ts": "prior_ts", "label": "prior_label", "outcome_ts": "prior_outcome_ts"}),
    on="customer_id",
)
pairs = pairs[(pairs.prior_ts < pairs.event_ts) & (pairs.prior_outcome_ts <= pairs.event_ts)]
training_value = pairs.groupby("event_id").prior_label.mean().reindex(ev.index)

same = np.isclose(training_value.to_numpy(float), ev.served_rate.to_numpy(float), equal_nan=True)
print("=== Fix: training recomputes the feature from outcomes known at event time (needs outcome_ts) ===")
print(f"events where training value == served value: {same.mean():.0%} of {len(ev)}")
print(
    "This needs the SOURCE to record WHEN each outcome became known (outcome_ts). A feature\n"
    "store cannot invent that history - it only makes the as-of join easy once it exists."
)
