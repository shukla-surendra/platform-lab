// Fake shop data used by every lesson. Run: make seed  (or see README)
// 1,000 users, 200 products, 300,000 orders. Takes ~10 s.
db = db.getSiblingDB("shop");
db.dropDatabase();

const cities = ["Pune", "Delhi", "Mumbai", "Bengaluru", "Chennai"];
const statuses = ["pending", "shipped", "delivered", "cancelled"];

db.users.insertMany(Array.from({ length: 1000 }, (_, i) => ({
  _id: i + 1,
  name: `user${i + 1}`,
  email: `user${i + 1}@example.com`,
  address: { city: cities[i % 5], pin: String(411000 + i) },
})));

db.products.insertMany(Array.from({ length: 200 }, (_, i) => ({
  _id: i + 1,
  name: `product${i + 1}`,
  price: 100 + (i * 37) % 900,
  tags: [["phone", "laptop", "book", "toy"][i % 4], i % 2 ? "sale" : "new"],
})));

const start = new Date("2026-01-01").getTime();
for (let batch = 0; batch < 30; batch++) {
  db.orders.insertMany(Array.from({ length: 10000 }, (_, j) => {
    const n = batch * 10000 + j;
    const pid = (n * 7) % 200 + 1;
    return {
      userId: (n * 13) % 1000 + 1,
      status: statuses[n % 4],
      city: cities[n % 5],
      total: 100 + (n * 31) % 5000,
      createdAt: new Date(start + n * 60000),          // one order per minute
      items: [{ productId: pid, name: `product${pid}`, qty: 1 + n % 3 }],
    };
  }));
}
print(`users ${db.users.countDocuments()}, products ${db.products.countDocuments()}, orders ${db.orders.countDocuments()}`);
