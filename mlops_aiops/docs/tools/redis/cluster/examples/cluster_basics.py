"""Connect to the cluster like a real client has to: give it *one* seed node,
and let the client discover the other 5 via CLUSTER SLOTS. Then write a batch
of keys and show they land on different masters purely by hash-slot — nobody
picked which node any of this goes to.

Run inside the cluster's own docker network (see README.md "Why a client
container"):
    docker compose exec client python cluster_basics.py
"""

from collections import Counter

from redis.cluster import RedisCluster

# A real client only needs ONE reachable node to bootstrap — RedisCluster
# calls CLUSTER SLOTS against it and learns the other 5 nodes + the full
# slot map from that single reply. This is different from e.g. a plain list
# of memcached hosts: cluster topology is discovered, not hand-configured.
rc = RedisCluster(host="172.30.0.11", port=7001, decode_responses=True)

print("Discovered cluster topology (from one seed node):")
for node in sorted(rc.get_primaries(), key=lambda n: n.port):
    print(f"  master {node.host}:{node.port}")

print()
print("Writing 300 keys, then checking which node each landed on...")
owner_of_key = {}
for i in range(300):
    key = f"user:{i}:profile"
    rc.set(key, f"profile-data-{i}")
    # get_node_from_key resolves the same CRC16(key) % 16384 -> slot -> node
    # routing the client used internally to send that SET.
    node = rc.get_node_from_key(key)
    owner_of_key[key] = f"{node.host}:{node.port}"

counts = Counter(owner_of_key.values())
print("\nKey distribution across masters:")
for node_addr, n in sorted(counts.items()):
    bar = "#" * (n // 5)
    print(f"  {node_addr:>18}  {n:>3} keys  {bar}")

assert len(counts) == 3, "expected keys spread across all 3 masters"
print("\nconfirmed: keys distributed across all 3 masters via hash slots, "
      "no client-side node selection")

print()
print("Reading one key back — client routes GET to the exact node that owns")
print("its slot, transparently:")
sample_key = "user:0:profile"
print(f"  GET {sample_key} -> {rc.get(sample_key)!r} "
      f"(served by {owner_of_key[sample_key]})")

rc.close()
