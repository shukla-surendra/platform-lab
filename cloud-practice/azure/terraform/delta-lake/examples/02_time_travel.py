# /// script
# requires-python = ">=3.11"
# dependencies = ["deltalake", "pandas", "pyarrow"]
# ///
"""Time travel: read the table as it existed at an earlier version,
side-by-side with the latest. This works because every version's files are
still sitting in storage -- "reading version 0" just means "only look at
the files version 0's commit said existed," ignoring files added later.

    uv run 02_time_travel.py
"""

import os

import pandas as pd
from deltalake import DeltaTable, write_deltalake

account = os.environ["STORAGE_ACCOUNT_NAME"]
key = os.environ["STORAGE_ACCOUNT_KEY"]
filesystem = os.environ["FILESYSTEM_NAME"]

storage_options = {
    "azure_storage_account_name": account,
    "azure_storage_account_key": key,
}
table_uri = f"abfss://{filesystem}@{account}.dfs.core.windows.net/orders_timetravel"

# Build a fresh 3-version table so this script works standalone, in any order.
write_deltalake(
    table_uri,
    pd.DataFrame({"order_id": [1, 2], "status": ["pending", "pending"]}),
    storage_options=storage_options,
    mode="overwrite",
)
write_deltalake(
    table_uri,
    pd.DataFrame({"order_id": [3, 4, 5], "status": ["pending"] * 3}),
    storage_options=storage_options,
    mode="append",
)
write_deltalake(
    table_uri,
    pd.DataFrame({"order_id": [6], "status": ["cancelled"]}),
    storage_options=storage_options,
    mode="append",
)
print("Built orders_timetravel: v0 (2 rows) -> v1 (+3 rows) -> v2 (+1 row)\n")

for version in (0, 1, 2):
    dt = DeltaTable(table_uri, storage_options=storage_options, version=version)
    df = dt.to_pandas()
    print(f"Reading AS OF version {version}: {len(df)} rows -> "
          f"order_ids {sorted(df['order_id'].tolist())}")

latest = DeltaTable(table_uri, storage_options=storage_options)
print(f"\nReading latest (no version pinned): {len(latest.to_pandas())} rows "
      f"-> version {latest.version()}")

# The point: version 0's read is completely unaffected by everything
# written after it. No row was ever mutated or deleted to make this work --
# each version is a *view* over an append-only set of files plus the
# transaction log's record of which files belonged to which version.
v0_rows = len(DeltaTable(table_uri, storage_options=storage_options, version=0).to_pandas())
assert v0_rows == 2, "version 0 must still show exactly its original 2 rows"
print("\nconfirmed: version 0's read is unchanged by writes that happened "
      "after it -- this is what makes 'query the table as of yesterday' or "
      "'reproduce the exact input a training job saw' possible without a "
      "separate snapshot/backup system.")
