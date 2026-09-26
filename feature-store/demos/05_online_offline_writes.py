"""If you use an online store, do the feature rows also land in the offline store?

Only if the write path puts them there. This demo shows the three write paths
and what each one costs you later.

Run:  uv run python demos/05_online_offline_writes.py
"""
from datetime import timedelta

import pandas as pd

from data import make_transactions
from mini_feature_store import FeatureView, MiniFeatureStore

raw = make_transactions()
END = raw["ts"].max()
FEATS = ["stats:avg_amount_30d", "stats:txn_count_30d"]


def compute(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw.amount > 0].sort_values("ts").set_index("ts")
    g = df.groupby("customer_id")["amount"].rolling("30D")
    out = pd.DataFrame({"avg_amount_30d": g.mean(), "txn_count_30d": g.count()})
    return out.reset_index().rename(columns={"ts": "event_ts"})


store = MiniFeatureStore()
store.apply(
    FeatureView("stats", "customer_id", ["avg_amount_30d", "txn_count_30d"], timedelta(days=14), compute),
    raw,
)
store.materialize("stats", up_to=END)  # PATH 1: batch -> offline, then copy to online

ACTIVE = raw[raw.ts > END - pd.Timedelta(days=3)].customer_id.unique()
c_both, c_online_only = int(ACTIVE[0]), int(ACTIVE[1])


def offline_value(customer: int, at: pd.Timestamp):
    df = store.get_historical_features(pd.DataFrame({"customer_id": [customer], "event_ts": [at]}), FEATS)
    return df.avg_amount_30d.iloc[0]


print("=== PATH 1: batch. Offline is written first; online is a copy of its latest row ===")
print("every online row already exists in offline history by construction "
      "(materialize reads it from there).\n")

# ---- PATH 2: dual write (streaming push -> online AND offline) ---------------
t1, t2 = END + pd.Timedelta(hours=1), END + pd.Timedelta(hours=5)
for t, v in [(t1, 100.0), (t2, 200.0)]:
    store.push(
        "stats",
        pd.DataFrame({"customer_id": [c_both], "event_ts": [t], "avg_amount_30d": [v], "txn_count_30d": [7.0]}),
        to_offline=True,
    )
print(f"=== PATH 2: streaming push to BOTH stores (customer {c_both}) ===")
print("online now (latest only):       ", store.get_online_features(FEATS, c_both, t2 + pd.Timedelta(minutes=1))["avg_amount_30d"])
print("offline as of t1 + 1 minute:    ", offline_value(c_both, t1 + pd.Timedelta(minutes=1)), " <- history kept")
print("offline as of t2 + 1 minute:    ", offline_value(c_both, t2 + pd.Timedelta(minutes=1)))
print("Online holds ONE value per entity (overwritten); offline holds every version.\n")

# ---- PATH 3: online-only write (the mistake) ---------------------------------
store.push(
    "stats",
    pd.DataFrame({"customer_id": [c_online_only], "event_ts": [t1], "avg_amount_30d": [100.0], "txn_count_30d": [7.0]}),
    to_offline=False,
)
served = store.get_online_features(FEATS, c_online_only, t2)["avg_amount_30d"]
trained = offline_value(c_online_only, t2)
print(f"=== PATH 3: streaming push to ONLINE ONLY (customer {c_online_only}) ===")
print(f"value the model was SERVED at t2:        {served}")
print(f"value a training set would REPRODUCE:    {trained:.2f}   <- the pushed value never reached offline")
print(
    "\nThat gap is training/serving skew created by the write path. Nothing errors.\n"
    "Once the online value is overwritten again, it is gone for good: you can no\n"
    "longer rebuild what the model saw.\n"
)
