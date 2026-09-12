"""Explore the three files Feast actually keeps on disk in feature_repo/data/.

Not part of the pipeline (data.py/train.py/etc.) -- a standalone debugging
tool for answering "what's actually in there" the way you might reach for
`sqlite3`/`pandas.read_parquet` directly, but with the online store's
protobuf-encoded values already decoded (raw SQLite access can't do that --
see the "online store (raw SQLite)" section below for what that looks like
un-decoded).

Usage:
    uv run python scripts/explore_feature_store.py                    # everything
    uv run python scripts/explore_feature_store.py --ip 185.75.225.22 # + one IP's values
"""

from __future__ import annotations

import argparse
import sqlite3

import pandas as pd

from fraud_detection.feast_features import (
    FEATURE_REPO_PATH,
    IP_VELOCITY_SOURCE_PATH,
    apply_feast_repo,
    get_online_ip_features,
)


def show_offline_store() -> None:
    print("\n=== Offline store: ip_velocity_stats.parquet ===")
    if not IP_VELOCITY_SOURCE_PATH.exists():
        print(f"Not found at {IP_VELOCITY_SOURCE_PATH} -- run train_with_feast.py first.")
        return

    df = pd.read_parquet(IP_VELOCITY_SOURCE_PATH)
    print(f"{len(df):,} rows, columns: {list(df.columns)}")
    print(df.describe(include="all").T)

    reused = df[df["ip_prior_txn_count"] > 0]
    print(f"\n{len(reused):,} rows where an IP had prior history (out of {len(df):,} total)")
    print("Top 5 IPs by max prior_txn_count seen:")
    print(
        df.groupby("ip_address")["ip_prior_txn_count"]
        .max()
        .sort_values(ascending=False)
        .head(5)
    )


def show_online_store_raw() -> None:
    """What you'd see hitting the SQLite file directly, no Feast involved --
    deliberately shown un-decoded, since that's the honest answer to
    "can I just query this with sqlite3": structurally yes, but entity_key
    and value are protobuf BLOBs, not plain SQL types."""
    print("\n=== Online store (raw SQLite, undecoded) ===")
    db_path = FEATURE_REPO_PATH / "data" / "online_store.db"
    if not db_path.exists():
        print(f"Not found at {db_path} -- run train_with_feast.py first.")
        return

    conn = sqlite3.connect(db_path)
    tables = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    ]
    print(f"Tables: {tables}")

    table = next((t for t in tables if "ip_velocity_stats" in t), None)
    if table:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count:,} rows")
        rows = conn.execute(
            f"SELECT feature_name, event_ts FROM {table} LIMIT 5"
        ).fetchall()
        print("Sample rows (entity_key/value omitted -- protobuf BLOBs, not text):")
        for feature_name, event_ts in rows:
            print(f"  {feature_name:<25} event_ts={event_ts}")
    conn.close()


def show_registry() -> None:
    print("\n=== Registry: entities, feature views, feature services ===")
    store = apply_feast_repo()
    for entity in store.list_entities():
        print(f"Entity: {entity.name} (join_key={entity.join_key}, type={entity.value_type})")
    for fv in store.list_feature_views():
        print(f"FeatureView: {fv.name} -> {[f.name for f in fv.schema]}")
    for fs in store.list_feature_services():
        print(f"FeatureService: {fs.name}")


def show_online_decoded(ip_address: str) -> None:
    print(f"\n=== Online store (decoded via Feast) for ip_address={ip_address} ===")
    store = apply_feast_repo()
    values = get_online_ip_features(store, ip_address)
    for name, value in values.items():
        print(f"  {name:<25} {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ip", help="Also look up this IP's decoded online-store values (e.g. 185.75.225.22)"
    )
    args = parser.parse_args()

    show_offline_store()
    show_online_store_raw()
    show_registry()
    if args.ip:
        show_online_decoded(args.ip)
    else:
        print(
            "\n(pass --ip <address> to also see decoded online-store values for a "
            "specific IP, e.g. --ip 185.75.225.22)"
        )


if __name__ == "__main__":
    main()
