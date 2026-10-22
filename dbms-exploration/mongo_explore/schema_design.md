# How a MongoDB schema is designed

## The one rule

> **Data that is read together is stored together.**

Postgres: you model the *things* (customers, orders, items), normalize them, and let JOINs
assemble any view later. Mongo: you model the *screens and API calls*. Each one should ideally
be **one read of one document** (or one indexed range of documents).

"Schemaless" means the database doesn't force a schema. Your app still has one. Enforce it with
`$jsonSchema` validation (bottom of this file) or an ODM (Mongoose, Pydantic/Beanie).

## Embed or reference? Decision matrix

| Question | → Embed | → Reference (separate collection) |
|---|---|---|
| Read together with the parent most of the time? | yes | no, often read alone |
| How many per parent? | **few** (addresses, order items) | **many / unbounded** (reviews, logs, comments) |
| Does it change independently, by other users? | no | yes (product price changes ≠ old orders change) |
| Needs to be queried/listed on its own? | rarely | yes ("all reviews by user X") |
| Shared by many parents? | no (or a copy is fine) | yes, one source of truth |
| Must the parent + child update atomically? | yes → embed (single-doc atomic) | can live with a transaction or eventual sync |

Script 08 measured the extremes: 10 embedded reviews = 2.6 KB, one read, perfect.
50,000+ embedded reviews = **16 MB limit error**, and 50 reads took **2,541 ms vs 14 ms** for
the referenced design.

## Relationships by size

| Relationship | Example | Design |
|---|---|---|
| one-to-one | user → profile settings | embed |
| one-to-**few** (< ~100, bounded) | user → addresses, order → items | embed an array |
| one-to-**many** (hundreds–thousands) | product → reviews | separate collection, child stores `productId` (+ index) |
| one-to-**squillions** (unbounded) | server → log lines, sensor → readings | child references parent; never an array in the parent; consider the bucket pattern |
| many-to-many | students ↔ courses | arrays of ids on one or both sides, e.g. `courseIds: [..]` (bounded) |

## Design patterns (the named ones interviewers ask about)

| Pattern | Problem | Idea | Example in this lab |
|---|---|---|---|
| **Extended reference** | joining to show a name every time | copy the few fields you display next to the id | order items store `productId` + `name` + `price` at purchase time (10) |
| **Subset** | parent doc too big because of a long list | embed only the latest/top N, keep the full list elsewhere | product has `latestReviews` (3); all reviews in `reviews` (10) |
| **Computed** | recalculating aggregates on every read | store the result, update it on write | `rating: { avg, count }` on product (10) |
| **Bucket** | millions of tiny docs (IoT, metrics) | one doc per sensor per hour with an array of readings | (or use time-series collections) |
| **Outlier** | 99% of items small, a few huge (celebrity followers) | normal embed + `hasOverflow: true` → overflow docs | |
| **Polymorphic** | different shapes in one list (products of different kinds) | one collection, `type` field, shared indexed fields | |
| **Schema versioning** | changing shape without downtime | `schemaVersion: 2`, app reads both, migrate lazily | |
| **Attribute** | many optional searchable fields | `attrs: [{k: "color", v: "red"}]` + index `{ "attrs.k": 1, "attrs.v": 1 }` | |

## Duplication is allowed — but decide who's the source of truth

Copying `name` into orders (extended reference) means a product rename doesn't update old
orders. That's **correct** for receipts and **wrong** for a user's display name in comments.
For each copied field, decide: *snapshot* (never update) or *must stay in sync* (update with
`updateMany` / a change stream / a background job, and accept that it's briefly stale).
Runnable Python walkthrough of every option: [stale_copies/](stale_copies/README.md).

## Anti-patterns

- **Unbounded arrays** (comments, followers, logs inside one doc) → 16 MB, slow reads, slow index updates.
- **Mirroring your SQL tables 1:1** then using `$lookup` everywhere → you got Postgres without its join planner.
- **Huge documents** read for a tiny field → use projection, or split hot and cold fields.
- **Too many collections** (one per user/tenant) → use one collection + `tenantId`.
- **Indexing every field** → slow writes, RAM pressure (see [indexes.md](indexes.md)).
- **Case-sensitive mess**: storing `"Pune"` and `"pune"` → normalize on write or use a collation.

## Enforcing a schema anyway

```js
db.createCollection("orders", { validator: { $jsonSchema: {
  bsonType: "object",
  required: ["userId", "status", "items"],
  properties: {
    status: { enum: ["pending", "shipped", "delivered", "cancelled"] },
    items:  { bsonType: "array", minItems: 1, maxItems: 100 },   // bound your arrays!
  },
}}});
```

Next: [access_patterns.md](access_patterns.md), the step-by-step method.
