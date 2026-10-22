"""
03 — FIRST QUESTION TO ASK: is this copy SUPPOSED to change?

Story: a restaurant changes its menu prices. The menu on the table must show the new
price (LIVE copy). The bill you were given yesterday must keep yesterday's price
(SNAPSHOT). Same data, opposite rules.

- products.categories  -> LIVE: the product page must show today's name and tax.
- orders.categories    -> SNAPSHOT: the invoice must keep the tax charged at purchase.
                          "Stale" here is correct. Never fan-out to orders.
"""
from common import mdb, mongo, seed_mongo, show

seed_mongo()

# an order copies the category AS IT WAS at purchase time
product = mdb.products.find_one({"_id": 1})
mdb.orders.insert_one({"_id": "order-1", "productId": 1, "price": product["price"],
                       "categories": product["categories"], "status": "paid"})

# tax changes later -> update only the LIVE copies (same fan-out as 02)
with mongo.start_session() as s, s.start_transaction():
    mdb.categories.update_one({"_id": "phones"}, {"$set": {"taxRate": 12}}, session=s)
    mdb.products.update_many({"categories._id": "phones"}, {"$set": {"categories.$[c].taxRate": 12}},
                             array_filters=[{"c._id": "phones"}], session=s)

show("product page tax (live)", mdb.products.find_one({"_id": 1})["categories"][0]["taxRate"])
show("order-1 invoice tax (snapshot)", mdb.orders.find_one({"_id": "order-1"})["categories"][0]["taxRate"])

"""
Real output:

product page tax (live)                12
order-1 invoice tax (snapshot)         18
"""
