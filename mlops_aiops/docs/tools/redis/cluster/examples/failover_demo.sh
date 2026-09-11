#!/usr/bin/env bash
# Kill a master mid-cluster and watch a replica get promoted automatically —
# no human, no orchestrator outside the cluster itself. This is the actual
# payoff of running 3 masters + 3 replicas instead of 3 bare masters.
#
# Run from the cluster/ directory (needs docker compose, not the client
# container — it stops/starts containers):
#   bash examples/failover_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Cluster state before ==="
docker exec redis-cluster-1 redis-cli -p 7001 cluster nodes | sort -k2

MASTER_KEY="failover-test-key"
docker exec redis-cluster-client python -c "
from redis.cluster import RedisCluster
rc = RedisCluster(host='172.30.0.11', port=7001, decode_responses=True)
rc.set('$MASTER_KEY', 'written-before-failover')
node = rc.get_node_from_key('$MASTER_KEY')
print(f'  wrote {\"$MASTER_KEY\"} via master {node.host}:{node.port}')
"

echo
echo "=== Killing redis-cluster-1 (a master) — simulating a crashed node ==="
docker kill redis-cluster-1 >/dev/null
echo "  redis-cluster-1 is down."

echo
echo "Waiting for the cluster to detect the failure and promote a replica"
echo "(cluster-node-timeout is 5000ms, so this takes a few seconds — the"
echo "surviving nodes have to stop hearing gossip heartbeats from it, agree"
echo "a majority of masters see it as failed, then a replica of the dead"
echo "master promotes itself)..."

for i in $(seq 1 15); do
  sleep 2
  STATE=$(docker exec redis-cluster-2 redis-cli -p 7002 cluster nodes 2>/dev/null | grep '172.30.0.11' || true)
  if echo "$STATE" | grep -q "master,fail"; then
    echo "  [${i}] 172.30.0.11 (old master) now marked: fail"
  fi
  PROMOTED=$(docker exec redis-cluster-2 redis-cli -p 7002 cluster nodes 2>/dev/null | grep '172.30.0.15' | grep master || true)
  if [ -n "$PROMOTED" ]; then
    echo "  [${i}] 172.30.0.15 (was a replica) is now: master"
    break
  fi
done

echo
echo "=== Cluster state after failover ==="
docker exec redis-cluster-2 redis-cli -p 7002 cluster nodes | sort -k2

echo
echo "=== Confirming writes still work (new master serves the old key) ==="
docker exec redis-cluster-client python -c "
from redis.cluster import RedisCluster
rc = RedisCluster(host='172.30.0.12', port=7002, decode_responses=True)
val = rc.get('$MASTER_KEY')
print(f'  GET $MASTER_KEY -> {val!r}')
assert val == 'written-before-failover', 'data lost across failover!'
rc.set('$MASTER_KEY-after', 'written-after-failover')
print('  new write after failover succeeded — cluster is fully writable again')
"

echo
echo "=== Restoring redis-cluster-1 (it rejoins as a replica, not master —"
echo "    172.30.0.15 already holds that master role now) ==="
docker start redis-cluster-1 >/dev/null
sleep 3
docker exec redis-cluster-1 redis-cli -p 7001 cluster nodes | sort -k2
