"""Connections shared by every script. Nothing to learn here."""
from pymongo import MongoClient

# directConnection: the replica set calls itself localhost:27017 inside the container
mongo = MongoClient("mongodb://localhost:27019/?directConnection=true")
mdb = mongo["shop"]


def show(label, value):
    print(f"{label:<38} {value}")


# The scenario used by every script:
# a category has several attributes, and each product embeds a COPY of the 2 categories it
# belongs to, because the product page always shows them together.
CATEGORIES = [
    {"_id": "phones", "name": "Phones", "path": "Electronics > Phones", "taxRate": 18, "returnDays": 7},
    {"_id": "laptops", "name": "Laptops", "path": "Electronics > Laptops", "taxRate": 18, "returnDays": 10},
    {"_id": "sale", "name": "Sale", "path": "Offers > Sale", "taxRate": 0, "returnDays": 0},
]


def seed_mongo(n_products=20_000):
    mdb.drop_collection("categories")
    mdb.drop_collection("products")
    mdb.drop_collection("orders")
    mdb.categories.insert_many(CATEGORIES)
    cats = {c["_id"]: c for c in CATEGORIES}
    mdb.products.insert_many([
        {"_id": i, "name": f"product{i}", "price": 1000 + i % 500,
         # two embedded category copies per product (half phones, half laptops; every 4th on sale)
         "categories": [cats["phones" if i % 2 else "laptops"]] + ([cats["sale"]] if i % 4 == 0 else [])}
        for i in range(1, n_products + 1)
    ])
    mdb.products.create_index("categories._id")
