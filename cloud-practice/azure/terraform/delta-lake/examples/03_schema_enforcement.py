# /// script
# requires-python = ">=3.11"
# dependencies = ["deltalake", "pandas", "pyarrow"]
# ///
"""Schema enforcement (the default) vs. schema evolution (opt-in). A plain
Parquet-files-in-a-folder "table" has no concept of a schema at all -- any
writer can drop in a file with whatever columns it wants, and readers only
find out something's wrong when a query breaks. Delta Lake tracks the
schema in its transaction log and checks every write against it.

    uv run 03_schema_enforcement.py
"""

import os

import pandas as pd
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError

account = os.environ["STORAGE_ACCOUNT_NAME"]
key = os.environ["STORAGE_ACCOUNT_KEY"]
filesystem = os.environ["FILESYSTEM_NAME"]

storage_options = {
    "azure_storage_account_name": account,
    "azure_storage_account_key": key,
}
table_uri = f"abfss://{filesystem}@{account}.dfs.core.windows.net/products"

write_deltalake(
    table_uri,
    pd.DataFrame({"product_id": [1, 2], "name": ["widget", "gadget"], "price": [9.99, 19.99]}),
    storage_options=storage_options,
    mode="overwrite",
)
print("Created products table: product_id (int), name (str), price (float)\n")

print("Attempt 1: append a row with an extra, unexpected column "
      "('discontinued')...")
bad_batch = pd.DataFrame({
    "product_id": [3],
    "name": ["thingamajig"],
    "price": [29.99],
    "discontinued": [True],
})
try:
    write_deltalake(table_uri, bad_batch, storage_options=storage_options, mode="append")
    print("  (unexpectedly succeeded)")
except (SchemaMismatchError, DeltaError, ValueError) as e:
    print(f"  REJECTED as expected: {type(e).__name__}: {e}")
    print("  Why: the table's schema (from its transaction log) has 3 "
          "columns. This batch has 4. Delta Lake checks the incoming "
          "Arrow schema against the table's committed schema *before* "
          "writing any data file -- a bare Parquet-files-in-a-folder "
          "table has no such check; a bad batch would just silently sit "
          "there until something downstream broke reading it.")

print()
print("Attempt 2: same extra column, but explicitly opt in to schema "
      "evolution (mergeSchema)...")
write_deltalake(
    table_uri,
    bad_batch,
    storage_options=storage_options,
    mode="append",
    schema_mode="merge",
)
dt = DeltaTable(table_uri, storage_options=storage_options)
df = dt.to_pandas()
print(f"  succeeded -- table now has columns: {list(df.columns)}")
print(df.sort_values("product_id").to_string(index=False))

assert "discontinued" in df.columns
assert df.loc[df["product_id"].isin([1, 2]), "discontinued"].isna().all(), (
    "pre-existing rows should get a null for the new column, not an error"
)
print("\nconfirmed: schema changes are always explicit (schema_mode='merge'), "
      "never silent -- and rows written before the new column existed get "
      "null for it rather than the table becoming unreadable.")
