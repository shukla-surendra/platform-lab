"""Problem #2: point-in-time correctness (label leakage through joins).

Scenario: predict whether a customer will churn. The feature is
`tickets_7d` — support tickets filed in the last 7 days — snapshotted weekly.
Customers who are about to cancel file a few extra tickets; customers who HAVE
cancelled file a flood (billing, closure, refunds).

To build a training set you must join labels to features. The question is
WHICH snapshot of the feature you attach to each label.

Run:  uv run python demos/02_point_in_time_leakage.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N, WEEKS = 3000, 26
START = pd.Timestamp("2026-01-05")
week_ts = [START + pd.Timedelta(weeks=w) for w in range(WEEKS)]

# ---- ground truth: who churns, and when ------------------------------------
churner = rng.random(N) < 0.30
churn_week = np.where(churner, rng.integers(10, 25, N), -1)

# ---- feature snapshots: one row per customer per week ----------------------
snap_rows = []
for c in range(N):
    for w in range(WEEKS):
        if churner[c] and w >= churn_week[c]:
            lam = 6.0  # already churned: closure/billing ticket flood
        elif churner[c] and w >= churn_week[c] - 3:
            lam = 1.5  # the weak, genuinely predictive pre-churn signal
        else:
            lam = 1.0
        snap_rows.append((c, week_ts[w], rng.poisson(lam)))
snapshots = pd.DataFrame(snap_rows, columns=["customer_id", "ts", "tickets_7d"])

# ---- label events: "as of time t, will this customer churn soon?" ----------
# Churners: predict 2 weeks before they leave. Non-churners: a random week.
event_week = np.where(churner, churn_week - 2, rng.integers(8, 23, N))
labels = pd.DataFrame(
    {
        "customer_id": np.arange(N),
        "event_ts": [week_ts[w] for w in event_week],
        "churned": churner.astype(int),
    }
)


def auc(y: np.ndarray, score: np.ndarray) -> float:
    """Rank-based AUC (no sklearn needed)."""
    r = pd.Series(score).rank(method="average").to_numpy()
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# ---- WRONG: join to the latest value of the feature ("the current table") --
# This is what happens when you join labels to a normal dimension/feature
# table that only holds today's value.
latest = snapshots.sort_values("ts").groupby("customer_id").tail(1)[["customer_id", "tickets_7d"]]
naive = labels.merge(latest, on="customer_id")

# ---- RIGHT: as-of join — the value that was true at event_ts ---------------
pit = pd.merge_asof(
    labels.sort_values("event_ts"),
    snapshots.rename(columns={"ts": "feature_ts"}).sort_values("feature_ts"),
    left_on="event_ts",
    right_on="feature_ts",
    by="customer_id",
    direction="backward",
)
assert (pit.feature_ts <= pit.event_ts).all(), "a feature from the future slipped in"

print("=== How well does `tickets_7d` alone predict churn? (AUC; 0.5 = coin flip) ===")
print(f"naive join (latest value):    {auc(naive.churned.to_numpy(), naive.tickets_7d.to_numpy()):.3f}")
print(f"point-in-time (as-of) join:   {auc(pit.churned.to_numpy(), pit.tickets_7d.to_numpy()):.3f}")

ex = int(np.flatnonzero(churner)[0])
print(f"\nExample churner (customer {ex}), prediction time {labels.loc[ex, 'event_ts'].date()}, churns week {churn_week[ex]}:")
print(f"  feature the naive join attached: {int(naive.loc[naive.customer_id == ex, 'tickets_7d'].iloc[0])}  (from AFTER they churned)")
print(f"  feature that was knowable then:  {int(pit.loc[pit.customer_id == ex, 'tickets_7d'].iloc[0])}")

print(
    "\nThe naive model looks brilliant in the notebook and is near-useless in\n"
    "production, because at prediction time the post-churn ticket flood doesn't\n"
    "exist yet. The bug is invisible in the code — it is a *semantic* error in\n"
    "the join. 'Give me each feature as of this timestamp' is the operation a\n"
    "feature store exists to make correct-by-default (see demo 3)."
)
