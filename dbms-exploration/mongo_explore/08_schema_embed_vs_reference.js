// 08 — Embed or reference? Measure it.
//
// Same data, two designs, for the page "show product 7 with its latest 10 reviews":
//   A) embedded:   reviews live inside the product document (1 read)
//   B) referenced: reviews in their own collection with productId (2 reads, or $lookup)
// And what happens when a product gets 50,000 reviews (unbounded array).
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.p_embed.drop(); db.p_ref.drop(); db.reviews.drop();

const review = (i) => ({ user: `user${i}`, stars: 1 + (i % 5), text: "x".repeat(200), at: new Date(1e12 + i) });
db.p_embed.insertOne({ _id: 7, name: "product7", reviews: Array.from({ length: 10 }, (_, i) => review(i)) });
db.p_ref.insertOne({ _id: 7, name: "product7" });
db.reviews.insertMany(Array.from({ length: 10 }, (_, i) => ({ productId: 7, ...review(i) })));
db.reviews.createIndex({ productId: 1, at: -1 });

show({ embedded_reads: 1, doc_bytes: bsonsize(db.p_embed.findOne({ _id: 7 })) });
const p = db.p_ref.findOne({ _id: 7 });
const rs = db.reviews.find({ productId: 7 }).sort({ at: -1 }).limit(10).toArray();
show({ referenced_reads: 2, reviews_found: rs.length });

// Grow it: keep pushing batches of 500 reviews into the embedded array
try {
  for (let b = 0; b < 140; b++)
    db.p_embed.updateOne({ _id: 7 }, { $push: { reviews: { $each: Array.from({ length: 500 }, (_, i) => review(b * 500 + i)) } } });
} catch (e) { show({ error: e.message.slice(0, 90) }); }
show({ embedded_doc_MB_now: (bsonsize(db.p_embed.findOne({ _id: 7 })) / 1048576).toFixed(1) });

// Now even reading just the product name loads the whole huge document from disk/cache
let t = Date.now(); for (let i = 0; i < 50; i++) db.p_embed.findOne({ _id: 7 });
const tEmbed = Date.now() - t;
t = Date.now(); for (let i = 0; i < 50; i++) db.p_ref.findOne({ _id: 7 });
show({ "50 reads ms (embedded, huge)": tEmbed, "50 reads ms (referenced)": Date.now() - t });

/* Real output (MongoDB 7.0, after seed.js):
{"embedded_reads":1,"doc_bytes":2627}
{"referenced_reads":2,"reviews_found":10}
{"error":"BSONObj size: 16871447 (0x1017017) is invalid. Size must be between 0 and 16793600(16MB) F"}
{"embedded_doc_MB_now":"16.0"}
{"50 reads ms (embedded, huge)":2541,"50 reads ms (referenced)":14}
*/
