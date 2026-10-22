// 04 — Compound indexes and the ESR rule: Equality, Sort, Range.
//
// Query from the "my orders" page: one user's orders above 1000, newest first.
// The ORDER of fields in a compound index decides whether Mongo can use it fully.
// Story: a phone book sorted by (city, surname). Great for "Smiths in Pune".
// Useless order for "everyone named Smith in any city".
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.orders.dropIndexes();
const q = () => db.orders.find({ userId: 42, total: { $gt: 1000 } }).sort({ createdAt: -1 }).limit(20);

db.orders.createIndex({ userId: 1, total: 1, createdAt: -1 });    // E, R, S  (wrong)
plan("E-R-S {userId,total,createdAt}", q());
db.orders.dropIndexes();

db.orders.createIndex({ userId: 1, createdAt: -1, total: 1 });    // E, S, R  (right)
plan("E-S-R {userId,createdAt,total}", q());

// Index prefix: {userId, createdAt, total} also serves "all orders of user 42"...
plan("prefix: userId only", db.orders.find({ userId: 42 }));
// ...but NOT a query that skips the first field
plan("no prefix: createdAt only", db.orders.find({ createdAt: { $gt: new Date("2026-06-01") } }).limit(20));

/* Real output (MongoDB 7.0, after seed.js):
E-R-S {userId,total,createdAt}     FETCH <- SORT <- IXSCAN      keys=240 docs=20 returned=20 ms=1
E-S-R {userId,createdAt,total}     LIMIT <- FETCH <- IXSCAN     keys=25 docs=20 returned=20 ms=1
prefix: userId only                FETCH <- IXSCAN              keys=300 docs=300 returned=300 ms=0
no prefix: createdAt only          LIMIT <- COLLSCAN            keys=0 docs=217461 returned=20 ms=41
*/
