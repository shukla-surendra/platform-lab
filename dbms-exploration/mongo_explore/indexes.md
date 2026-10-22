# Indexes — decision matrix

Numbers in this file come from scripts 03–06 on the 300,000-order collection.

## How to read `explain()` (the only 4 things you need)

```js
db.orders.find({ userId: 42 }).explain("executionStats")
```
| Look at | Good | Bad |
|---|---|---|
| stage | `IXSCAN`, `IDHACK`, `PROJECTION_COVERED` | `COLLSCAN` (read every doc), `SORT` (sorted in memory) |
| `totalKeysExamined` | ≈ `nReturned` | ≫ `nReturned` (walked lots of index for nothing) |
| `totalDocsExamined` | ≈ `nReturned` (0 if covered) | ≫ `nReturned` |
| `executionTimeMillis` | small | grows with collection size |

Golden ratio: **keys ≈ docs ≈ returned**.

## Which index for which query

| Your query looks like | Index to create | Type | Proof |
|---|---|---|---|
| `{ userId: 42 }` | `{ userId: 1 }` | single field | 300,000 docs → 300 docs, 47 ms → 1 ms (03) |
| `{ userId: 42, total: {$gt: 1000} }` sorted by `createdAt` | `{ userId: 1, createdAt: -1, total: 1 }` | compound, **ESR order** | keys 240 + in-memory SORT → keys 25, no SORT (04) |
| `{ tags: "sale" }` where `tags` is an array | `{ tags: 1 }` | multikey (automatic for arrays) | (05) |
| only asks for fields that are all in the index | `{ userId: 1, status: 1 }` + projection without `_id` | covered | docs read = **0** (05) |
| always filters one specific value, e.g. `status: "pending"` | `{ createdAt: 1 }, { partialFilterExpression: { status: "pending" } }` | partial | indexes only the 25% pending docs: 844 KB (05) |
| "must be unique" (email) | `{ email: 1 }, { unique: true }` | unique | |
| delete docs automatically after N seconds (sessions, OTPs, logs) | `{ createdAt: 1 }, { expireAfterSeconds: 3600 }` | TTL | |
| word search in text | `{ title: "text" }`, or Atlas Search for real search | text | |
| "near me" | `{ location: "2dsphere" }` | geo | |
| unknown/user-defined field names (`attrs.*`) | `{ "attrs.$**": 1 }` | wildcard | |
| shard key spread evenly | `{ userId: "hashed" }` | hashed | |

## The ESR rule (compound index field order)

```
{ Equality fields , Sort fields , Range fields }
   userId: 42        createdAt: -1   total: {$gt: 1000}
```
- **E first:** narrows to one small slice of the index.
- **S next:** inside that slice, entries are already in sort order → no in-memory SORT.
- **R last:** a range in the middle would break the sort order of everything after it.

**Prefix rule:** `{a, b, c}` also serves queries on `{a}` and `{a, b}`, but **not** `{b}` or
`{c}` alone (script 04: a `createdAt`-only query did a COLLSCAN of 217,461 docs).

## What's fast, what's slow

| ✅ Fast | ❌ Slow | Why |
|---|---|---|
| `_id` lookup (`IDHACK`) | — | special fastest path |
| equality on indexed field | same query, no index (`COLLSCAN`) | 300 vs 300,000 docs read |
| `/^user99/` (anchored regex) | `/99/` (contains) | prefix = index range; contains = read every key (11 vs 1000 keys) |
| `$in: [a, b, c]` on selective field | `$ne`, `$nin`, `$not` | negation matches most docs; index + fetch was **96 ms vs 53 ms** for a plain full scan |
| keyset paging: `createdAt > lastSeen` | `skip(200000)` | skip still walks 200,020 keys (33 ms vs 0 ms) |
| sort on indexed field | sort on unindexed field (`SORT` stage) | 300,000 docs into memory; >100 MB fails without `allowDiskUse` |
| covered query | fetching full docs you don't need | covered reads 0 docs |
| small docs | huge docs (big embedded arrays) | 50 reads: 14 ms vs 2,541 ms (08) |
| `$match` first in a pipeline | `$match` after `$group`/`$unwind` | only a first-stage `$match` can use an index |

## Cost side of indexes (don't index everything)

- Every index slows **every write** (insert/update/delete must update it too) and uses RAM.
  Your working set (hot data + indexes) should fit in RAM.
- An index on a **low-cardinality** field alone (`status` with 4 values) rarely helps;
  combine it with a selective field or use a partial index.
- Find unused indexes: `db.orders.aggregate([{ $indexStats: {} }])` (look at `accesses.ops`).
- Build on a live system: index builds are online since 4.2, but still use CPU/IO; do it
  off-peak.
