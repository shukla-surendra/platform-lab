"""ON-DEMAND features and FEATURE SERVICES (Q9): models compose shared + own + request-time features.

  model_a = customer_stats + merchant_stats                      (shared views only)
  model_b = customer_stats[avg_amount_30d] + amount_vs_avg       (1 shared feature + a request-time feature)

`amount_vs_avg` needs the live `amount`, so it is computed at request time by ONE function used online and offline.

Run:  docker compose run --rm workbench python explore/04_on_demand_and_services.py
"""
import pandas as pd
from common import FEATURE_SERVER, banner, sql, store
import requests

banner("what each feature service exposes")
for name in ("model_a", "model_b"):
    fs = store.get_feature_service(name)
    print(f"{name}: {[f'{p.name}:{[f.name for f in p.features]}' for p in fs.feature_view_projections]}")

cid = int(sql("SELECT customer_id FROM customer_stats WHERE event_timestamp > now() - interval '3 days' LIMIT 1").iloc[0, 0])
amount = 100.0

banner(f"ONLINE model_b for customer {cid}, request amount={amount}")
on = store.get_online_features(features=store.get_feature_service("model_b"), entity_rows=[{"customer_id": cid, "amount": amount}]).to_dict()
print({k: v[0] for k, v in on.items()})
expected = amount / on["avg_amount_30d"][0]
print(f"amount / avg_amount_30d = {expected:.6f}   feast amount_vs_avg = {on['amount_vs_avg'][0]:.6f}   equal: {abs(expected - on['amount_vs_avg'][0]) < 1e-9}")

banner("same thing over the REST feature server")
# request-time values (the RequestSource fields) travel in `entities`, next to the join key
resp = requests.post(
    f"{FEATURE_SERVER}/get-online-features",
    json={"feature_service": "model_b", "entities": {"customer_id": [cid], "amount": [amount]}},
    timeout=10,
)
print("HTTP", resp.status_code)
body = resp.json()
print({n: r["values"][0] for n, r in zip(body["metadata"]["feature_names"], body["results"])})

banner("OFFLINE model_b: the SAME on-demand function computes the training column")
spine = pd.DataFrame({"customer_id": [cid], "event_timestamp": [pd.Timestamp.now(tz="UTC")], "amount": [amount]})
off = store.get_historical_features(entity_df=spine, features=store.get_feature_service("model_b")).to_df()
print(off.to_string(index=False))
print(f"\nonline amount_vs_avg == offline amount_vs_avg: {abs(on['amount_vs_avg'][0] - off.amount_vs_avg.iloc[0]) < 1e-6}")
