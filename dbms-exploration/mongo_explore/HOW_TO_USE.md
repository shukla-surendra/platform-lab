# How to use this lab

You only need **Docker**. MongoDB and its shell (`mongosh`) both run inside a container.

## 1. Start it (once per day)

```bash
cd ~/projects/2026/platform-lab/dbms-exploration/mongo_explore
make up
```
This starts MongoDB 7 on port **27018** and loads the fake shop (1,000 users, 200 products,
300,000 orders). You should see:
```
 Container mongo_explore-mongo-1 Healthy
users 1000, products 200, orders 300000
```

## 2. Run a lesson

```bash
make run L=03          # runs 03_index_basics.js
```
```
### 03_index_basics.js
userId = 42, no index              COLLSCAN                     keys=0 docs=300000 returned=300 ms=47
userId = 42, index {userId:1}      FETCH <- IXSCAN              keys=300 docs=300 returned=300 ms=1
...
```

The study loop for each lesson:
1. **Open the `.js` file** in your editor and read the story comment at the top.
2. **Read the code**: it's ~20–40 lines, one idea.
3. **Run it** with `make run L=NN`.
4. **Compare** with the "Real output" block at the bottom of the file. Numbers like `ms=` will
   differ a bit; `docs=` and `keys=` should match.
5. **Change something** (a filter, the index order, a value) and run it again.

Go in order: 01 → 10. Then read the docs: `schema_design.md` → `access_patterns.md` →
`indexes.md` → `postgres_vs_mongo.md`.

## 3. How to read a result line

Most lessons print one line per query using `plan()` from `lib.js`:

```
E-S-R {userId,createdAt,total}     LIMIT <- FETCH <- IXSCAN     keys=25 docs=20 returned=20 ms=1
└── what was tried                 └── how Mongo did it         └── how much work it did
```
| Part | Meaning | Good sign |
|---|---|---|
| `IXSCAN` / `COLLSCAN` | used an index / read every document | IXSCAN |
| `SORT` | sorted in memory (no index for the sort) | absent |
| `IDHACK` | looked up directly by `_id` | fastest |
| `keys=` | index entries read | close to `returned` |
| `docs=` | documents read | close to `returned` (0 = covered query) |
| `ms=` | time taken | small |

Read the stages **right to left**: `LIMIT <- FETCH <- IXSCAN` = scan index → fetch docs → keep 20.

## 4. Play in the interactive shell

```bash
make shell
```
```js
shop> show collections
shop> db.orders.findOne()
shop> db.orders.find({ userId: 42 }).limit(3)
shop> db.orders.getIndexes()
shop> load("/lab/lib.js")                                    // gives you plan()
shop> plan("my test", db.orders.find({ city: "Pune" }))
shop> db.orders.createIndex({ city: 1 })
shop> plan("my test again", db.orders.find({ city: "Pune" }))
shop> load("/lab/07_aggregation.js")                         // run a whole lesson in here
shop> exit
```

## 5. Write your own script

Copy any lesson as a starting point:
```bash
cp 03_index_basics.js 99_my_try.js       # edit it, then:
make run L=99
```
Keep these two lines at the top, because every script needs them:
```js
load("/lab/lib.js");                 // plan() and show()
db = db.getSiblingDB("shop");        // pick the database
```

## 6. All commands

| Command | Does |
|---|---|
| `make up` | start Mongo + load data |
| `make list` | list lessons |
| `make run L=05` | run one lesson |
| `make all` | run all lessons in order |
| `make shell` | interactive shell on `shop` |
| `make seed` | reload data from scratch |
| `make down` | stop and delete the container |

Without `make` (same thing, by hand):
```bash
docker compose up -d --wait
docker compose exec mongo mongosh --quiet /lab/seed.js
docker compose exec mongo mongosh --quiet /lab/05_covered_multikey_partial.js
docker compose exec mongo mongosh shop
```

## 7. Connect from a GUI or app (optional)

Connection string from your Mac:
```
mongodb://localhost:27018/shop?directConnection=true
```
Paste it into MongoDB Compass (free GUI: browse documents, see indexes, visual explain plans),
or use it from Python (`pymongo.MongoClient("...")`). `directConnection=true` is required
because the container's replica set calls itself `localhost:27017` internally.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `service "mongo" is not running` | `make up` |
| "file not found" when you pass a Mac path like `/Users/...` | scripts must be referenced as `/lab/<file>` (the path inside the container); `make run` does it for you |
| `node 03_....js` → `db is not defined` | these are mongosh scripts, not Node: use `make run` |
| numbers very different from "Real output" | a previous experiment left indexes/data behind → `make seed` |
| `port is already allocated` (27018) | something else uses it; change `"27018:27017"` in `docker-compose.yml` |
| `Transaction numbers are only allowed on a replica set` | the replica set wasn't initialised yet; wait a few seconds, or `make down && make up` |
| Computer feels slow | `make down` when you're finished (data is reloaded by `make up` anyway) |
