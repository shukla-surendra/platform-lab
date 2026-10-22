// 05 — Three index tricks: covered queries, arrays (multikey), partial indexes.
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.orders.dropIndexes();
db.orders.createIndex({ userId: 1, status: 1 });

// Covered: every field asked for is IN the index -> no document is read (docs=0).
// You must exclude _id, because it isn't in this index.
plan("covered (projection in index)", db.orders.find({ userId: 42 }, { _id: 0, userId: 1, status: 1 }));
plan("not covered (needs total)", db.orders.find({ userId: 42 }, { _id: 0, userId: 1, total: 1 }));

// Multikey: index on a field inside an array -> one index entry PER array element.
db.products.createIndex({ tags: 1 });
plan("tags = 'sale' (multikey)", db.products.find({ tags: "sale" }));

// Partial: only index the documents you actually query (smaller, faster to write).
db.orders.createIndex({ createdAt: 1 }, { partialFilterExpression: { status: "pending" } });
plan("pending + date (partial used)", db.orders.find({ status: "pending", createdAt: { $gt: new Date("2026-07-01") } }));
plan("shipped + date (partial unusable)", db.orders.find({ status: "shipped", createdAt: { $gt: new Date("2026-07-01") } }));

const s = db.orders.stats({ indexDetails: false }).indexSizes;
show(Object.fromEntries(Object.entries(s).map(([k, v]) => [k, Math.round(v / 1024) + " KB"])));

/* Real output (MongoDB 7.0, after seed.js):
covered (projection in index)      PROJECTION_COVERED <- IXSCAN keys=300 docs=0 returned=300 ms=0
not covered (needs total)          PROJECTION_SIMPLE <- FETCH <- IXSCAN keys=300 docs=300 returned=300 ms=0
tags = 'sale' (multikey)           FETCH <- IXSCAN              keys=100 docs=100 returned=100 ms=0
pending + date (partial used)      FETCH <- IXSCAN              keys=9839 docs=9839 returned=9839 ms=4
shipped + date (partial unusable)  COLLSCAN                     keys=0 docs=300000 returned=9840 ms=56
{"_id_":"7592 KB","userId_1_status_1":"1704 KB","createdAt_1":"844 KB"}
*/
