"""Redis Cluster's sharp edge: multi-key commands only work if every key in
the command hashes to the *same* slot. This demonstrates the failure, then
the fix (hash tags), and proves the fix by checking both keys actually
co-locate on one node.

Run inside the cluster's own docker network:
    docker compose exec client python crossslot_and_hashtags.py
"""

from redis.cluster import RedisCluster
from redis.exceptions import RedisClusterException

rc = RedisCluster(host="172.30.0.11", port=7001, decode_responses=True)

print("Attempt 1: MSET two ordinary keys in one command...")
try:
    rc.mset({"order:1001": "pending", "order:1002": "pending"})
    print("  (unexpectedly succeeded — got lucky and both hashed to the "
          "same slot; re-run to see it fail)")
except RedisClusterException as e:
    print(f"  FAILED as expected: {e}")
    print("  Why: MSET is sent as one command to one node. Redis computes "
          "CRC16(key) % 16384 per key — two different keys almost always "
          "land in two different slots, which could mean two different "
          "nodes. A single node can't atomically write a key it doesn't "
          "own, so the command can't be split across nodes and is refused. "
          "redis-py's cluster client catches this client-side before ever "
          "sending the command (RedisClusterException) — a bare redis-cli "
          "against a real node would instead round-trip and get the "
          "server's own '(error) CROSSSLOT Keys in request don't hash to "
          "the same slot' back. Different client libraries pick one "
          "behavior or the other; both mean the same underlying rule.")

print()
print("Attempt 2: same idea, but with a hash tag — {order:1001} in both "
      "keys forces Redis to hash only the {...} substring, so both keys "
      "collapse onto the same slot on purpose:")
key_a = "{order:1001}:status"
key_b = "{order:1001}:items"
rc.mset({key_a: "pending", key_b: "sku-42,sku-91"})
print(f"  MSET {key_a} {key_b} -> succeeded")

slot_a = rc.keyslot(key_a)
slot_b = rc.keyslot(key_b)
node_a = rc.get_node_from_key(key_a)
node_b = rc.get_node_from_key(key_b)
print(f"  slot({key_a}) = {slot_a}, owner = {node_a.host}:{node_a.port}")
print(f"  slot({key_b}) = {slot_b}, owner = {node_b.host}:{node_b.port}")

assert slot_a == slot_b, "hash-tagged keys must land in the same slot"
assert (node_a.host, node_a.port) == (node_b.host, node_b.port)
print("\nconfirmed: hash tags put related keys on the same node, which is "
      "exactly what lets MSET (and any other multi-key op, e.g. a Lua "
      "script or MULTI/EXEC transaction touching both) work in a sharded "
      "cluster — at the cost of giving up automatic even distribution for "
      "that key family.")

rc.close()
