"""
01 — THE PROBLEM: copies go stale.

Story: you printed the shop's price list and stuck a copy on every shelf. Then the
manager changes one price on the master list. Every shelf copy is now wrong, and
nothing tells you which ones.

In Mongo we embedded a copy of each category inside every product (read together ->
stored together). Now "Phones" is renamed and its tax drops from 18% to 12%.
Only the categories collection changes. The 10,000 embedded copies don't.
"""
from common import mdb, seed_mongo, show

seed_mongo()

# the "master" record changes
mdb.categories.update_one({"_id": "phones"}, {"$set": {"name": "Mobile Phones", "taxRate": 12}})
show("categories.phones now", mdb.categories.find_one({"_id": "phones"}, {"name": 1, "taxRate": 1}))

# ...but the product page reads the embedded copy
p = mdb.products.find_one({"_id": 1}, {"categories": 1})
show("product 1 embedded copy", p["categories"][0])

stale = mdb.products.count_documents({"categories": {"$elemMatch": {"_id": "phones", "taxRate": {"$ne": 12}}}})
show("products with a stale 'phones' copy", stale)

"""
Real output:

categories.phones now                  {'_id': 'phones', 'name': 'Mobile Phones', 'taxRate': 12}
product 1 embedded copy                {'_id': 'phones', 'name': 'Phones', 'path': 'Electronics > Phones', 'taxRate': 18, 'returnDays': 7}
products with a stale 'phones' copy    10000
"""
