"""Demonstrates the problem consistent hashing solves: naive `hash(key) % N`
sharding remaps almost every key when N changes, because N is baked into the
formula. Consistent hashing only remaps the keys that "belong" to the node
being added or removed.

Run: python3 demo_consistent_hashing.py
"""

from consistent_hashing import ConsistentHashRing, Node, _hash

KEYS = [f"user:{i}" for i in range(10_000)]


def naive_shard(key: str, node_count: int) -> int:
    return _hash(key) % node_count


def demo_naive_hashing() -> None:
    print("=" * 70)
    print("NAIVE HASHING: shard = hash(key) % N")
    print("=" * 70)

    before = {k: naive_shard(k, 4) for k in KEYS}
    after = {k: naive_shard(k, 5) for k in KEYS}  # one node added, N: 4 -> 5

    moved = sum(1 for k in KEYS if before[k] != after[k])
    print(f"Nodes: 4 -> 5 (added one node)")
    print(f"Keys that moved to a different shard: {moved:,} / {len(KEYS):,} "
          f"({moved / len(KEYS):.1%})")
    print("Almost every key gets reassigned, because %-N shifts the whole")
    print("formula, not just the new node's fair share. In production this")
    print("means a near-total cache flush / data reshuffle for one node add.")
    print()


def demo_consistent_hashing() -> None:
    print("=" * 70)
    print("CONSISTENT HASHING: ring with virtual nodes")
    print("=" * 70)

    ring = ConsistentHashRing([Node("shard-a"), Node("shard-b"),
                                Node("shard-c"), Node("shard-d")])
    before = {k: ring.get_node(k) for k in KEYS}

    ring.add_node(Node("shard-e"))  # one node added
    after = {k: ring.get_node(k) for k in KEYS}

    moved = sum(1 for k in KEYS if before[k] != after[k])
    moved_to_new_node = sum(1 for k in KEYS if after[k] == "shard-e")
    stayed_but_would_have_moved_naively = len(KEYS) - moved

    print(f"Nodes: 4 -> 5 (added shard-e)")
    print(f"Keys that moved to a different shard: {moved:,} / {len(KEYS):,} "
          f"({moved / len(KEYS):.1%})")
    print(f"Of those, moved specifically onto the new node: {moved_to_new_node:,}")
    print(f"Keys left untouched: {stayed_but_would_have_moved_naively:,}")
    print()
    print("Only ~1/5 of keys move (the new node's fair share) and every key")
    print("that moves goes TO the new node -- no key ever moves BETWEEN two")
    print("pre-existing nodes. That's the property that makes cache/shard")
    print("rebalancing cheap: adding a node only steals its share, it doesn't")
    print("scramble everyone else's assignments.")
    print()


def demo_removal() -> None:
    print("=" * 70)
    print("CONSISTENT HASHING: removing a node (e.g. it crashed)")
    print("=" * 70)

    ring = ConsistentHashRing([Node("shard-a"), Node("shard-b"),
                                Node("shard-c"), Node("shard-d")])
    before = {k: ring.get_node(k) for k in KEYS}
    ring.remove_node("shard-d")
    after = {k: ring.get_node(k) for k in KEYS}

    moved = sum(1 for k in KEYS if before[k] != after[k])
    print(f"Keys reassigned after removing shard-d: {moved:,} / {len(KEYS):,} "
          f"({moved / len(KEYS):.1%})")
    print("Only shard-d's own keys move (to their next clockwise neighbor on")
    print("the ring) -- every other node's keys are untouched.")
    print()


if __name__ == "__main__":
    demo_naive_hashing()
    demo_consistent_hashing()
    demo_removal()
