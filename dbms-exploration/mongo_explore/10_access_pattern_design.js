// 10 — Designing from access patterns (worked example; method in access_patterns.md).
//
// Step 1 was writing down the app's queries. Step 2 is shaping documents so each query is
// ONE indexed read. Step 3 (this script) proves every query is an IXSCAN, no COLLSCAN/SORT.
load("/lab/lib.js");
db = db.getSiblingDB("app");
db.dropDatabase();

// users: addresses embedded (few, always shown with the user)
db.users.insertOne({ _id: 42, name: "Asha", addresses: [{ label: "home", city: "Pune", default: true }] });

// products: rating summary pre-computed + the 3 latest reviews copied in (subset pattern)
db.products.insertOne({ _id: 7, name: "pen", price: 10, tags: ["stationery", "sale"],
  rating: { avg: 4.5, count: 1200 },
  latestReviews: [{ user: "Ravi", stars: 5, text: "smooth" }] });

// reviews: their own collection (unbounded: could be millions per product)
db.reviews.insertOne({ productId: 7, user: "Ravi", stars: 5, text: "smooth", at: new Date() });

// orders: items embedded with name/price COPIED at purchase time (extended reference:
// the receipt must not change when the product is renamed or re-priced later)
db.orders.insertOne({ userId: 42, status: "pending", createdAt: new Date(),
  items: [{ productId: 7, name: "pen", price: 10, qty: 2 }], total: 20 });

// one index per access pattern (ESR order)
db.orders.createIndex({ userId: 1, createdAt: -1 });                                   // Q2
db.orders.createIndex({ createdAt: 1 }, { partialFilterExpression: { status: "pending" } }); // Q5
db.reviews.createIndex({ productId: 1, at: -1 });                                      // Q4
db.products.createIndex({ tags: 1, price: 1 });                                        // Q6

plan("Q1 profile + addresses", db.users.find({ _id: 42 }));
plan("Q2 my last 20 orders", db.orders.find({ userId: 42 }).sort({ createdAt: -1 }).limit(20));
plan("Q3 order detail", db.orders.find({ _id: db.orders.findOne()._id }));
plan("Q4a product page", db.products.find({ _id: 7 }));
plan("Q4b 'see all reviews' page", db.reviews.find({ productId: 7 }).sort({ at: -1 }).limit(20));
plan("Q5 admin: oldest pending", db.orders.find({ status: "pending" }).sort({ createdAt: 1 }).limit(50));
plan("Q6 tag 'sale' by price", db.products.find({ tags: "sale" }).sort({ price: 1 }).limit(20));

/* Real output (MongoDB 7.0, after seed.js):
Q1 profile + addresses             IDHACK                       keys=1 docs=1 returned=1 ms=0
Q2 my last 20 orders               LIMIT <- FETCH <- IXSCAN     keys=1 docs=1 returned=1 ms=0
Q3 order detail                    IDHACK                       keys=1 docs=1 returned=1 ms=0
Q4a product page                   IDHACK                       keys=1 docs=1 returned=1 ms=0
Q4b 'see all reviews' page         LIMIT <- FETCH <- IXSCAN     keys=1 docs=1 returned=1 ms=0
Q5 admin: oldest pending           LIMIT <- FETCH <- IXSCAN     keys=1 docs=1 returned=1 ms=0
Q6 tag 'sale' by price             LIMIT <- FETCH <- IXSCAN     keys=1 docs=1 returned=1 ms=0
*/
