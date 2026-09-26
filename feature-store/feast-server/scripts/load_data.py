"""Generate a small transactions dataset and load it into Postgres (the OFFLINE store).

Tables written (all timestamps are UTC, ending at "now" so TTL/freshness behave realistically):
  transactions    the spine / label table: one row per transaction, with a `label` (chargeback)
  customer_stats  feature history: 30-day avg amount + count per customer, at every transaction
  merchant_stats  feature history for a second entity (merchant)

Re-running replaces the tables.
"""
import os

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

URL = os.getenv("DATABASE_URL", "postgresql+psycopg://feast:feast@postgres:5432/feast")
N_CUSTOMERS, N_MERCHANTS, DAYS = 200, 25, 90

rng = np.random.default_rng(7)
now = pd.Timestamp.now(tz="UTC").floor("h")
start = now - pd.Timedelta(days=DAYS)

rows = []
for cid in range(N_CUSTOMERS):
    rate = rng.uniform(0.2, 1.5)  # transactions per day
    # ~15% of customers go quiet partway through, so some features go stale (TTL exploration)
    active_days = DAYS if rng.random() > 0.15 else int(DAYS * rng.uniform(0.3, 0.7))
    n = rng.poisson(rate * active_days)
    ts = start + pd.to_timedelta(rng.uniform(0, active_days, n), unit="D")
    amount = rng.lognormal(mean=3.5, sigma=0.6, size=n).round(2)
    refund = rng.random(n) < 0.10
    amount = np.where(refund, -amount, amount)
    rows.append(
        pd.DataFrame(
            {
                "customer_id": cid,
                "merchant_id": rng.integers(0, N_MERCHANTS, n),
                "event_timestamp": ts,
                "amount": amount,
            }
        )
    )

txns = pd.concat(rows, ignore_index=True).sort_values("event_timestamp").reset_index(drop=True)
txns.insert(0, "txn_id", txns.index.astype("int64"))
# synthetic label ("chargeback"): more likely for large purchases; refunds are never chargebacks
p = np.clip(0.02 + 0.002 * np.maximum(txns.amount - 60, 0), 0, 0.6)
txns["label"] = ((rng.random(len(txns)) < p) & (txns.amount > 0)).astype("int64")


def rolling_stats(df: pd.DataFrame, key: str, avg: str, cnt: str) -> pd.DataFrame:
    """Trailing 30-day avg + count of positive amounts, evaluated at every transaction time."""
    d = df[df.amount > 0].set_index("event_timestamp").sort_index()
    g = d.groupby(key)["amount"].rolling("30D")
    out = pd.DataFrame({avg: g.mean(), cnt: g.count().astype("int64")}).reset_index()
    out["created"] = now  # ingestion time, separate from event time (bitemporal-style)
    return out


customer_stats = rolling_stats(txns, "customer_id", "avg_amount_30d", "txn_count_30d")
merchant_stats = rolling_stats(txns, "merchant_id", "merch_avg_30d", "merch_txn_30d")

engine = create_engine(URL)
with engine.begin() as conn:
    for name, df in [("transactions", txns), ("customer_stats", customer_stats), ("merchant_stats", merchant_stats)]:
        df.to_sql(name, conn, if_exists="replace", index=False, chunksize=5000)
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_txn_ts ON transactions (event_timestamp)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cust_stats ON customer_stats (customer_id, event_timestamp)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_merch_stats ON merchant_stats (merchant_id, event_timestamp)"))

print(
    f"loaded: transactions={len(txns)} customer_stats={len(customer_stats)} merchant_stats={len(merchant_stats)} "
    f"window={start:%Y-%m-%d}..{now:%Y-%m-%d %H:%M} UTC"
)
