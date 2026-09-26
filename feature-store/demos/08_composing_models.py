"""Shared features are rarely enough. How do several models build on one store?

Each model = shared feature views  +  its own private view(s)  +  request-time (on-demand)
features  +  its own fitted preprocessing. The store is the common layer, not the whole input.

Run:  uv run python demos/08_composing_models.py
"""
from datetime import timedelta

import numpy as np
import pandas as pd

from data import make_transactions
from mini_feature_store import FeatureView, MiniFeatureStore

rng = np.random.default_rng(5)
raw = make_transactions()
raw["merchant_id"] = rng.integers(0, 25, len(raw))
END = raw["ts"].max()


def rolling(df: pd.DataFrame, key: str, col: str, out: dict) -> pd.DataFrame:
    g = df.sort_values("ts").set_index("ts").groupby(key)[col].rolling("30D")
    res = pd.DataFrame({name: getattr(g, fn)() for name, fn in out.items()})
    return res.reset_index().rename(columns={"ts": "event_ts"})


def customer_stats(r):  # SHARED: many models want it
    return rolling(r[r.amount > 0], "customer_id", "amount", {"cust_avg_30d": "mean", "cust_txn_30d": "count"})


def merchant_stats(r):  # SHARED
    return rolling(r[r.amount > 0], "merchant_id", "amount", {"merch_avg_30d": "mean"})


def night_activity(r):  # PRIVATE to model B: only it cares about time-of-day behaviour
    r = r.assign(night=(r.ts.dt.hour < 6).astype(float))
    return rolling(r, "customer_id", "night", {"night_share_30d": "mean"})


TTL = timedelta(days=14)
store = MiniFeatureStore()
store.apply(FeatureView("cust", "customer_id", ["cust_avg_30d", "cust_txn_30d"], TTL, customer_stats), raw)
store.apply(FeatureView("merch", "merchant_id", ["merch_avg_30d"], TTL, merchant_stats), raw)
store.apply(FeatureView("night", "customer_id", ["night_share_30d"], TTL, night_activity), raw)


# ---- request-time (on-demand) feature: uses the REQUEST + a stored feature -------
def amount_vs_avg(amount, cust_avg_30d):
    """ONE function used by training and serving, so it cannot skew."""
    return amount / cust_avg_30d


# ---- each model declares what it consumes ("feature service" / training-set spec) --
MODELS = {
    "model_a": ["cust:cust_avg_30d", "cust:cust_txn_30d", "merch:merch_avg_30d"],  # shared only
    "model_b": ["cust:cust_avg_30d", "night:night_share_30d"],  # 1 shared + 1 private (+ on-demand below)
}

# ---- training sets from the same store, different columns --------------------------
spine = (
    raw.sample(300, random_state=2)
    .rename(columns={"ts": "event_ts"})[["customer_id", "merchant_id", "event_ts", "amount"]]
)
spine = spine[spine.event_ts > raw.ts.min() + pd.Timedelta(days=40)]
train = {m: store.get_historical_features(spine, feats) for m, feats in MODELS.items()}
train["model_b"]["amount_vs_avg"] = amount_vs_avg(train["model_b"].amount, train["model_b"].cust_avg_30d)

print("=== One store, two models, different inputs ===")
for m, df in train.items():
    cols = [c for c in df.columns if c not in ("customer_id", "merchant_id", "event_ts", "amount") and "__feature_ts" not in c]
    print(f"{m}: {cols}")
print("\nview      computed   used by")
for view in store.views:
    users = [m for m, feats in MODELS.items() if any(f.split(":")[0] == view for f in feats)]
    kind = "shared" if len(users) > 1 else "single consumer"
    print(f"{view:<9} once       {', '.join(users):<16} ({kind})")
print("amount_vs_avg: per request, model_b only (on-demand: needs the live request)\n")

# ---- serving model_b: stored features + the live request, same on-demand function ----
store.materialize("cust", up_to=END)
store.materialize("night", up_to=END)
NOW = END + pd.Timedelta(hours=1)
customers = list(range(200))
request_amount = {c: 20.0 + c for c in customers}  # each customer's incoming request amount

offline = store.get_historical_features(
    pd.DataFrame({"customer_id": customers, "event_ts": NOW, "amount": [request_amount[c] for c in customers]}),
    MODELS["model_b"],
).set_index("customer_id")
offline["amount_vs_avg"] = amount_vs_avg(offline.amount, offline.cust_avg_30d)

mismatch = 0
for c in customers:
    on = store.get_online_features(MODELS["model_b"], c, NOW)
    on["amount_vs_avg"] = None if on["cust_avg_30d"] is None else amount_vs_avg(request_amount[c], on["cust_avg_30d"])
    for f in ("cust_avg_30d", "night_share_30d", "amount_vs_avg"):
        a, b = on[f], offline.loc[c, f]
        if (a is None) != pd.isna(b) or (a is not None and not np.isclose(a, b)):
            mismatch += 1
print("=== Serving model_b: stored + private + on-demand features vs. the offline build ===")
print(f"values compared: {len(customers) * 3}   mismatches: {mismatch}")
print("The on-demand column needs the live request, so it is computed at request time by the SAME function training used.")
