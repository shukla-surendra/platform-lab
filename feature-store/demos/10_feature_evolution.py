"""Train today. 30 days later: 2 features dropped, 3 added. What still works?

Compares management conventions:
  IN-PLACE   redefine the feature view under the same name           (the anti-pattern)
  VERSIONED  keep the old view frozen, add a new version             (expand / contract)
  SNAPSHOT   store the exact training set with the model             (audit-grade)
and what happens when the source history has expired (retention).

Run:  uv run python demos/10_feature_evolution.py
"""
import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

from data import make_transactions
from mini_feature_store import FeatureView, MiniFeatureStore

raw = make_transactions()
END = raw["ts"].max()  # "today"
TTL = timedelta(days=14)


def _roll(r, agg):
    df = r.sort_values("ts").set_index("ts")
    g = df.groupby("customer_id")["amount"].rolling("30D")
    out = pd.DataFrame({name: fn(g) for name, fn in agg.items()})
    return out.reset_index().rename(columns={"ts": "event_ts"})


# ---- v1: what the model was trained on -------------------------------------------
def compute_v1(r):
    pos = r[r.amount > 0]
    out = _roll(pos, {"avg_amount_30d": lambda g: g.mean(), "txn_count_30d": lambda g: g.count(),
                      "max_amount_30d": lambda g: g.max()})
    refunds = r.assign(is_refund=(r.amount < 0).astype(float)).sort_values("ts").set_index("ts")
    rs = refunds.groupby("customer_id")["is_refund"].rolling("30D").mean().rename("refund_share_30d")
    return out.merge(rs.reset_index().rename(columns={"ts": "event_ts"}), on=["customer_id", "event_ts"], how="left")


V1 = ["avg_amount_30d", "txn_count_30d", "max_amount_30d", "refund_share_30d"]


# ---- v2 (30 days later): dropped max_amount_30d + refund_share_30d, added 3 new ------
def compute_v2(r):
    pos = r[r.amount > 0]
    return _roll(pos, {"avg_amount_30d": lambda g: g.mean(), "txn_count_30d": lambda g: g.count(),
                       "std_amount_30d": lambda g: g.std(), "min_amount_30d": lambda g: g.min(),
                       "sum_amount_30d": lambda g: g.sum()})


V2 = ["avg_amount_30d", "txn_count_30d", "std_amount_30d", "min_amount_30d", "sum_amount_30d"]


def digest(df: pd.DataFrame, cols) -> str:
    d = df[["customer_id", "event_ts", *cols]].sort_values(["customer_id", "event_ts"]).reset_index(drop=True)
    d[list(cols)] = d[list(cols)].round(6)
    return hashlib.sha256(d.to_csv(index=False).encode()).hexdigest()[:12]


# ---- DAY 0: train, and record what the model needs to be reproduced --------------
rng = np.random.default_rng(0)
spine = pd.DataFrame(
    {
        "customer_id": rng.integers(0, 200, 400),
        "event_ts": raw.ts.min() + pd.to_timedelta(rng.uniform(50, 85, 400), unit="D"),
        "label": rng.integers(0, 2, 400),
    }
)
store = MiniFeatureStore()
store.apply(FeatureView("stats_v1", "customer_id", V1, TTL, compute_v1), raw)
train0 = store.get_historical_features(spine, [f"stats_v1:{f}" for f in V1])
MODEL_RECORD = {
    "features": [f"stats_v1:{f}" for f in V1],  # the model's feature contract
    "spine": spine.copy(),  # the (entity, event_ts, label) rows used
    "dataset_hash": digest(train0, V1),
    "training_snapshot": train0.copy(),  # option: keep the exact rows
}
print(f"DAY 0: trained on {len(V1)} features {V1}\n       training-set hash {MODEL_RECORD['dataset_hash']}\n")

# ---- DAY 30 ----------------------------------------------------------------------
print("DAY 30: max_amount_30d and refund_share_30d dropped; std/min/sum added.\n")


def reproduce(store, label):
    try:
        df = store.get_historical_features(MODEL_RECORD["spine"], MODEL_RECORD["features"])
        return digest(df, V1) == MODEL_RECORD["dataset_hash"]
    except Exception as e:  # noqa: BLE001
        return f"FAILS ({type(e).__name__}: {e})"


# A. IN-PLACE: same view name, new definition
inplace = MiniFeatureStore()
inplace.apply(FeatureView("stats_v1", "customer_id", V2, TTL, compute_v2), raw)  # 'stats_v1' overwritten
res_a = reproduce(inplace, "in-place")

# B. VERSIONED: old view kept frozen, new view added alongside
versioned = MiniFeatureStore()
versioned.apply(FeatureView("stats_v1", "customer_id", V1, TTL, compute_v1), raw)
versioned.apply(FeatureView("stats_v2", "customer_id", V2, TTL, compute_v2), raw)
res_b = reproduce(versioned, "versioned")

# C. VERSIONED, but source history has expired (retention) -> recompute is not the same
short_raw = raw[raw.ts >= END - pd.Timedelta(days=45)]
expired = MiniFeatureStore()
expired.apply(FeatureView("stats_v1", "customer_id", V1, TTL, compute_v1), short_raw)
res_c = reproduce(expired, "versioned + history expired")

# D. SNAPSHOT: exact rows stored with the model
snap = MODEL_RECORD["training_snapshot"]
res_d = digest(snap, V1) == MODEL_RECORD["dataset_hash"]

print(f"{'strategy':<52}{'can reproduce the day-0 training set?'}")
print(f"{'A  in-place redefinition of the view':<52}{res_a}")
print(f"{'B  versioned views (v1 frozen, v2 added)':<52}{res_b}")
print(f"{'C  versioned, but source history expired':<52}{res_c}")
print(f"{'D  training snapshot stored with the model':<52}{res_d}")

# ---- serving: the deployed model still expects the day-0 features ------------------
print("\nServing the day-0 model after the change (customer 3):")
inplace.materialize("stats_v1", up_to=END)
try:
    served = inplace.get_online_features([f"stats_v1:{f}" for f in V1], 3, END + pd.Timedelta(hours=1))
    print("  in-place :", {k: (None if v is None else round(v, 2)) for k, v in served.items()})
except Exception as e:  # noqa: BLE001
    print(f"  in-place : FAILS ({type(e).__name__}: {e})  <- the deployed model asks for a feature that no longer exists")
versioned.materialize("stats_v1", up_to=END)
ok = versioned.get_online_features([f"stats_v1:{f}" for f in V1], 3, END + pd.Timedelta(hours=1))
print("  versioned:", {k: (None if v is None else round(v, 2)) for k, v in ok.items()})
print("\nNew features (v2) only matter to a NEW model version trained on them; the old model keeps using v1 until retired.")
