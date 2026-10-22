// 01 — A document is a JSON object; a collection is a folder of them.
//
// Story: in Postgres an order is spread over 3 tables (orders, order_items, addresses) and
// you JOIN them back. In Mongo you store the order the way you'd print the receipt: one
// object, with its items and address inside it.
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.demo.drop();

db.demo.insertOne({
  _id: "order-1",
  user: { id: 7, name: "Asha" },                 // embedded object
  items: [                                        // embedded array
    { sku: "pen", qty: 2, price: 10 },
    { sku: "bag", qty: 1, price: 900 },
  ],
  status: "pending",
});
db.demo.insertOne({ _id: "order-2", user: { id: 8, name: "Ravi" }, items: [{ sku: "pen", qty: 1, price: 10 }], giftNote: "Happy birthday" });

// "dot notation" reaches inside objects and arrays
show(db.demo.find({ "user.name": "Asha" }, { _id: 1 }).toArray());
show(db.demo.find({ "items.sku": "bag" }, { _id: 1 }).toArray());     // any item matches
// no fixed schema: order-2 has giftNote and no status; order-1 the opposite
show(db.demo.find({ status: { $exists: false } }, { _id: 1, giftNote: 1 }).toArray());

/* Real output (MongoDB 7.0, after seed.js):
[{"_id":"order-1"}]
[{"_id":"order-1"}]
[{"_id":"order-2","giftNote":"Happy birthday"}]
*/
