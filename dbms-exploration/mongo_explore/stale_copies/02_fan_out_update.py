"""
02 — FIX 1: FAN-OUT UPDATE. Change the master AND every copy, together.

Story: when the manager changes the master list, someone walks to every shelf and
replaces the copy, and the shop stays closed until it's done (a transaction), so no
customer sees half-old / half-new shelves.

Two tricks:
- `categories.$[c]` + array_filters: update ONLY the matching element inside each
  product's categories array (a product can hold several categories).
- an index on "categories._id" so finding the copies isn't a full scan.
"""
import time

from common import mdb, mongo, seed_mongo, show

seed_mongo()
new = {"name": "Mobile Phones", "taxRate": 12}

t = time.perf_counter()
with mongo.start_session() as s, s.start_transaction():
    mdb.categories.update_one({"_id": "phones"}, {"$set": new}, session=s)
    r = mdb.products.update_many(
        {"categories._id": "phones"},
        {"$set": {"categories.$[c].name": new["name"], "categories.$[c].taxRate": new["taxRate"]}},
        array_filters=[{"c._id": "phones"}],
        session=s,
    )
show("products updated", r.modified_count)
show("took", f"{(time.perf_counter() - t) * 1000:.0f} ms")

show("product 1 embedded copy", mdb.products.find_one({"_id": 1})["categories"][0])
show("product 4 (laptops + sale) untouched", [c["name"] for c in mdb.products.find_one({"_id": 4})["categories"]])
stale = mdb.products.count_documents({"categories": {"$elemMatch": {"_id": "phones", "taxRate": {"$ne": 12}}}})
show("stale copies left", stale)

"""
Real output:

products updated                       10000
took                                   48 ms
product 1 embedded copy                {'_id': 'phones', 'name': 'Mobile Phones', 'path': 'Electronics > Phones', 'taxRate': 12, 'returnDays': 7}
product 4 (laptops + sale) untouched   ['Laptops', 'Sale']
stale copies left                      0
"""
