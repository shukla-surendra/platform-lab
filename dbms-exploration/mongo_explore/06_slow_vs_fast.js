// 06 — Same answer, very different cost. Classic slow patterns and their fast versions.
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.orders.dropIndexes();
db.orders.createIndex({ status: 1 });
db.orders.createIndex({ createdAt: 1 });
db.users.createIndex({ name: 1 });

// 1. Regex: anchored prefix uses the index; "contains" scans every key.
plan("name /^user99/ (prefix)", db.users.find({ name: /^user99/ }));
plan("name /99/ (contains)", db.users.find({ name: /99/ }));

// 2. Negation: $ne / $nin match almost everything -> index barely helps.
plan("status $ne cancelled", db.orders.find({ status: { $ne: "cancelled" } }));
plan("status $in [3 values]", db.orders.find({ status: { $in: ["pending", "shipped", "delivered"] } }));
//    When a query returns most of the collection, the index is SLOWER than reading everything:
plan("status $ne, forced full scan", db.orders.find({ status: { $ne: "cancelled" } }).hint({ $natural: 1 }));

// 3. Pagination: skip(N) still walks N entries. "Keyset" jumps straight there.
plan("page 10000 via skip", db.orders.find().sort({ createdAt: 1 }).skip(200000).limit(20));
const last = db.orders.find().sort({ createdAt: 1 }).skip(199999).limit(1).next().createdAt;
plan("page 10000 via createdAt > last", db.orders.find({ createdAt: { $gt: last } }).sort({ createdAt: 1 }).limit(20));

// 4. Sort without an index -> in-memory SORT stage (fails above 100 MB unless allowDiskUse).
plan("sort by total (no index)", db.orders.find().sort({ total: -1 }).limit(20));
plan("sort by createdAt (indexed)", db.orders.find().sort({ createdAt: -1 }).limit(20));


/* Real output (MongoDB 7.0, after seed.js):
name /^user99/ (prefix)            FETCH <- IXSCAN              keys=11 docs=11 returned=11 ms=0
name /99/ (contains)               FETCH <- IXSCAN              keys=1000 docs=19 returned=19 ms=0
status $ne cancelled               FETCH <- IXSCAN              keys=225001 docs=225000 returned=225000 ms=96
status $in [3 values]              FETCH <- IXSCAN              keys=225000 docs=225000 returned=225000 ms=93
status $ne, forced full scan       COLLSCAN                     keys=0 docs=300000 returned=225000 ms=53
page 10000 via skip                LIMIT <- FETCH <- SKIP <- IXSCAN keys=200020 docs=20 returned=20 ms=34
page 10000 via createdAt > last    LIMIT <- FETCH <- IXSCAN     keys=20 docs=20 returned=20 ms=0
sort by total (no index)           SORT <- COLLSCAN             keys=0 docs=300000 returned=20 ms=54
sort by createdAt (indexed)        LIMIT <- FETCH <- IXSCAN     keys=20 docs=20 returned=20 ms=0
*/
