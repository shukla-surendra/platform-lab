"""OFFLINE: point-in-time join onto a spine (Q1, Q2, Q7, Q8 in ../../doubt.md).

The spine = labelled transactions (customer_id, merchant_id, event_timestamp, label).
Feast attaches, for EACH row, the feature values that were latest at-or-before that row's timestamp,
from EACH feature view (customer_stats, merchant_stats), each on its own entity key.

Run:  docker compose run --rm workbench python explore/01_offline_pit.py
"""
import pandas as pd
from common import banner, sql, store

banner("spine: labelled events (kept separate from the feature store)")
spine = sql(
    """
    SELECT txn_id, customer_id, merchant_id, event_timestamp, label
    FROM transactions
    WHERE event_timestamp BETWEEN now() - interval '60 days' AND now() - interval '2 days'
    ORDER BY random() LIMIT 300
    """
)
print(spine.head(3).to_string(index=False))

banner("Feast get_historical_features(spine, feature_service='model_a')")
train = store.get_historical_features(entity_df=spine, features=store.get_feature_service("model_a")).to_df()
print(train.head(3).to_string(index=False))
print(f"\nrows: {len(train)}   rows with a missing customer feature (no fresh value within ttl): {train.avg_amount_30d.isna().sum()}")

banner("independent check: recompute the customer join with pandas merge_asof (14-day ttl)")
cust = sql("SELECT customer_id, event_timestamp AS feature_ts, avg_amount_30d, txn_count_30d FROM customer_stats")
left = spine.copy()
left["event_timestamp"] = pd.to_datetime(left.event_timestamp, utc=True)
cust["feature_ts"] = pd.to_datetime(cust.feature_ts, utc=True)
expected = pd.merge_asof(
    left.sort_values("event_timestamp"),
    cust.sort_values("feature_ts"),
    left_on="event_timestamp",
    right_on="feature_ts",
    by="customer_id",
    direction="backward",
    tolerance=pd.Timedelta(days=14),
)[["txn_id", "avg_amount_30d", "feature_ts"]].rename(columns={"avg_amount_30d": "expected"})
check = train.merge(expected, on="txn_id")
same = (check.avg_amount_30d.isna() & check.expected.isna()) | ((check.avg_amount_30d - check.expected).abs() < 1e-6)
print(f"Feast == independent as-of join for {same.mean():.1%} of {len(check)} rows")
future = (check.feature_ts > pd.to_datetime(check.txn_id.map(spine.set_index("txn_id").event_timestamp), utc=True)).sum()
print(f"values from the future: {future}")
print(
    "\nNote: the spine rows are transactions and the stats include the transaction itself, so the as-of\n"
    "join is inclusive of the event (see Q7). Decide if that is right for your label."
)
