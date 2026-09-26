"""FEATURE EVOLUTION: drop a feature, keep old models working via pinned versions (Q12 in ../../doubt.md).

Uses a throwaway feature view `evolution_demo` (deleted at the end); the lab's real views are untouched.
Needs `enable_online_feature_view_versioning: true` under `registry` in feature_store.yaml (already set).

Run:  docker compose run --rm workbench python explore/05_feature_versions.py
"""
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
from common import banner, store
from feast import FeatureView, Field
from feast.types import Float64, Int64

sys.path.insert(0, "/app/feature_repo")
from feature_definitions import customer, customer_source  # noqa: E402

NAME = "evolution_demo"


def make_view(fields):
    return FeatureView(name=NAME, entities=[customer], ttl=timedelta(days=14), schema=fields,
                       source=customer_source, online=True, version="latest")


def try_read(ref: str, cid: int = 0) -> str:
    spine = pd.DataFrame({"customer_id": [cid], "event_timestamp": [pd.Timestamp.now(tz="UTC")]})
    out = []
    for kind, fn in (
        ("offline", lambda: store.get_historical_features(entity_df=spine, features=[ref]).to_df().iloc[0, -1]),
        ("online ", lambda: store.get_online_features(features=[ref], entity_rows=[{"customer_id": cid}]).to_dict()[ref.split(":")[1]][0]),
    ):
        try:
            out.append(f"{kind}={fn()}")
        except Exception as e:  # noqa: BLE001
            out.append(f"{kind}=FAILS({type(e).__name__})")
    return "  ".join(out)


v1 = None
try:
    banner("day 0: the model is trained on evolution_demo with 2 features")
    v0 = make_view([Field(name="avg_amount_30d", dtype=Float64), Field(name="txn_count_30d", dtype=Int64)])
    store.apply([v0])
    now = datetime.now(timezone.utc)
    store.materialize(now - timedelta(days=30), now, feature_views=[NAME])
    print("versions:", [v["version"] for v in store.list_feature_view_versions(NAME)])

    banner("re-applying an unchanged definition does not create a version")
    store.apply([v0])
    print("versions:", [v["version"] for v in store.list_feature_view_versions(NAME)])

    banner("day 30: txn_count_30d is DROPPED from the definition")
    v1 = make_view([Field(name="avg_amount_30d", dtype=Float64)])
    store.apply([v1])
    print("versions:", [v["version"] for v in store.list_feature_view_versions(NAME)])
    print("current features:", [f.name for f in store.get_feature_view(NAME).features])

    banner("who can still read the dropped feature?")
    print(f"{'evolution_demo:txn_count_30d':<36} (unpinned: 'latest')   {try_read('evolution_demo:txn_count_30d')}")
    print(f"{'evolution_demo@v0:txn_count_30d':<36} (pinned to v0)        {try_read('evolution_demo@v0:txn_count_30d')}")
    print(f"{'evolution_demo@v1:avg_amount_30d':<36} (pinned to v1)        {try_read('evolution_demo@v1:avg_amount_30d')}")
    print(
        "\nRead it: the unpinned reference breaks (the in-place failure from demo 10), the v0 pin keeps the old model working.\n"
        "The v1 online value is None because each version has its OWN online data: v1 was never materialized.\n"
        "=> pin the feature version in the model's feature spec, and materialize every version that a live model uses."
    )
finally:
    if v1 is not None:
        store.apply([], objects_to_delete=[v1], partial=False)
    print("\ncleanup: removed the throwaway view; remaining views:", [f.name for f in store.list_feature_views()])
