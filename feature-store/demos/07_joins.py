"""Does a feature store support joins?  Yes - but a specific kind.

What it joins: several feature views (possibly for DIFFERENT entities) onto a table of
(keys, event_ts) rows, each one point-in-time correct, on entity keys.
What it does NOT do: arbitrary relational joins. The joins across your source tables
happen earlier, inside the feature computation.

Run:  uv run python demos/07_joins.py
"""
from datetime import timedelta

import numpy as np
import pandas as pd

from data import make_transactions
from mini_feature_store import FeatureView, MiniFeatureStore

rng = np.random.default_rng(11)
raw = make_transactions()
raw["merchant_id"] = rng.integers(0, 25, len(raw))  # each transaction also belongs to a merchant
END = raw["ts"].max()


# ---- JOIN TYPE 1 (inside the pipeline, NOT the store): combine source tables ----
# e.g. transactions ⟕ merchants ⟕ customers ... happens here, in the feature computation.
def customer_stats(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw.amount > 0].sort_values("ts").set_index("ts")
    g = df.groupby("customer_id")["amount"].rolling("30D")
    out = pd.DataFrame({"cust_avg_30d": g.mean(), "cust_txn_30d": g.count()})
    return out.reset_index().rename(columns={"ts": "event_ts"})


def merchant_stats(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw.amount > 0].sort_values("ts").set_index("ts")
    g = df.groupby("merchant_id")["amount"].rolling("30D")
    out = pd.DataFrame({"merch_avg_30d": g.mean(), "merch_txn_30d": g.count()})
    return out.reset_index().rename(columns={"ts": "event_ts"})


store = MiniFeatureStore()
store.apply(FeatureView("cust", "customer_id", ["cust_avg_30d", "cust_txn_30d"], timedelta(days=14), customer_stats), raw)
store.apply(FeatureView("merch", "merchant_id", ["merch_avg_30d", "merch_txn_30d"], timedelta(days=14), merchant_stats), raw)

# ---- JOIN TYPE 2 (the store's job): features onto (keys, event_ts) rows ----------
# The "spine": events we want to score/learn from. It carries BOTH entity keys.
spine = raw.sample(400, random_state=1).rename(columns={"ts": "event_ts"})[["customer_id", "merchant_id", "event_ts"]]
spine = spine[spine.event_ts > raw.ts.min() + pd.Timedelta(days=40)].reset_index(drop=True)

train = store.get_historical_features(
    spine, ["cust:cust_avg_30d", "cust:cust_txn_30d", "merch:merch_avg_30d", "merch:merch_txn_30d"]
)
print("=== Two feature views for two different entities, joined onto one spine ===")
print(train.head(3).to_string(index=False, float_format="%.2f"))

leaks = int((train["cust__feature_ts"] > train["event_ts"]).sum() + (train["merch__feature_ts"] > train["event_ts"]).sum())
print(f"\nrows: {len(train)}   feature values from the future (either view): {leaks}")
exact = int((train["cust__feature_ts"] == train["event_ts"]).sum())
print(
    f"rows where the customer feature_ts == event_ts: {exact}  <- the spine rows ARE transactions, so the value already\n"
    "  includes the event being scored. Decide deliberately whether the event may count (as-of is inclusive here; use a\n"
    "  strictly-before join, or exclude the event in the feature, if the label depends on that event)."
)
print(f"rows missing a fresh customer value: {train.cust_avg_30d.isna().sum()}   merchant value: {train.merch_avg_30d.isna().sum()}")

# ---- verify against an independent, direct computation ---------------------------
def direct_avg(key: str, value, at: pd.Timestamp) -> float:
    """Latest positive txn for this key at/before `at`; mean of positives in the 30 days ending at it."""
    d = raw[(raw[key] == value) & (raw.amount > 0) & (raw.ts <= at)]
    if d.empty:
        return np.nan
    last = d.ts.max()
    if at - last > timedelta(days=14):  # ttl
        return np.nan
    return d[(d.ts > last - pd.Timedelta(days=30)) & (d.ts <= last)].amount.mean()

sample = train.sample(60, random_state=0)
ok = all(
    np.isclose(direct_avg("customer_id", r.customer_id, r.event_ts), r.cust_avg_30d, equal_nan=True)
    and np.isclose(direct_avg("merchant_id", r.merchant_id, r.event_ts), r.merch_avg_30d, equal_nan=True)
    for r in sample.itertuples()
)
print(f"independent recomputation matches the joined values for 60 sampled rows: {ok}")

# ---- ONLINE: no relational join, just one keyed lookup per view -------------------
store.materialize("cust", up_to=END)
store.materialize("merch", up_to=END)
now = END + pd.Timedelta(hours=1)
cust_feats = store.get_online_features(["cust:cust_avg_30d"], 3, now)  # lookup 1 (key: customer_id)
merch_feats = store.get_online_features(["merch:merch_avg_30d"], 7, now)  # lookup 2 (key: merchant_id)
print("\n=== Online 'join' = one key lookup per entity, combined by the caller ===")
print({**cust_feats, **merch_feats})
