# /// script
# requires-python = ">=3.11"
# dependencies = ["deltalake", "pandas", "pyarrow"]
# ///
"""The basics: create a Delta table, append to it, and see that each write
is a new, numbered *version* -- nothing is overwritten in place, even
though it looks like one growing table when you just read the latest data.

Needs STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY, FILESYSTEM_NAME in the
environment (see README.md "Run the demos"):
    uv run 01_create_and_append.py
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
table_uri = f"abfss://{filesystem}@{account}.dfs.core.windows.net/orders"

print(f"Table URI: {table_uri}\n")

# Version 0: the table doesn't exist yet -- "overwrite" on a nonexistent
# path just creates it. This also resets the demo to a clean state if
# you've run this script before.
initial = pd.DataFrame({
    "order_id": [1, 2, 3],
    "status": ["pending", "pending", "shipped"],
})
write_deltalake(table_uri, initial, storage_options=storage_options, mode="overwrite")
print("Wrote version 0 (3 rows, mode=overwrite -- creates the table).")

# Version 1: append. This does NOT touch the 3 rows already there -- it
# adds one new Parquet file to the table's directory and records a new
# commit that says "the table now also includes this file."
more_orders = pd.DataFrame({
    "order_id": [4, 5],
    "status": ["pending", "pending"],
})
write_deltalake(table_uri, more_orders, storage_options=storage_options, mode="append")
print("Wrote version 1 (2 more rows, mode=append).\n")

dt = DeltaTable(table_uri, storage_options=storage_options)
print(f"Current table version: {dt.version()}")
print(f"Current row count: {len(dt.to_pandas())}")
print(dt.to_pandas().sort_values("order_id").to_string(index=False))

print("\nFull commit history (one entry per version, oldest first):")
for entry in reversed(dt.history()):
    print(f"  v{entry['version']}: {entry['operation']} "
          f"({entry['operationParameters']}) "
          f"-> {entry['operationMetrics'].get('num_added_rows', '?')} rows added")

assert dt.version() == 1
assert len(dt.to_pandas()) == 5
print("\nconfirmed: 2 versions exist, latest read returns all 5 rows, "
      "nothing was overwritten -- the append only ever *added* a file.")
