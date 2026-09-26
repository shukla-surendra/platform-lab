"""ONLINE: key lookups through the Python SDK and the REST feature server; peek at Redis (Q4, Q11).

Run:  docker compose run --rm workbench python explore/02_online_get.py
"""
import redis
import requests
from common import FEATURE_SERVER, banner, sql, store

FEATS = ["customer_stats:avg_amount_30d", "customer_stats:txn_count_30d"]

banner("single-key get + multi-get via the Python SDK")
active = sql("SELECT DISTINCT customer_id FROM customer_stats WHERE event_timestamp > now() - interval '7 days' LIMIT 3")
ids = [int(x) for x in active.customer_id] + [99999]  # 99999 does not exist
out = store.get_online_features(features=FEATS, entity_rows=[{"customer_id": i} for i in ids]).to_dict()
for i, avg, cnt in zip(out["customer_id"], out["avg_amount_30d"], out["txn_count_30d"]):
    print(f"customer {i:>5}: avg_amount_30d={avg}  txn_count_30d={cnt}")
print("-> a key with no value comes back as None: the model needs a default/missing path (Q5, Q11)")

banner("same lookup over REST: POST /get-online-features")
resp = requests.post(
    f"{FEATURE_SERVER}/get-online-features",
    json={"features": FEATS, "entities": {"customer_id": ids}},
    timeout=10,
).json()
names = resp["metadata"]["feature_names"]
cols = {n: r["values"] for n, r in zip(names, resp["results"])}
for i, avg in zip(cols["customer_id"], cols["avg_amount_30d"]):
    print(f"customer {i:>5}: avg_amount_30d={avg}")
print("REST == SDK:", [round(x, 6) if x is not None else None for x in cols["avg_amount_30d"]]
      == [round(x, 6) if x is not None else None for x in out["avg_amount_30d"]])

banner("what Redis actually holds")
r = redis.Redis(host="redis", port=6379)
print("keys in Redis:", r.dbsize(), "= one hash per ENTITY KEY (a customer or a merchant), latest values only, no history")
key = next(r.scan_iter(count=100))
print("sample key (binary-serialised entity key):", key[:24], "...  hash fields:", len(r.hgetall(key)))
print("Redis key TTL:", r.ttl(key), "(-1 = no Redis expiry; the feature ttl is a Feast concept, not a Redis expiry)")

banner("which customers have NO value online?")
all_ids = [int(x) for x in sql("SELECT DISTINCT customer_id FROM customer_stats ORDER BY 1").customer_id]
res = store.get_online_features(features=FEATS[:1], entity_rows=[{"customer_id": i} for i in all_ids]).to_dict()
missing = [i for i, v in zip(res["customer_id"], res["avg_amount_30d"]) if v is None]
print(f"customers in offline history: {len(all_ids)};  with an online value: {len(all_ids) - len(missing)};  missing: {len(missing)}")
print("missing = went quiet before the 30-day materialization window, so materialize never copied them (cold start / inactive)")
