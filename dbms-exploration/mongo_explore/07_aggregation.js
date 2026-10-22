// 07 — The aggregation pipeline: Mongo's GROUP BY / JOIN.
//
// Story: an assembly line. Each stage takes documents in and passes documents out.
// Put $match (and $sort) FIRST so they can use indexes and shrink the stream early.
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.orders.dropIndexes();
db.orders.createIndex({ status: 1, createdAt: 1 });

// SQL: SELECT city, count(*), sum(total) FROM orders
//      WHERE status='delivered' AND createdAt >= '2026-06-01' GROUP BY city ORDER BY 3 DESC
const byCity = db.orders.aggregate([
  { $match: { status: "delivered", createdAt: { $gte: new Date("2026-06-01") } } },
  { $group: { _id: "$city", orders: { $sum: 1 }, revenue: { $sum: "$total" } } },
  { $sort: { revenue: -1 } },
]).toArray();
byCity.forEach(show);

// $unwind = one output doc per array element; then group per product (top 3 sellers)
show(db.orders.aggregate([
  { $match: { status: "delivered", createdAt: { $gte: new Date("2026-06-01") } } },
  { $unwind: "$items" },
  { $group: { _id: "$items.name", qty: { $sum: "$items.qty" } } },
  { $sort: { qty: -1 } }, { $limit: 3 },
]).toArray());

// $lookup = LEFT JOIN. Works, but it's a query per input doc: keep the input small.
show(db.orders.aggregate([
  { $match: { userId: 42 } }, { $limit: 1 },
  { $lookup: { from: "users", localField: "userId", foreignField: "_id", as: "user" } },
  { $project: { _id: 0, total: 1, "user.name": 1, "user.address.city": 1 } },
]).toArray());

const e = db.orders.explain().aggregate([{ $match: { status: "delivered" } }, { $group: { _id: "$city" } }]);
show({ firstStageUsesIndex: JSON.stringify(e).includes("IXSCAN") });

/* Real output (MongoDB 7.0, after seed.js):
{"_id":"Bengaluru","orders":4128,"revenue":10767504}
{"_id":"Chennai","orders":4128,"revenue":10750632}
{"_id":"Pune","orders":4128,"revenue":10733760}
{"_id":"Delhi","orders":4128,"revenue":10716888}
{"_id":"Mumbai","orders":4128,"revenue":10700016}
[{"_id":"product103","qty":827},{"_id":"product63","qty":827},{"_id":"product147","qty":827}]
[{"total":4967,"user":[{"name":"user42","address":{"city":"Delhi"}}]}]
{"firstStageUsesIndex":true}
*/
