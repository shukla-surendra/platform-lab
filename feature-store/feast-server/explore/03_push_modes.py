"""PUSH: do pushed feature rows also land in the offline store? (Q4 in ../../doubt.md)

Feast has three push modes:
    PushMode.ONLINE              -> online store only
    PushMode.OFFLINE             -> offline store only
    PushMode.ONLINE_AND_OFFLINE  -> both
BUT the offline modes need an offline store that implements `offline_write_batch`. In Feast 0.66 the
Postgres offline store does NOT (the file/Dask store does). This lab uses Postgres, so this script shows:
  1. ONLINE-only push  -> the skew trap (served value never reaches history)
  2. the offline modes raising NotImplementedError on this backend
  3. the workaround: write the row to the offline table yourself, then push ONLINE  (a manual dual write)

Run:  docker compose run --rm workbench python explore/03_push_modes.py
(Each run appends rows to customer_stats; `docker compose up -d --force-recreate feast-init` reloads clean data.)
"""
import pandas as pd
from common import banner, engine, sql, store
from feast.data_source import PushMode

FEAT = ["customer_stats_fresh:avg_amount_30d"]

active = sql("SELECT DISTINCT customer_id FROM customer_stats WHERE event_timestamp > now() - interval '5 days' ORDER BY 1 LIMIT 2")
c_trap, c_dual = (int(x) for x in active.customer_id)
now = pd.Timestamp.now(tz="UTC")
# a fresh value every run, so re-running the script always shows a real before -> after change
STAMP = round(100 + (now.timestamp() % 100), 2)


def row(cid: int, avg: float) -> pd.DataFrame:
    return pd.DataFrame(
        {"customer_id": [cid], "event_timestamp": [now], "created": [now], "avg_amount_30d": [avg], "txn_count_30d": [9]}
    )


def online(cid: int) -> float:
    return store.get_online_features(features=FEAT, entity_rows=[{"customer_id": cid}]).to_dict()["avg_amount_30d"][0]


def offline(cid: int) -> float:
    spine = pd.DataFrame({"customer_id": [cid], "event_timestamp": [now + pd.Timedelta(minutes=1)]})
    return store.get_historical_features(entity_df=spine, features=FEAT).to_df().avg_amount_30d.iloc[0]


banner(f"1. ONLINE-only push for customer {c_trap} (the trap)")
b_on, b_off = online(c_trap), offline(c_trap)
store.push("customer_stats_push", row(c_trap, STAMP), to=PushMode.ONLINE)
print(f"online : {b_on:.2f} -> {online(c_trap):.2f}   (serving sees the new value)")
print(f"offline: {b_off:.2f} -> {offline(c_trap):.2f}   (a training set as of now does NOT contain it)")
print(f"=> served value {STAMP:.2f}, reproducible training value {offline(c_trap):.2f} = silent skew created by the write path")

banner("2. the offline push modes on this backend")
for mode in (PushMode.ONLINE_AND_OFFLINE, PushMode.OFFLINE):
    try:
        store.push("customer_stats_push", row(c_dual, STAMP + 1000), to=mode)
        print(f"{mode.name}: worked")
    except NotImplementedError:
        print(f"{mode.name}: NotImplementedError -> the Postgres offline store cannot write pushed rows in this Feast version")

banner(f"3. workaround: manual dual write for customer {c_dual} (offline row via SQL, then push ONLINE)")
row(c_dual, STAMP + 1000).to_sql("customer_stats", engine, if_exists="append", index=False)  # 1) history
store.push("customer_stats_push", row(c_dual, STAMP + 1000), to=PushMode.ONLINE)  # 2) serving
print(f"online : {online(c_dual):.2f}")
print(f"offline: {offline(c_dual):.2f}")
print(f"consistent: {abs(online(c_dual) - offline(c_dual)) < 1e-9}")
print(
    "\nTakeaway: the dual write is a property of your BACKEND and write path, not of 'having a feature store'.\n"
    "With Postgres you own it (ideally as one transaction/pipeline step); with a backend that implements\n"
    "offline_write_batch (e.g. Feast's file store) PushMode.ONLINE_AND_OFFLINE does it for you."
)
