# /// script
# requires-python = ">=3.11"
# dependencies = ["deltalake", "pandas", "pyarrow", "azure-storage-blob"]
# ///
"""The payoff: Delta Lake's ACID guarantee isn't a database engine holding
locks -- it's an ordered, append-only log of small JSON commit files, one
per version, sitting right next to the data as plain blobs. This script
writes a table, then reads that log directly with the plain Blob SDK (no
Delta library involved) to make the mechanism concrete.

    uv run 04_inspect_transaction_log.py
"""

import json
import os

import pandas as pd
from azure.storage.blob import BlobServiceClient
from deltalake import write_deltalake

account = os.environ["STORAGE_ACCOUNT_NAME"]
key = os.environ["STORAGE_ACCOUNT_KEY"]
filesystem = os.environ["FILESYSTEM_NAME"]

storage_options = {
    "azure_storage_account_name": account,
    "azure_storage_account_key": key,
}
table_path = "txlog_demo"
table_uri = f"abfss://{filesystem}@{account}.dfs.core.windows.net/{table_path}"

write_deltalake(
    table_uri,
    pd.DataFrame({"event_id": [1, 2], "kind": ["click", "click"]}),
    storage_options=storage_options,
    mode="overwrite",
)
write_deltalake(
    table_uri,
    pd.DataFrame({"event_id": [3], "kind": ["purchase"]}),
    storage_options=storage_options,
    mode="append",
)
print("Wrote 2 versions to txlog_demo.\n")

# HNS being on doesn't stop the plain Blob API from listing/reading these
# files -- every ADLS Gen2 path is also addressable as a blob. This is
# deliberately NOT using the deltalake library below, to prove the log is
# just... files.
blob_service = BlobServiceClient(
    account_url=f"https://{account}.blob.core.windows.net",
    credential=key,
)
container = blob_service.get_container_client(filesystem)

log_prefix = f"{table_path}/_delta_log/"
log_blobs = sorted(b.name for b in container.list_blobs(name_starts_with=log_prefix))
print(f"Files under {log_prefix}:")
for name in log_blobs:
    print(f"  {name}")

first_commit_name = log_blobs[0]  # "00000000000000000000.json" -- version 0
print(f"\nRaw contents of {first_commit_name} (version 0's commit, "
      f"one JSON object per line):")
raw = container.download_blob(first_commit_name).readall().decode()
for line in raw.strip().splitlines():
    obj = json.loads(line)
    action = next(iter(obj))  # "metaData", "add", "protocol", "commitInfo"...
    print(f"  [{action}] {json.dumps(obj[action])[:160]}")

print(
    "\nWhat this proves: version 0's commit records the table's schema "
    "(metaData) and exactly which Parquet file(s) now belong to the table "
    "(add, with a path and row/byte stats) -- nothing about *how* to read "
    "the data, just *which files are authoritative as of this version*. "
    "Version 1 exists as 00000000000000000001.json, itself just one more "
    "'add' entry for one more file -- the log is append-only, one file per "
    "version, and a version is only considered committed once its numbered "
    "JSON file exists. Two concurrent writers racing for version N both "
    "try to create the *same* filename; storage's atomic "
    "create-if-not-exists semantics let exactly one of them win, and the "
    "loser detects the conflict and either retries as version N+1 or "
    "fails outright. That single mechanic -- 'exactly one writer can "
    "successfully create file N' -- is the entire ACID guarantee, no "
    "database, no lock manager, no coordinator process."
)

assert len(log_blobs) == 2
assert log_blobs[0].endswith("00000000000000000000.json")
assert log_blobs[1].endswith("00000000000000000001.json")
print("\nconfirmed: exactly one numbered JSON commit file per version, "
      "found via the plain Blob API -- the transaction log really is just "
      "files, not a hidden service.")
