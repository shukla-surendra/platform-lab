"""Common feature-store access patterns, offline and online, and the use case each serves.

Run:  uv run python demos/09_access_patterns.py
"""
from datetime import timedelta

import numpy as np
import pandas as pd

from data import make_transactions
from mini_feature_store import FeatureView, MiniFeatureStore, get_online_features_batch

raw = make_transactions()
END = raw["ts"].max()
FEATS = ["stats:avg_amount_30d", "stats:txn_count_30d"]


def compute(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw.amount > 0].sort_values("ts").set_index("ts")
    g = df.groupby("customer_id")["amount"].rolling("30D")
    out = pd.DataFrame({"avg_amount_30d": g.mean(), "txn_count_30d": g.count()})
    return out.reset_index().rename(columns={"ts": "event_ts"})


store = MiniFeatureStore()
store.apply(FeatureView("stats", "customer_id", ["avg_amount_30d", "txn_count_30d"], timedelta(days=14), compute), raw)
customers = sorted(raw.customer_id.unique())

print("################ OFFLINE ################")

# 1. Point-in-time join onto a spine of (entity, event_ts)  -> TRAINING SETS
spine = raw.sample(200, random_state=0).rename(columns={"ts": "event_ts"})[["customer_id", "event_ts"]]
spine = spine[spine.event_ts > raw.ts.min() + pd.Timedelta(days=40)]
pit = store.get_historical_features(spine, FEATS)
print(f"1. PIT join (spine of {len(spine)} keyed events)        -> {len(pit)} rows   [training sets, evaluation sets]")

# 2. Time-range scan  -> BULK reads: monitoring baselines, backfill checks, big training windows
feb = store.range_scan("stats", "2026-02-01", "2026-03-01")
print(f"2. Range scan  event_ts in [Feb 1, Mar 1)             -> {len(feb)} rows   [drift baselines, backfill validation, bulk training]")

# 3. Snapshot as of a date  -> BATCH SCORING: 'score everyone as of the run date'
AS_OF = pd.Timestamp("2026-03-15")
snap = store.snapshot("stats", AS_OF)
print(f"3. Snapshot as of {AS_OF.date()} (latest per entity, ttl applied) -> {len(snap)} entities   [nightly/monthly batch scoring]")

# consistency: the snapshot equals a PIT join for every entity at that same instant
ref = store.get_historical_features(pd.DataFrame({"customer_id": customers, "event_ts": AS_OF}), FEATS).dropna(subset=["avg_amount_30d"])
merged = snap.merge(ref, on="customer_id", suffixes=("_snap", "_pit"))
ok = len(snap) == len(ref) and np.allclose(merged.avg_amount_30d_snap, merged.avg_amount_30d_pit)
print(f"   snapshot == PIT join for the same instant: {ok}\n")

# 4. Event-scoped table: features frozen at each event's own time, addressed by event_id
events = raw.sample(150, random_state=4).rename(columns={"ts": "event_ts"}).reset_index(drop=True)
events["event_id"] = events.index
events = events[events.event_ts > raw.ts.min() + pd.Timedelta(days=40)]
event_table = store.get_historical_features(events[["event_id", "customer_id", "event_ts"]], FEATS).set_index("event_id")
eid = int(events.event_id.iloc[0])
print(f"4. Event-scoped rows: lookup by event_id={eid}: {event_table.loc[eid, 'avg_amount_30d']:.2f} "
      f"(fixed at that event's time)   [alert/case scoring, audit, reproducible training]")
print("   there is no 'latest value' here: each row is one event's immutable feature vector.\n")

print("################ ONLINE ################")
store.materialize("stats", up_to=END)
NOW = END + pd.Timedelta(hours=1)

# 5. Single-key get  -> one entity per request (fraud check on a card, credit decision)
print("5. get(customer_id=3):", {k: round(v, 2) for k, v in store.get_online_features(FEATS, 3, NOW).items()},
      "  [single-entity real-time decision]")

# 6. Multi-get: many keys, one call  -> RANKING / RECOMMENDATION over candidates
candidates = customers[:100]
batch = get_online_features_batch(store, FEATS, candidates, NOW)
fresh = sum(v["avg_amount_30d"] is not None for v in batch.values())
print(f"6. multi-get of {len(candidates)} keys in one call -> {fresh} fresh, {len(candidates) - fresh} missing/stale   [rank N candidates per request]")

# 7. Multi-entity get  -> one request needs several entity types (see demo 7 / 8)
print("7. multi-entity get = one lookup per entity type, combined by the caller (customer + merchant + device)   [fraud, ads]")

# 8. Missing / stale key -> None (TTL): the model must have a default path
stale = [c for c in customers if store.get_online_features(FEATS, c, NOW)["avg_amount_30d"] is None]
print(f"8. missing/stale keys return None: {len(stale)} of {len(customers)} entities   [cold start, inactive users -> default handling]")
