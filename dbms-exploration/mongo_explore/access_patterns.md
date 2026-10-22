# Designing from access patterns — the method

Worked example: a small shop app. The code version, with every query proven indexed, is
[10_access_pattern_design.js](10_access_pattern_design.js).

## Step 1 — List every query the app makes, with how often

Write them as sentences first, **before** thinking about collections:

| # | Screen / API | Query | Frequency | Read or write |
|:-:|---|---|---|---|
| Q1 | profile page | user by id, with addresses | high | R |
| Q2 | "my orders" | user's last 20 orders, newest first | high | R |
| Q3 | order detail | one order by id, with its items | high | R |
| Q4 | product page | product + rating + a few latest reviews; "see all" pages through reviews | **very high** | R |
| Q5 | admin dashboard | oldest pending orders | low | R |
| Q6 | category page | products with tag X, by price | high | R |
| W1 | checkout | create order, reduce stock | medium | W |
| W2 | write review | add review, update rating | low | W |

The **ratio of reads to writes** decides a lot. The product page is read ~1000× more often than
a review is written, so it's worth doing extra work on the write (W2) to make the read (Q4)
a single document.

## Step 2 — For each query, decide what one document must contain

| Query | Shape decision | Why |
|---|---|---|
| Q1 | `users` with `addresses: [...]` embedded | one-to-few, always shown together |
| Q2, Q3 | `orders` own collection, `userId` field | one-to-many and growing: never an array of orders in the user doc |
| Q3 | items embedded **with `name`, `price` copied** | extended reference: the receipt must not change if the product is renamed or re-priced |
| Q4 | `products` holds `rating: {avg, count}` + `latestReviews` (3) | computed + subset patterns → product page = 1 read |
| Q4 "see all" | `reviews` own collection with `productId` | unbounded, paged |
| Q6 | `products.tags` array | multikey index |

## Step 3 — One index per query, in ESR order

| Query | Filter (E) | Sort (S) | Range (R) | Index |
|---|---|---|---|---|
| Q1, Q3, Q4 | `_id` | | | built-in `_id` |
| Q2 | `userId` | `createdAt -1` | | `{ userId: 1, createdAt: -1 }` |
| Q4 see all | `productId` | `at -1` | | `{ productId: 1, at: -1 }` |
| Q5 | `status: "pending"` (always) | `createdAt` | | partial `{ createdAt: 1 }` where pending |
| Q6 | `tags` | `price` | | `{ tags: 1, price: 1 }` |

## Step 4 — Prove it with `explain()`

Real output of script 10. Every query is `IDHACK` (lookup by `_id`) or `IXSCAN`. There's no
`COLLSCAN` and no `SORT`:
```
Q1 profile + addresses             IDHACK
Q2 my last 20 orders               LIMIT <- FETCH <- IXSCAN
Q3 order detail                    IDHACK
Q4a product page                   IDHACK
Q4b 'see all reviews' page         LIMIT <- FETCH <- IXSCAN
Q5 admin: oldest pending           LIMIT <- FETCH <- IXSCAN
Q6 tag 'sale' by price             LIMIT <- FETCH <- IXSCAN
```

## Step 5 — Design the writes

| Write | Steps | Atomic how? |
|---|---|---|
| W1 checkout | `products.updateOne({_id, stock: {$gte: qty}}, {$inc: {stock: -qty}})` → if modified, insert order | conditional update (02); wrap both in a transaction if they must be all-or-nothing (09) |
| W2 review | insert into `reviews`; `$inc` rating count/sum and `$push` with `$slice: -3` into `latestReviews` | two docs → transaction, or accept rating being briefly behind |

```js
db.products.updateOne({ _id: 7 }, {
  $inc: { "rating.count": 1, "rating.sum": 5 },
  $push: { latestReviews: { $each: [newReview], $slice: -3 } },   // bounded array!
});
```

## Step 6 — Re-check against the warning list

- Any array that can grow forever? (`latestReviews` is capped with `$slice` ✅)
- Any query not in the table? Add an index, or accept a slow admin query.
- Will one document be updated by thousands of users per second? (a "hot document" → split it, e.g. counter shards)
- Will this collection ever be sharded? Pick a shard key that's in most queries (`userId` for orders).

When requirements change, start again from Step 1. In Mongo, a new access pattern can mean a
new shape, not just a new query.
