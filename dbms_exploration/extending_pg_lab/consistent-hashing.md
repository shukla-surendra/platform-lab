# Consistent Hashing — Design Interview Notes

## 1. The problem it solves

Suppose we distribute keys across `N` nodes using:

```text
node = hash(key) % N
```

This works as long as `N` stays constant.

The problem appears when the cluster changes.

For example:

```text
4 nodes → hash(key) % 4
5 nodes → hash(key) % 5
```

Because the modulus changed, many keys now map to different nodes. That means a large amount of data may need to move.

### Why is this a problem?

Imagine 1 million keys distributed across 4 nodes:

```text
Node A → 250K keys
Node B → 250K keys
Node C → 250K keys
Node D → 250K keys
```

Now add Node E.

With modulo hashing:

```text
hash(key) % 4
        ↓
hash(key) % 5
```

A large fraction of keys can map to different nodes, causing significant data movement.

### What consistent hashing solves

Consistent hashing is designed to minimize data movement when nodes join or leave.

When a node joins, only the keys in the ranges transferred to that node need to move.

When a node leaves, only the keys previously owned by that node need to move.

For a node joining a cluster with `N` existing nodes, the expected fraction of keys that move is approximately:

```text
1 / (N + 1)
```

rather than almost all keys.

---

## 2. The ring

Instead of using modulo-based buckets, consistent hashing places both **nodes** and **keys** into the same circular hash space.

The hash space is commonly represented as:

```text
0 -------------------------- 2^32 - 1
```

and visualized as a ring:

```text
                    0 / 2^32
                       │
              ┌────────┼────────┐
              │                 │
         Node D                 Node A
              │                 │
              │     RING        │
              │                 │
         Node C                 Node B
              │                 │
              └────────┼────────┘
                       │
```

### Placement rule

A key belongs to the **first node found while walking clockwise from the key's position**.

For example:

```text
        A                 B
        ●-----------------●
         \               /
          \      K      /
           \     ●     /
            \         /
             ●-------●
             D       C
```

If walking clockwise from `K` reaches `C` first:

```text
K → C
```

Therefore, **C owns key K**.

---

## 3. What happens when a node joins?

Suppose the ring initially contains:

```text
A → B → C → D
```

Now node `E` joins between `C` and `D`:

```text
Before:

C ---------------- D
      keys owned by D


After:

C -------- E -------- D
      ↑
   transferred
   key range
```

Node `E` takes ownership of the portion of the keyspace immediately counter-clockwise from it, which was previously owned by `D`.

Therefore:

```text
Before:

D → keys in that range

After:

E → keys in that range
```

Only that affected portion moves.

Everything else stays where it is.

---

## 4. What happens when a node leaves?

Suppose:

```text
A → B → C → D
```

and `C` leaves.

Its key range is transferred to the next appropriate node according to the ring's ownership rule.

Conceptually:

```text
Before:

B -------- C -------- D
          keys


After:

B ------------------- D
       transferred
         keys
```

Again, the entire dataset does not need to be remapped.

---

## 5. The core benefit

The key property is:

> **Node membership changes affect only a small portion of the keyspace instead of remapping almost every key.**

This is why consistent hashing is useful in distributed systems.

### Modulo hashing

```text
N = 4

hash(key) % 4
      ↓
Node 0 / 1 / 2 / 3

N = 5

hash(key) % 5
      ↓
Node 0 / 1 / 2 / 3 / 4

Many keys change owners
```

### Consistent hashing

```text
Node joins
    ↓
New node takes a portion of the ring
    ↓
Only keys in that portion move
    ↓
Other keys remain where they are
```

---

# 6. Virtual nodes (vnodes)

Hashing each physical node to only one point on the ring creates two major problems:

1. **Uneven load**
2. **Large and uneven ownership ranges**

Random node positions may produce something like:

```text
A ─────────────────────── B ── C ───────────── D
        large range             small range
```

Node A might own a much larger portion of the keyspace than Node C.

## Solution: virtual nodes

Instead of placing each physical node at one point, represent each physical node using **many virtual nodes (vnodes/tokens)** distributed around the ring.

For example:

```text
Physical Node A
    ├── A#1
    ├── A#2
    ├── A#3
    └── ...

Physical Node B
    ├── B#1
    ├── B#2
    ├── B#3
    └── ...
```

Visually:

```text
A#1 ---- B#2 ---- A#7 ---- C#3 ---- B#9 ---- A#4 ---- C#8
```

The physical nodes therefore own many small portions of the ring.

### Why vnodes help

#### 1. Better load distribution

With more vnodes, ownership is spread across many small portions of the ring.

Statistically, this tends to make the total ownership of each physical node more balanced.

This is related to the **law of large numbers**.

#### 2. More granular rebalancing

When a physical node leaves:

```text
A has many vnodes

A#1
A#4
A#7
A#12
...
```

Its ownership is spread across many parts of the ring.

Those small ranges can be reclaimed by multiple peers instead of one large range moving to a single neighbor.

#### 3. Heterogeneous hardware

You can give a more powerful physical node more vnodes:

```text
Small node:
100 vnodes

Large node:
200 vnodes
```

The larger node can therefore own a larger fraction of the keyspace.

### Important distinction

```text
Number of vnodes
        ≠
Replication factor
```

**Vnodes** answer:

> How finely is ownership divided?

**Replication factor** answers:

> How many physical copies of the data do we keep?

---

# 7. Replication on the ring

Consistent hashing determines **data ownership**.

Replication is a separate mechanism used for **fault tolerance and availability**.

A common Dynamo/Cassandra-style approach is to replicate a key to the next `R` distinct physical nodes walking clockwise around the ring.

For example, with replication factor `R = 3`:

```text
Key K
  │
  ├── Primary → Node A
  ├── Replica → Node B
  └── Replica → Node C
```

The important word is **distinct physical nodes**.

A physical node may have many vnodes:

```text
Node A
 ├── A#1
 ├── A#2
 └── A#3
```

You do not want:

```text
A#1 → A#2 → A#3
```

to count as three replicas because they are all on the same physical machine.

Instead:

```text
A#1 → Node A
B#2 → Node B
C#3 → Node C
```

counts as three distinct physical nodes.

### Mental model

```text
Consistent hashing
        ↓
Which node owns the key?

Replication
        ↓
Which additional nodes store copies?
```

---

# 8. Consistent hashing does NOT automatically solve hot keys

This is an important interview distinction.

Consistent hashing can balance **ownership of the keyspace**, but it does not necessarily balance **request traffic**.

For example:

```text
Node A → 33% of keyspace
Node B → 33% of keyspace
Node C → 34% of keyspace
```

The ring looks perfectly balanced.

But suppose one key becomes extremely popular:

```text
Key = celebrity_user

10 million requests
        ↓
      Node B
        ↓
   🔥 HOT NODE
```

Even though the keyspace is balanced, one key can create a traffic hotspot.

### Therefore

> **Consistent hashing balances data ownership; it does not automatically balance request traffic.**

Hot-key mitigation may require techniques such as:

- Request-level load balancing
- Caching
- Replicating particularly hot data
- Splitting/striping hot keys where appropriate

---

# 9. Rebalancing is not free

The statement:

> "Only a small fraction of keys move"

describes **how much ownership changes**, not how easy or instantaneous the migration is.

During migration, a distributed system must handle:

- Reads during movement
- Writes during movement
- Temporary ownership
- Failed transfers
- Duplicate copies
- Consistency
- Recovery

Different systems use different mechanisms, such as:

- Hinted handoff
- Read repair
- Streaming
- Background data movement

Therefore:

> **Consistent hashing minimizes data movement; it does not eliminate the complexity of data migration.**

---

# 10. Consistent hashing vs. range-based sharding

These approaches solve related problems but have different properties.

| | Consistent hashing | Range-based sharding |
|---|---|---|
| Placement | Hash-based | Key-range based |
| Keyspace | Circular hash space | Ordered ranges |
| Range queries | Poor locality | Excellent locality |
| Sequential keys | Distributed by hash | Can create hot ranges |
| Node changes | Small portion of keyspace affected | Requires range movement/splitting |
| Typical use | Distributed KV stores, caches | Relational/range-oriented systems |

### Example

Range sharding:

```text
Node A → IDs 1–1M
Node B → IDs 1M–2M
Node C → IDs 2M–3M
```

This is excellent for:

```sql
WHERE id BETWEEN 1000000 AND 1100000
```

But sequential writes can concentrate on the latest range:

```text
Node C
  ↑
  🔥 new IDs
```

Hash-based distribution spreads sequential IDs more evenly:

```text
hash(1) → Node B
hash(2) → Node A
hash(3) → Node C
hash(4) → Node A
...
```

but sacrifices natural range locality.

---

# 11. Consistent hashing vs. Citus-style sharding

This is especially useful when comparing consistent hashing with your PostgreSQL/Citus lab.

| | Consistent hashing | Citus-style distributed sharding |
|---|---|---|
| Data placement | Hash/ring based | Explicit shard metadata |
| Ownership | Determined by ring positions/tokens | Determined by shard metadata and placement |
| Adding node | New node can take ownership of portions of the keyspace | New node can be added and existing shards can be rebalanced onto it |
| Movement granularity | Token/vnode ranges | Physical shards |
| Metadata | Ring/token membership | Citus metadata catalog |
| Coordinator | Often peer-to-peer designs | Coordinator-based |
| Rebalancing | Depends on implementation | Explicit rebalancing operation |

### The key insight

Both approaches address the same fundamental problem:

> **How do we distribute data across nodes while minimizing data movement when the cluster changes?**

But they represent ownership differently.

```text
Consistent hashing:

Key
 ↓
Hash
 ↓
Ring position
 ↓
Next node/token
 ↓
Owner


Citus-style sharding:

Key
 ↓
Distribution function
 ↓
Shard
 ↓
Metadata catalog
 ↓
Worker node
```

Citus uses explicit metadata such as shard and placement information, which makes shard ownership observable and rebalancing controllable.

---

# 12. Important interview points

### If asked: "Why consistent hashing over modulo hashing?"

Answer:

> **Modulo hashing remaps a large fraction of keys when the number of nodes changes. Consistent hashing maps nodes and keys into a shared ring so that a node join or leave affects only a small portion of the keyspace.**

### If asked: "Does consistent hashing guarantee even distribution?"

Answer:

> **No. Basic consistent hashing can produce uneven ranges. Virtual nodes/tokens are used to improve statistical load distribution.**

### If asked: "Does it solve hot keys?"

Answer:

> **No. It balances keyspace ownership, not request frequency. A single extremely popular key can still overload one node.**

### If asked: "What does replication do?"

Answer:

> **Consistent hashing determines the primary owner; replication determines where additional copies are stored for fault tolerance and availability.**

### If asked: "What happens when a node joins?"

Answer:

> **The new node takes ownership of portions of the existing keyspace, so only those affected keys/ranges need to move.**

### If asked: "What happens when a node leaves?"

Answer:

> **Its owned ranges are transferred to other nodes, rather than remapping the entire dataset.**

---

# 13. 30-second interview answer

> **Consistent hashing is a technique for distributing keys across multiple nodes while minimizing data movement when nodes join or leave.**
>
> Instead of computing `hash(key) % N`, we place both nodes and keys in the same hash space, usually represented as a ring. A key is assigned to the next node clockwise.
>
> When a node joins or leaves, only the affected portions of the keyspace need to move instead of remapping almost every key.
>
> In practice, virtual nodes/tokens are used to improve load distribution and make rebalancing more granular.
>
> Consistent hashing solves data-placement stability; it does not by itself solve replication, hot keys, or request-load balancing.

---

# 14. Final mental model

```text
                         CONSISTENT HASHING
                                  │
                                  ↓
                    Stable data placement
                    when nodes change
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
              Hash the nodes              Hash the keys
                    │                           │
                    └─────────────┬─────────────┘
                                  ↓
                               RING
                                  │
                    key → next node clockwise
                                  │
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
               Node joins                  Node leaves
                    ↓                           ↓
             Small key range              Its range moves
                moves away                to another node
                    │                           │
                    └─────────────┬─────────────┘
                                  ↓
                              VNODES
                                  │
                    Better distribution
                    + granular movement
                                  │
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
              Replication                  Hot keys
              (fault tolerance)             (separate problem)
```
