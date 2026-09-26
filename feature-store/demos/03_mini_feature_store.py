"""Demo 3: the two problems from demos 1 and 2, solved by a tiny feature store.

Run:  uv run python demos/03_mini_feature_store.py
"""
from datetime import timedelta

import numpy as np
import pandas as pd

from data import make_transactions
from mini_feature_store import FeatureView, MiniFeatureStore

raw = make_transactions()
END = raw["ts"].max()


# ---- 1. Define the feature ONCE ---------------------------------------------
def compute_txn_stats(raw: pd.DataFrame) -> pd.DataFrame:
    """avg amount + count over a trailing 30 days, evaluated at every transaction."""
    df = raw[raw.amount > 0].sort_values("ts").set_index("ts")
    g = df.groupby("customer_id")["amount"].rolling("30D")
    out = pd.DataFrame({"avg_amount_30d": g.mean(), "txn_count_30d": g.count()})
    return out.reset_index().rename(columns={"ts": "event_ts"})


view = FeatureView(
    name="customer_txn_stats",
    entity_key="customer_id",
    features=["avg_amount_30d", "txn_count_30d"],
    ttl=timedelta(days=14),
    compute=compute_txn_stats,
)
store = MiniFeatureStore()
store.apply(view, raw)  # transformation runs once, here
FEATS = ["customer_txn_stats:avg_amount_30d", "customer_txn_stats:txn_count_30d"]

# ---- 2. Offline: a point-in-time correct training set ------------------------
rng = np.random.default_rng(0)
labels = pd.DataFrame(
    {
        "customer_id": rng.integers(0, 200, 500),
        "event_ts": pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.uniform(40, 85, 500), unit="D"),
        "label": rng.integers(0, 2, 500),
    }
)
train = store.get_historical_features(labels, FEATS)
leaks = (train["customer_txn_stats__feature_ts"] > train["event_ts"]).sum()
print("=== Offline: training set ===")
print(f"rows: {len(train)}   rows with a feature from the future: {leaks}")
print(f"rows with no fresh feature (NaN, beyond ttl or no history): {train.avg_amount_30d.isna().sum()}")
print(train.head(3).to_string(index=False, float_format="%.2f"))

# ---- 3. Materialize, then serve online --------------------------------------
n = store.materialize("customer_txn_stats", up_to=END)
print(f"\n=== Online: materialized {n} entities into the key-value store ===")
NOW = END + pd.Timedelta(hours=1)
print("lookup customer 3:", store.get_online_features(FEATS, 3, NOW))

# ---- 4. The real test: does online == offline for the same instant? ---------
customers = list(range(200))
offline_now = store.get_historical_features(
    pd.DataFrame({"customer_id": customers, "event_ts": NOW}), FEATS
).set_index("customer_id")

mismatch = 0
stale_online = 0
for c in customers:
    on = store.get_online_features(FEATS, c, NOW)
    for f in ("avg_amount_30d", "txn_count_30d"):
        a, b = on[f], offline_now.loc[c, f]
        if a is None:
            stale_online += 1 if f == "avg_amount_30d" else 0
        if (a is None) != pd.isna(b) or (a is not None and not np.isclose(a, b)):
            mismatch += 1

print("\n=== Consistency: online lookup vs offline as-of join at the same instant ===")
print(f"feature values compared: {len(customers) * 2}   mismatches: {mismatch}")
print(f"customers with no fresh feature (inactive > {view.ttl.days} days => ttl => None): {stale_online}")

print(
    "\nSkew is gone because there is ONE definition (compute_txn_stats) and both\n"
    "stores are filled from its output. Leakage is gone because the only way to\n"
    "read training data is the as-of join. What you're paying for: a second\n"
    "storage system, a materialization job, and a registry to keep in sync.\n"
)
