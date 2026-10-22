# Stale copies: what happens when embedded data changes (Python)

**The scenario.** `categories` is a collection where each category has several attributes
(name, path, tax rate, return days). Products embed a **copy** of the categories they belong
to, because the product page always shows them together (*"read together → store together"*).
Later a category changes: renamed, tax rate lowered. Every product holding the old copy is
now **stale**. How do you manage that in MongoDB?

5 small Python scripts, one idea each, with real output pasted at the bottom of every file.

```bash
cd dbms-exploration/mongo_explore/stale_copies
make up            # MongoDB 7 on localhost:27019
make run L=01      # run 01_the_problem.py   (uv installs pymongo on the fly)
make all           # all 5 in order
make down
```
Without make: `uv run --no-project --with-requirements requirements.txt python 01_the_problem.py`

## Files

| File | One idea | Real result |
|---|---|---|
| [01_the_problem.py](01_the_problem.py) | Rename a category; the copies don't change | **10,000** stale products |
| [02_fan_out_update.py](02_fan_out_update.py) | Update master + all copies in one transaction (`$[c]` + `array_filters`) | 10,000 fixed in 48 ms, 0 stale, other categories untouched |
| [03_snapshot_vs_live.py](03_snapshot_vs_live.py) | Some copies **must not** change (invoices) | product tax 12, invoice tax stays 18 ✅ |
| [04_embed_less.py](04_embed_less.py) | Embed only stable fields; look up volatile ones (`$lookup` / cache) | tax always fresh, 1 extra lookup |
| [05_change_stream_sync.py](05_change_stream_sync.py) | Background worker fixes copies after a change | stale for ~70 ms, then fixed |

`common.py` holds the connection and the seed data (3 categories, 20,000 products).

## Step 1: is this copy supposed to change at all?

Answer this before choosing a technique (script 03):

| Copy | Kind | Rule |
|---|---|---|
| category inside **product** | **live** | must show today's value → keep in sync |
| category/tax inside **order / invoice** | **snapshot** | must keep the value at purchase time → never update |
| author name on old **comments** | depends | product decision; often "live, but a few seconds late is fine" |

A snapshot isn't stale data, it's history. A lot of "staleness" bugs come from treating
snapshots as live copies, or live copies as snapshots.

## Step 2: pick a technique for live copies (MongoDB)

| Technique | Script | Fresh? | Read cost | Write cost | Use when |
|---|---|---|---|---|---|
| **Fan-out update in a transaction** | 02 | always | 1 read | updates **every** copy (needs index on `categories._id`) | category changes rarely, copies count is moderate (thousands to low millions) |
| **Embed less** (stable fields only) + `$lookup`/cache | 04 | always (cache: within its TTL) | +1 lookup | 1 update | the field changes often (prices, tax, stock) |
| **Background sync** (change stream / queue) | 05 | eventually (ms–seconds) | 1 read | async, off the request path | huge fan-out, and a short delay is acceptable (display names, labels) |
| **Do nothing** (snapshot) | 03 | n/a | 1 read | none | the copy is history |
| Version stamp + lazy repair | — | on read | 1 read + check | repair when found | rarely-read docs; store `categoryVersion`, refresh the copy when it's behind |

Rule of thumb: **embed what's stable, reference what changes**, and fan out the rare
changes to the stable fields (a rename).

## How is this different in Postgres?

In Postgres the category would normally be stored **once** and joined on read, so a rename
updates 1 row and nothing goes stale. Copies only exist if you add them on purpose. That side
is in its own folder: [../../pg_stale_copies/](../../pg_stale_copies/README.md).

If categories change often **and** are shared by many records, that's a sign the data is
relational. Consider Postgres, or reference instead of embed (04).
