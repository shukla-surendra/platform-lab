# MongoDB exploration, in small steps

**10 runnable scripts** (one idea each, real output pasted at the bottom of every file) +
**4 short concept docs**. Everything runs against a 300,000-order fake shop.

```bash
cd dbms-exploration/mongo_explore
make up            # start MongoDB 7 (localhost:27018) + load the data
make run L=03      # run lesson 03_*.js
make shell         # interactive shell
make down          # stop when finished
```

**New here? Read [HOW_TO_USE.md](HOW_TO_USE.md) first.** It covers the study loop, how to
read the output lines, playing in the shell, writing your own script, connecting with
Compass, and troubleshooting.

## Files

**Scripts** (run in order; each prints its own result):

| File | One idea |
|---|---|
| [01_document_model.js](01_document_model.js) | A document = the whole receipt in one JSON object; dot-notation queries |
| [02_update_operators.js](02_update_operators.js) | `$inc`, `$set`, `$push`, upsert: atomic updates on one document |
| [03_index_basics.js](03_index_basics.js) | No index → reads all 300,000 docs (47 ms); with index → 300 docs (1 ms) |
| [04_compound_index_esr.js](04_compound_index_esr.js) | Field **order** in a compound index: the ESR rule |
| [05_covered_multikey_partial.js](05_covered_multikey_partial.js) | Covered queries (0 docs read), array indexes, partial indexes |
| [06_slow_vs_fast.js](06_slow_vs_fast.js) | Regex, `$ne`, `skip()` pagination, unindexed sort: slow versions vs fast versions |
| [07_aggregation.js](07_aggregation.js) | The pipeline = Mongo's `GROUP BY` / `JOIN` |
| [08_schema_embed_vs_reference.js](08_schema_embed_vs_reference.js) | Embed vs reference, measured; hitting the 16 MB document limit |
| [09_transactions.js](09_transactions.js) | Single-doc atomicity, multi-doc transactions, write conflicts |
| [10_access_pattern_design.js](10_access_pattern_design.js) | A full app designed from its queries; every query proven indexed |

**Concept docs** (read after the scripts, or on their own):

| File | Answers |
|---|---|
| [schema_design.md](schema_design.md) | How is a Mongo schema designed? Embed or reference? Design patterns, anti-patterns |
| [access_patterns.md](access_patterns.md) | The step-by-step method: queries first, then documents, then indexes |
| [indexes.md](indexes.md) | Index decision matrix: which index type for which query; what's fast, what's slow |
| [postgres_vs_mongo.md](postgres_vs_mongo.md) | Side-by-side comparison + "when to use what" decision matrix |
| [doubt.md](doubt.md) | Your questions + answers, as you ask them |
| [stale_copies/](stale_copies/README.md) | **Python track:** embedded copies go stale when the source changes; 4 ways to manage it |

`lib.js` has the `plan()` helper the scripts use: it prints the 5 numbers from `explain()`
that matter (plan stages, index keys read, docs read, docs returned, time).

## The whole topic in five lines

1. **Postgres:** design the tables from the *data* (normalize), then write any query you like.
   **Mongo:** design the documents from the *queries* ("data that's read together is stored together").
2. One document is always written atomically. Embed things so most writes touch one document.
3. Every frequent query needs an index, with fields in **Equality → Sort → Range** order.
4. Don't let anything grow without limit inside one document (16 MB cap, slower reads as it grows).
5. Joins (`$lookup`) and multi-doc transactions exist, but if you need them everywhere, use Postgres.

Reset: `docker compose down && docker compose up -d --wait`, then run `seed.js` again.
