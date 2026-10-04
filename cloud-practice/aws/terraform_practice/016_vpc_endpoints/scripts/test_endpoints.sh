#!/usr/bin/env bash
# Tests for the VPC endpoints demo. Part 1 inspects AWS from your laptop; part 2
# runs commands ON the private instance (via SSM, which itself rides on the
# interface endpoints).
set -uo pipefail
cd "$(dirname "$0")/.."
source ../net_modules/scripts/lib.sh

ID=$(terraform output -raw instance_id)
ALLOWED=$(terraform output -raw allowed_bucket)
DENIED=$(terraform output -raw denied_bucket)
RT=$(terraform output -raw route_table_id)
S3EP=$(terraform output -raw s3_endpoint_id)
IFACE=$(terraform output -raw interface_endpoints)

expect() {  # expect "<desc>" "<command output>" "<substring that must appear>"
  if printf '%s' "$2" | grep -qiE "$3"; then
    printf 'PASS  %s\n' "$1"; PASS=$((PASS+1))
  else
    printf 'FAIL  %s   (wanted /%s/, got: %s)\n' "$1" "$3" "$(printf '%s' "$2" | head -2 | tr '\n' ' ')"; FAIL=$((FAIL+1))
  fi
}

echo "== Part 1: what AWS says (from your laptop)"
echo "-- route table: look for a 'pl-...' destination pointing at the vpce (the gateway endpoint)"
aws ec2 describe-route-tables --region "$REGION" --route-table-ids "$RT" \
  --query 'RouteTables[0].Routes[].{dest:DestinationCidrBlock,prefixlist:DestinationPrefixListId,target:GatewayId}' --output table
out=$(aws ec2 describe-route-tables --region "$REGION" --route-table-ids "$RT" --output text)
expect "route table has the S3 gateway endpoint route ($S3EP)" "$out" "$S3EP"
expect "route table has NO internet gateway route"             "$(printf '%s' "$out" | grep -c 'igw-' || true)" '^0$'

echo "-- endpoints"
aws ec2 describe-vpc-endpoints --region "$REGION" \
  --filters "Name=vpc-endpoint-state,Values=available,pending" "Name=tag:Project,Values=endpoints-lab" \
  --query 'VpcEndpoints[].{service:ServiceName,type:VpcEndpointType,state:State,privateDns:PrivateDnsEnabled}' --output table

echo "-- control: from your laptop (no endpoint involved) the 'denied' bucket is readable by YOUR credentials"
laptop=$(aws s3 ls "s3://$DENIED" --region "$REGION" 2>&1)
expect "laptop can list the denied bucket (so it is the endpoint policy that blocks the instance)" "$laptop" 'test\.txt'

echo; echo "== Part 2: from inside the private instance (via SSM)"
ssm_wait_online "$ID" || { echo "instance not reachable via SSM (expected when interface endpoints are disabled: interface_endpoints=$IFACE)"; exit 2; }

out=$(ssm_exec "$ID" "getent hosts ssm.$REGION.amazonaws.com")
expect "ssm hostname resolves to a PRIVATE IP (interface endpoint, private DNS)" "$out" '^10\.50\.'

out=$(ssm_exec "$ID" "curl -s -m 6 -o /dev/null -w 'http_%{http_code}' https://example.com || true")
expect "no internet: curl https://example.com fails" "$out" 'http_000'

out=$(ssm_exec "$ID" "export AWS_DEFAULT_REGION=$REGION; aws s3 ls s3://$ALLOWED 2>&1")
expect "S3 allowed bucket readable through the gateway endpoint" "$out" 'test\.txt'

out=$(ssm_exec "$ID" "export AWS_DEFAULT_REGION=$REGION; aws s3 ls s3://$DENIED 2>&1")
expect "S3 denied bucket blocked by the ENDPOINT policy (role allows it)" "$out" 'AccessDenied|denied|403'

echo; summary
