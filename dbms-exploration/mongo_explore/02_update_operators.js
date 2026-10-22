// 02 — Updates change part of a document, atomically.
//
// Story: two cashiers sell the last pens at the same time. With $inc, Mongo does
// "read-add-write" inside the server as ONE step on ONE document — no lost sale,
// no lock you have to manage. (Same idea as Postgres `SET stock = stock - 1`.)
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.stock.drop();
db.stock.insertOne({ _id: "pen", qty: 100, log: [] });

db.stock.updateOne({ _id: "pen" }, { $inc: { qty: -1 } });                 // add/subtract
db.stock.updateOne({ _id: "pen" }, { $set: { color: "blue" } });           // set a field
db.stock.updateOne({ _id: "pen" }, { $push: { log: "sold 1" } });          // append to array
show(db.stock.findOne());

// Conditional update = safe "only sell if in stock" (no read-then-write in the app)
const r1 = db.stock.updateOne({ _id: "pen", qty: { $gte: 500 } }, { $inc: { qty: -500 } });
show({ soldFiveHundred: r1.modifiedCount });

// Upsert: update if exists, insert if not
db.stock.updateOne({ _id: "bag" }, { $inc: { qty: 5 } }, { upsert: true });
show(db.stock.find({}, { log: 0 }).toArray());

/* Real output (MongoDB 7.0, after seed.js):
{"_id":"pen","qty":99,"log":["sold 1"],"color":"blue"}
{"soldFiveHundred":0}
[{"_id":"pen","qty":99,"color":"blue"},{"_id":"bag","qty":5}]
*/
