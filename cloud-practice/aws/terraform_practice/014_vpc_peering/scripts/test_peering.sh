#!/usr/bin/env bash
# Connectivity tests for the peering demo. Runs curl FROM each instance (via SSM)
# to the other instances' PRIVATE IPs and compares with what should happen.
#
# Expected (default config, enable_routes=true):
#   A->B ok, B->A ok, B->C ok, C->B ok, A->C BLOCKED, C->A BLOCKED  (not transitive)
# With enable_routes=false: everything BLOCKED (peering without routes).
# try_transitive_route=true does not change anything: A<->C stays BLOCKED.
set -uo pipefail
cd "$(dirname "$0")/.."
source ../net_modules/scripts/lib.sh

A_ID=$(terraform output -raw a_instance_id); B_ID=$(terraform output -raw b_instance_id)
C_ID=$(terraform output -raw c_instance_id)
A_IP=$(terraform output -raw a_ip); B_IP=$(terraform output -raw b_ip); C_IP=$(terraform output -raw c_ip)
ROUTES=$(terraform output -raw routes_enabled)

echo "A=$A_IP  B=$B_IP  C=$C_IP   routes_enabled=$ROUTES"
for id in "$A_ID" "$B_ID" "$C_ID"; do ssm_wait_online "$id" || exit 2; done
sleep 20   # let the tiny web servers (user_data) finish starting

if [ "$ROUTES" = "true" ]; then direct=reachable; else direct=blocked; fi

echo; echo "== directly peered pairs"
check "A -> B  ($B_IP)" "$A_ID" "$B_IP" "$direct"
check "B -> A  ($A_IP)" "$B_ID" "$A_IP" "$direct"
check "B -> C  ($C_IP)" "$B_ID" "$C_IP" "$direct"
check "C -> B  ($B_IP)" "$C_ID" "$B_IP" "$direct"

echo; echo "== NOT peered: peering is not transitive (always blocked)"
check "A -> C  ($C_IP)" "$A_ID" "$C_IP" blocked
check "C -> A  ($A_IP)" "$C_ID" "$A_IP" blocked

echo; summary
