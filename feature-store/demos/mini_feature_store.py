"""A feature store in ~100 lines, to show that there is no magic in it.

Every real product (Feast, SageMaker Feature Store, Databricks, Tecton,
Hopsworks) is these pieces with scale, durability, security and a UI:

    registry        feature definitions declared once
    offline store   full history of feature values, each with an event time
    online store    latest value per entity, key-value lookup
    point-in-time   "feature values as they were at time t"  (offline read)
    materialize     copy latest offline values into the online store
    ttl             a feature older than X is treated as missing

Here the offline store is a DataFrame and the online store is a dict.
"""
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable

import pandas as pd

NS = "datetime64[ns]"


@dataclass
class FeatureView:
    name: str
    entity_key: str  # column that identifies the entity, e.g. "customer_id"
    features: list[str]
    ttl: timedelta
    # raw data -> DataFrame[entity_key, event_ts, *features]. THE single
    # definition of the feature: both the offline and online paths use its output.
    compute: Callable[[pd.DataFrame], pd.DataFrame]


@dataclass
class MiniFeatureStore:
    views: dict[str, FeatureView] = field(default_factory=dict)
    _offline: dict[str, pd.DataFrame] = field(default_factory=dict)
    _online: dict[tuple[str, object], dict] = field(default_factory=dict)

    # ---- registry / batch computation ---------------------------------------
    def apply(self, view: FeatureView, raw: pd.DataFrame) -> None:
        """Register the view and run its transformation ONCE over the raw data."""
        table = view.compute(raw)
        table["event_ts"] = table["event_ts"].astype(NS)
        self.views[view.name] = view
        self._offline[view.name] = table.sort_values("event_ts").reset_index(drop=True)

    # ---- offline read: training sets ----------------------------------------
    def get_historical_features(self, entity_df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
        """For each (entity, event_ts) row return the latest feature values that
        were known AT OR BEFORE event_ts and not older than the view's ttl.

        `features` are "view:feature" references.
        """
        out = entity_df.copy()
        out["event_ts"] = out["event_ts"].astype(NS)
        out = out.sort_values("event_ts").reset_index(drop=True)
        for view_name, cols in _group_by_view(features).items():
            view = self.views[view_name]
            right = self._offline[view_name][[view.entity_key, "event_ts", *cols]].rename(
                columns={"event_ts": f"{view_name}__feature_ts"}
            )
            out = pd.merge_asof(
                out,
                right.sort_values(f"{view_name}__feature_ts"),
                left_on="event_ts",
                right_on=f"{view_name}__feature_ts",
                by=view.entity_key,
                direction="backward",  # never look into the future
                tolerance=view.ttl,  # too old => NaN
            )
        return out

    # ---- other offline access patterns ---------------------------------------
    def range_scan(self, view_name: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        """All feature rows with start <= event_ts < end (bulk training, backfill checks, monitoring)."""
        t = self._offline[view_name]
        return t[(t["event_ts"] >= pd.Timestamp(start)) & (t["event_ts"] < pd.Timestamp(end))]

    def snapshot(self, view_name: str, as_of: pd.Timestamp) -> pd.DataFrame:
        """Latest row per entity known at as_of, dropping values older than the ttl (batch scoring)."""
        view = self.views[view_name]
        t = self._offline[view_name]
        latest = t[t["event_ts"] <= pd.Timestamp(as_of)].groupby(view.entity_key).tail(1)
        return latest[(pd.Timestamp(as_of) - latest["event_ts"]) <= view.ttl]

    # ---- materialize: offline -> online -------------------------------------
    def materialize(self, view_name: str, up_to: pd.Timestamp) -> int:
        """Load the latest value per entity (as of `up_to`) into the online store."""
        view = self.views[view_name]
        t = self._offline[view_name]
        latest = t[t["event_ts"] <= pd.Timestamp(up_to)].groupby(view.entity_key).tail(1)
        for _, row in latest.iterrows():
            self._online[(view_name, row[view.entity_key])] = {
                "event_ts": row["event_ts"],
                **{f: row[f] for f in view.features},
            }
        return len(latest)

    # ---- streaming-style write: new values arrive one at a time -------------
    def push(self, view_name: str, rows: pd.DataFrame, to_offline: bool = True) -> None:
        """Write fresh feature values straight to the online store.

        With to_offline=True (the sane default) the same rows are also appended
        to the offline history, so training can later reproduce what serving
        saw. With to_offline=False the online store gets values the offline
        store never records — see demos/05_online_offline_writes.py.
        """
        view = self.views[view_name]
        rows = rows.copy()
        rows["event_ts"] = rows["event_ts"].astype(NS)
        if to_offline:
            new = rows[[view.entity_key, "event_ts", *view.features]]
            merged = pd.concat([self._offline[view_name], new], ignore_index=True)
            self._offline[view_name] = merged.sort_values("event_ts").reset_index(drop=True)
        for _, row in rows.iterrows():
            key = (view_name, row[view.entity_key])
            current = self._online.get(key)
            # latest event time wins; an out-of-order older value must not overwrite a newer one
            if current is None or row["event_ts"] >= current["event_ts"]:
                self._online[key] = {"event_ts": row["event_ts"], **{f: row[f] for f in view.features}}

    # ---- online read: serving ------------------------------------------------
    def get_online_features(self, features: list[str], entity_key, now: pd.Timestamp) -> dict:
        """O(1) lookup. Missing or older-than-ttl values come back as None."""
        result = {}
        for view_name, cols in _group_by_view(features).items():
            view = self.views[view_name]
            rec = self._online.get((view_name, entity_key))
            stale = rec is None or (pd.Timestamp(now) - rec["event_ts"]) > view.ttl
            for c in cols:
                result[c] = None if stale else rec[c]
        return result


def get_online_features_batch(store: "MiniFeatureStore", features: list[str], entity_keys: list, now: pd.Timestamp) -> dict:
    """Multi-get: many keys in one call (e.g. all candidate items for one ranking request)."""
    return {k: store.get_online_features(features, k, now) for k in entity_keys}


def _group_by_view(refs: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for ref in refs:
        view, feat = ref.split(":")
        grouped.setdefault(view, []).append(feat)
    return grouped
