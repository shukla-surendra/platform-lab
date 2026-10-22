// 03 — Without an index Mongo reads EVERY document (COLLSCAN).
//
// Story: finding one customer's orders in a 300,000-page notebook. Without an index you
// flip every page. An index is the alphabetical list at the back: jump straight there.
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.orders.dropIndexes();

plan("userId = 42, no index", db.orders.find({ userId: 42 }));

db.orders.createIndex({ userId: 1 });
plan("userId = 42, index {userId:1}", db.orders.find({ userId: 42 }));

// An index only helps if the query uses its FIRST field
plan("status = 'pending' (not indexed)", db.orders.find({ status: "pending" }));

show(db.orders.getIndexes().map(i => i.name));

/* Real output (MongoDB 7.0, after seed.js):
userId = 42, no index              COLLSCAN                     keys=0 docs=300000 returned=300 ms=47
userId = 42, index {userId:1}      FETCH <- IXSCAN              keys=300 docs=300 returned=300 ms=1
status = 'pending' (not indexed)   COLLSCAN                     keys=0 docs=300000 returned=75000 ms=52
["_id_","userId_1"]
*/
