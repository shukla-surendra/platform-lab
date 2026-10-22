"""
05 — FIX 3: SYNC IN THE BACKGROUND with a change stream (eventual consistency).

Story: the manager changes the master list and walks away. A helper is subscribed to
"master list changed" notifications and fixes the shelf copies right after.
For a short moment shelves are old. That's fine for a product name, NOT for money.

A change stream is a live feed of every change to a collection (needs a replica set).
Real systems run the watcher as a separate worker and store its "resume token"
so it continues where it stopped after a crash.
"""
import threading
import time

from common import mdb, seed_mongo, show

seed_mongo()
ready = threading.Event()


def sync_worker():
    with mdb.categories.watch(full_document="updateLookup") as stream:
        ready.set()
        for change in stream:
            cat = change["fullDocument"]
            fields = {f"categories.$[c].{k}": v for k, v in cat.items() if k != "_id"}
            r = mdb.products.update_many({"categories._id": cat["_id"]}, {"$set": fields},
                                         array_filters=[{"c._id": cat["_id"]}])
            show("  worker: fixed copies", r.modified_count)
            return


worker = threading.Thread(target=sync_worker)
worker.start()
ready.wait()

t = time.perf_counter()
mdb.categories.update_one({"_id": "phones"}, {"$set": {"name": "Mobile Phones"}})
show("right after the change, product 1 says", mdb.products.find_one({"_id": 1})["categories"][0]["name"])
worker.join()
show("after the worker, product 1 says", mdb.products.find_one({"_id": 1})["categories"][0]["name"])
show("stale window", f"{(time.perf_counter() - t) * 1000:.0f} ms")

"""
Real output:

right after the change, product 1 says Phones
  worker: fixed copies                 10000
after the worker, product 1 says       Mobile Phones
stale window                           70 ms
"""
