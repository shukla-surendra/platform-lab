#!/usr/bin/env bash
# Connectivity tests for the transit gateway demo (curl from each instance, via SSM).
#
# Default (isolate_vpc_c=false): full mesh, all six directions reachable
#   (contrast with lesson 014 where A<->C was blocked).
# isolate_vpc_c=true: A<->B reachable; anything involving C blocked.
set -uo pipefail
cd "$(dirname "$0")/.."
source ../net_modules/scripts/lib.sh

A_ID=$(terraform output -raw a_instance_id); B_ID=$(terraform output -raw b_instance_id)
C_ID=$(terraform output -raw c_instance_id)
A_IP=$(terraform output -raw a_ip); B_IP=$(terraform output -raw b_ip); C_IP=$(terraform output -raw c_ip)
ISOLATED=$(terraform output -raw c_isolated)
MAIN_RT=$(terraform output -raw main_route_table_id)

echo "A=$A_IP  B=$B_IP  C=$C_IP   c_isolated=$ISOLATED"

echo; echo "== TGW route table 'main' (what the hub has learned)"
aws ec2 search-transit-gateway-routes --region "$REGION" --transit-gateway-route-table-id "$MAIN_RT" \
  --filters "Name=state,Values=active" \
  --query 'Routes[].{cidr:DestinationCidrBlock,type:Type,attachment:TransitGatewayAttachments[0].TransitGatewayAttachmentId}' \
  --output table

for id in "$A_ID" "$B_ID" "$C_ID"; do ssm_wait_online "$id" || exit 2; done
sleep 20

if [ "$ISOLATED" = "true" ]; then c_expect=blocked; else c_expect=reachable; fi

echo; echo "== A and B (always connected through the hub)"
check "A -> B  ($B_IP)" "$A_ID" "$B_IP" reachable
check "B -> A  ($A_IP)" "$B_ID" "$A_IP" reachable

echo; echo "== anything involving C (transitive via TGW; blocked if C is isolated)"
check "A -> C  ($C_IP)" "$A_ID" "$C_IP" "$c_expect"
check "C -> A  ($A_IP)" "$C_ID" "$A_IP" "$c_expect"
check "B -> C  ($C_IP)" "$B_ID" "$C_IP" "$c_expect"
check "C -> B  ($B_IP)" "$C_ID" "$B_IP" "$c_expect"

echo; summary
