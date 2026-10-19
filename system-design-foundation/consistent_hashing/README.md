# Consistent Hashing

Notes-to-self on the sharding/load-balancing technique used by Dynamo,
Cassandra, memcached clients, CDNs, and most distributed caches — and a
runnable demo proving *why* it's needed.

## The problem: naive hashing (`hash(key) % N`)

The obvious way to shard is `shard = hash(key) % N`. The bug is that `N` is
baked directly into the formula, so **any** change to the node count changes
almost every key's result — not just the keys that should move.

Worked example, `hash(key) = 17`:

| N (node count) | `17 % N` | shard |
|---|---|---|
| 4 | `17 % 4` | **1** |
| 5 (added a node) | `17 % 5` | **2** |

The key didn't need to move — no node it cared about changed — but the
modulo result changed anyway, purely because the divisor changed. Multiply
that across every key in the system and you get the numbers in the demo
below: adding a 5th node to a 4-node naive setup remaps **~80% of all keys**.
For a cache, that's a near-total flush (mass cache misses hitting your
database all at once); for a data store, it's a full re-migration — all
triggered by adding *one* server.

## The fix: consistent hashing

Stop depending on `N`. Instead, place both **nodes** and **keys** as points
on a fixed circular hash space (a **ring**, `0` to `2^64-1` here, built from
SHA-256 so it never depends on how many nodes exist). A key belongs to
whichever node's point is the next one **clockwise** from the key's own
position on the ring (`ConsistentHashRing.get_node` — a `bisect` lookup).

Why that one change fixes everything: when a new node is added, its points
land at effectively random spots on the ring. Only the keys whose
next-clockwise neighbor *used to be* some other node but is now this new
node get reassigned — every other key's next-clockwise neighbor never
changed, so it isn't touched. Removing a node is the mirror image: only that
node's own keys move, to whichever node is next clockwise after it. No key
ever jumps between two nodes that were already there — moves only ever
involve the node being added or removed.

## Files

| File | What it is |
|---|---|
| `consistent_hashing.py` | The implementation: `ConsistentHashRing` (add/remove nodes, look up a key's node, look up N distinct nodes for replication) and `Node` (name + weight). Uses SHA-256 for a stable hash and **virtual nodes** (150 points per node by default) so the keyspace stays balanced instead of landing in a few lumpy arcs. |
| `demo_consistent_hashing.py` | Side-by-side comparison: naive `hash(key) % N` vs. this ring, both under a node being added, plus a node being removed. Prints how many keys move in each case. |

## Run it

```bash
python3 demo_consistent_hashing.py
```

Sample output (10,000 keys, 4 → 5 nodes):

```
NAIVE HASHING: shard = hash(key) % N
Keys that moved to a different shard: 7,973 / 10,000 (79.7%)

CONSISTENT HASHING: ring with virtual nodes
Keys that moved to a different shard: 2,086 / 10,000 (20.9%)
Of those, moved specifically onto the new node: 2,086
```

Naive hashing reshuffles ~80% of keys. Consistent hashing moves only the new
node's fair share (~1/5, since there are now 5 nodes) — and every key that
moves goes *to* the new node, never between two pre-existing nodes.

## Using it directly

```python
from consistent_hashing import ConsistentHashRing, Node

ring = ConsistentHashRing([Node("shard-a"), Node("shard-b"), Node("shard-c")])

ring.get_node("user:42")              # -> which node owns this key
ring.get_nodes("user:42", count=3)    # -> 3 distinct nodes, for replication

ring.add_node(Node("shard-d"))        # only shard-d's fair share moves
ring.remove_node("shard-a")           # only shard-a's keys move, to their
                                       # next-clockwise neighbor

Node("shard-e", weight=3)             # gets 3x the ring points -> 3x the keys
```

## Key ideas worth remembering

- **Ring + clockwise lookup** replaces `% N`, so node count changes are
  local, not global.
- **Virtual nodes** (many points per physical node) smooth out load —
  without them, one unlucky node placement can own a huge arc of the ring.
- **Weight** scales a node's virtual-node count, so heterogeneous hardware
  (a bigger box) can take a proportionally bigger share.
- **Replica lookup** (`get_nodes`, walk clockwise collecting distinct nodes)
  is how systems like Dynamo pick N replicas for a key without a second
  data structure.
