# Shared data that changes: how Postgres handles it (Python)

**The scenario.** Categories have several attributes (name, path, tax rate, return days).
Each product belongs to 1–2 categories. Later a category changes: "Phones" is renamed and its
tax drops from 18% to 12%. Who sees the old values, and who should?

This is the Postgres side of [mongo_explore/stale_copies/](../mongo_explore/stale_copies/README.md),
where MongoDB embeds category copies in every product and has to keep them in sync.

```bash
cd dbms-exploration/pg_stale_copies
make up            # Postgres 16 on localhost:5435
make all           # run 01 -> 02 -> 03 (each builds on the previous one)
make down
```
Without make: `uv run --no-project --with-requirements requirements.txt python 01_normalized.py`

## Files

| File | One idea | Real result |
|---|---|---|
| [01_normalized.py](01_normalized.py) | Store the category once; products point to it via a link table (many-to-many); JOIN on read | rename = **1 row** updated, every product page shows the new name |
| [02_snapshot_history.py](02_snapshot_history.py) | The invoice copies the tax at purchase time (snapshot); a trigger fills a history table | invoice keeps 18; "category as of order date" → `Phones, 18` |
| [03_denormalized_copy.py](03_denormalized_copy.py) | If you copy for speed anyway: trigger (always fresh) vs materialized view (stale until `REFRESH`) | trigger adds 51 ms per category update; view shows old value until refreshed |

`common.py` holds the connection.

## The idea in three lines

1. **Live data lives in one place** (01). Nothing can go stale, because nothing is copied.
2. **Copies are only for history** (02): an invoice must keep the old tax. That's correct, not stale.
3. **If you copy for speed** (03), make the database keep the copy in sync (trigger, same
   transaction), or accept it's stale until the next refresh (materialized view).

## Which tool when

| Need | Tool | Fresh? | Cost |
|---|---|---|---|
| show current category on product page | normalized tables + JOIN (01) | always | a join on each read (cheap with indexes) |
| invoice must keep old values | snapshot columns (02) | intentionally old | a few extra columns |
| "what was it on date X?" | history table + trigger, `valid_from/valid_to` (02) | n/a | one insert per change |
| very hot read path, avoid joins | trigger-maintained copy (03 A) | always | every category update rewrites all copies |
| reports/listings, slightly old is OK | materialized view (03 B) | until `REFRESH` | refresh on a schedule (`REFRESH ... CONCURRENTLY` avoids blocking reads; needs a unique index on the view) |
