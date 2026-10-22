"""
04 — FIX 2: DON'T COPY WHAT CHANGES. Embed only stable fields, look the rest up.

Story: instead of printing the price on every shelf label, the label says "see the
price board" and points to one board. Change the board once, everyone sees it.

Split category fields by how often they change:
- stable  (_id, name)                  -> embed: the listing page needs no extra read
- volatile (taxRate, returnDays, path) -> read from `categories` when needed

The cost: one extra lookup, either $lookup in the pipeline or a tiny in-app cache
(3 categories vs 20,000 products, so the cache is easy).

A name DOES change sometimes (01 renamed "Phones"). Because it changes rarely, a fan-out
(02) or a background sync (05) for just that one field is cheap and acceptable.
"""
from common import mdb, seed_mongo, show

seed_mongo()
# keep only {_id, name} inside products
mdb.products.update_many({}, [{"$set": {"categories": {
    "$map": {"input": "$categories", "as": "c", "in": {"_id": "$$c._id", "name": "$$c.name"}}}}}])

mdb.categories.update_one({"_id": "phones"}, {"$set": {"taxRate": 12, "returnDays": 15}})

# A) server-side join: always fresh
doc = mdb.products.aggregate([
    {"$match": {"_id": 1}},
    {"$lookup": {"from": "categories", "localField": "categories._id", "foreignField": "_id",
                 "as": "categoryDetails", "pipeline": [{"$project": {"taxRate": 1, "returnDays": 1}}]}},
]).next()
show("embedded (stable part)", doc["categories"])
show("looked up (volatile part)", doc["categoryDetails"])

# B) app-side cache: load all categories once, refresh every N seconds / on change event
cache = {c["_id"]: c for c in mdb.categories.find()}
p = mdb.products.find_one({"_id": 1})
show("tax via cache", [cache[c["_id"]]["taxRate"] for c in p["categories"]])

"""
Real output:

embedded (stable part)                 [{'_id': 'phones', 'name': 'Phones'}]
looked up (volatile part)              [{'_id': 'phones', 'taxRate': 12, 'returnDays': 15}]
tax via cache                          [12]
"""
