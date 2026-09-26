"""Synthetic transaction data shared by the demos (seeded, so output is reproducible)."""
import numpy as np
import pandas as pd

START = pd.Timestamp("2026-01-01")


def make_transactions(n_customers: int = 200, days: int = 90, seed: int = 7) -> pd.DataFrame:
    """One row per transaction: customer_id, ts, amount (negative = refund).

    Customers differ in activity level, and ~15% go quiet for the last
    stretch of the window (so TTL / staleness has something to bite on).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for cid in range(n_customers):
        rate = rng.uniform(0.2, 1.5)  # transactions per day
        active_days = days if rng.random() > 0.15 else int(days * rng.uniform(0.3, 0.7))
        n = rng.poisson(rate * active_days)
        ts = START + pd.to_timedelta(rng.uniform(0, active_days, n), unit="D")
        amount = rng.lognormal(mean=3.5, sigma=0.6, size=n).round(2)
        refund = rng.random(n) < 0.10
        amount = np.where(refund, -amount, amount)
        rows.append(pd.DataFrame({"customer_id": cid, "ts": ts, "amount": amount}))
    df = pd.concat(rows, ignore_index=True)
    return df.sort_values("ts").reset_index(drop=True)
