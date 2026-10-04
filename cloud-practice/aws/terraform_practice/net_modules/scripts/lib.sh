#!/usr/bin/env bash
# Shared helpers for the networking demos. Source this file; do not run it.
#   ssm_wait_online <instance-id>
#   ssm_exec <instance-id> "<shell command>"       -> prints the command output
#   check <description> <from-instance-id> <target-ip> <reachable|blocked>
#   summary                                         -> prints totals, exit 1 if any FAIL
# Needs: aws CLI v2, python3. Instances need the SSM agent + AmazonSSMManagedInstanceCore.

REGION="${AWS_REGION:-us-east-1}"
PASS=0
FAIL=0

ssm_wait_online() {
  local id="$1" i
  printf 'waiting for %s to register with SSM' "$id"
  for i in $(seq 1 40); do
    local st
    st=$(aws ssm describe-instance-information --region "$REGION" \
      --filters "Key=InstanceIds,Values=$id" \
      --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)
    if [ "$st" = "Online" ]; then echo " online"; return 0; fi
    printf '.'; sleep 6
  done
  echo " TIMEOUT (instance never became SSM-managed; check role, outbound path, agent)"
  return 1
}

ssm_exec() {
  local id="$1" cmd="$2" params cid st i
  params=$(python3 -c 'import json,sys; print(json.dumps({"commands":[sys.argv[1]]}))' "$cmd")
  cid=$(aws ssm send-command --region "$REGION" --instance-ids "$id" \
        --document-name AWS-RunShellScript --parameters "$params" \
        --query 'Command.CommandId' --output text) || return 1
  for i in $(seq 1 30); do
    st=$(aws ssm get-command-invocation --region "$REGION" --command-id "$cid" \
             --instance-id "$id" --query 'Status' --output text 2>/dev/null || echo Pending)
    case "$st" in
      Pending|InProgress|Delayed) sleep 2 ;;
      *) break ;;
    esac
  done
  aws ssm get-command-invocation --region "$REGION" --command-id "$cid" --instance-id "$id" \
    --query '[StandardOutputContent,StandardErrorContent]' --output text 2>/dev/null
}

# check "A -> B" <from-id> <to-ip> <reachable|blocked>
check() {
  local desc="$1" from="$2" ip="$3" expect="$4" code result
  code=$(ssm_exec "$from" "curl -s -m 5 -o /dev/null -w '%{http_code}' http://$ip/ || true" | head -1 | tr -d '[:space:]')
  if [ "$code" = "200" ]; then result=reachable; else result=blocked; fi
  if [ "$result" = "$expect" ]; then
    printf 'PASS  %-34s expected %-9s got %-9s (http %s)\n' "$desc" "$expect" "$result" "${code:-none}"
    PASS=$((PASS+1))
  else
    printf 'FAIL  %-34s expected %-9s got %-9s (http %s)\n' "$desc" "$expect" "$result" "${code:-none}"
    FAIL=$((FAIL+1))
  fi
}

summary() {
  echo "----"; echo "passed: $PASS  failed: $FAIL"
  [ "$FAIL" -eq 0 ]
}
