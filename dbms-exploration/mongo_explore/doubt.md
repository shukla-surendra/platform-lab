# MongoDB — doubts

Glossary:
- **Document** — one JSON-like record (stored as BSON), max 16 MB.
- **Collection** — a group of documents (like a table, but no fixed columns).
- **COLLSCAN / IXSCAN** — read every document / use an index.
- **ESR** — compound index field order: Equality, Sort, Range.
- **Embed / reference** — put data inside the parent doc / store it separately with an id.
- **Access pattern** — one query the app makes (what it filters, sorts, returns, and how often).

(Your questions will be added below as `## Qn.` sections.)

## Q1. How do I run these .js files?

Short version: `make up` once, then `make run L=03`. Full guide: [HOW_TO_USE.md](HOW_TO_USE.md).

They aren't Node.js programs. They're **mongosh scripts**: JavaScript that the Mongo shell runs,
with `db`, `print`, and `load` built in. mongosh isn't installed on the Mac, but it **is**
inside the container, and `docker-compose.yml` mounts this folder at `/lab` there.

```
 your Mac                                container
 mongo_explore/03_index_basics.js  ──►  /lab/03_index_basics.js  ──► mongosh runs it
```

```bash
cd dbms-exploration/mongo_explore
docker compose up -d --wait                                         # 1. start Mongo
docker compose exec mongo mongosh --quiet /lab/seed.js              # 2. load data (once)
docker compose exec mongo mongosh --quiet /lab/03_index_basics.js   # 3. run a lesson
```

Inside the shell, to experiment after a lesson:
```bash
docker compose exec mongo mongosh shop
shop> load("/lab/03_index_basics.js")
shop> db.orders.find({ userId: 42 }).explain("executionStats")
```

Gotchas:
- Use the path **`/lab/...`** (inside the container), not your Mac path.
- `node 03_index_basics.js` won't work, because `db` and `load` only exist in mongosh.
- With mongosh installed on the Mac (`brew install mongosh`), the scripts still say
  `load("/lab/lib.js")`, so keep running them through the container.
- Lessons 03–07 drop and recreate indexes; if output looks odd, re-run `seed.js`.

## Q2. I embed category documents (several attributes each) into other records because they're read together. When a category changes, all those copies are stale. How is that managed, and how does Postgres do it?

Short answer: **first decide whether the copy should change at all.** An invoice's tax is a
*snapshot* and must stay old. A product page's category is *live* and must follow the master.
For live copies, Mongo gives you three options:

1. **Fan-out update** (update master + every copy in one transaction): always fresh, writes cost more.
2. **Embed less**: copy only fields that rarely change; look up volatile ones.
3. **Background sync** (change stream worker): cheap, but stale for a moment.

Postgres stores the category **once** and JOINs, so a rename is 1 row and nothing goes stale.
Copies only appear if you add them (snapshot columns, a trigger-maintained jsonb copy, or a
materialized view).

Measured: rename → 10,000 stale Mongo products; fan-out fixed them in 48 ms; Postgres
updated 1 row. Python walkthroughs: Mongo in [stale_copies/](stale_copies/README.md),
Postgres in [../pg_stale_copies/](../pg_stale_copies/README.md).
