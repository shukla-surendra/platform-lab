#!/usr/bin/env bash
# Example 01: deny all incoming traffic
#
#   ./demo.sh           create the app, test, apply the policy, test again
#   ./demo.sh cleanup   delete everything this example created
set -uo pipefail
cd "$(dirname "$0")"

NAMESPACES=(np-01)

STAGE_NAMES=("no policy" "apply the deny-all policy")
STAGE_CMDS=("" "kubectl apply -f policy.yaml")

# from-namespace  from-pod  test  target  port  expected-result-per-step
CHECKS=(
  "np-01 client tcp web 80 ok BLOCKED"
)

# ---------------------------------------------------------------------------
# Everything below is the same in every example folder.
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "cleanup" ]]; then
  kubectl delete namespace "${NAMESPACES[@]}" --ignore-not-found
  exit 0
fi

# probe <namespace> <pod> <tcp|dns> <target> [port]  ->  prints "ok" or "BLOCKED"
probe() {
  if [[ $3 == dns ]]; then
    kubectl -n "$1" exec "$2" -- nslookup -timeout=2 "$4" >/dev/null 2>&1
  else
    kubectl -n "$1" exec "$2" -- nc -z -w 2 "$4" "$5" >/dev/null 2>&1
  fi && echo ok || echo BLOCKED
}

# describe one check line for the table
describe() {
  local c=($1)
  if [[ ${c[2]} == dns ]]; then echo "${c[0]}/${c[1]} -> DNS lookup of ${c[3]%%.*}"
  elif [[ ${c[3]} =~ ^[0-9.]+$ ]]; then echo "${c[0]}/${c[1]} -> web's IP:${c[4]}"
  else echo "${c[0]}/${c[1]} -> ${c[3]%%.*}:${c[4]}"; fi
}

# Run every check for stage $1. Network rules can take a few seconds to apply,
# so retry for up to 90s until every result matches what's expected.
run_checks() {
  local stage=$1 deadline=$((SECONDS + 90)) results all c exp
  while :; do
    results=(); all=1
    for c in "${CHECKS[@]}"; do
      c=($c); exp=${c[$((5 + stage))]}
      got=$(probe "${c[0]}" "${c[1]}" "${c[2]}" "${c[3]}" "${c[4]}")
      results+=("$got"); [[ $got == "$exp" ]] || all=0
    done
    (( all )) && break
    (( SECONDS >= deadline )) && break
    sleep 5
  done
  printf "   %-44s %-9s %-9s\n" "connection" "expected" "result"
  local i=0
  for c in "${CHECKS[@]}"; do
    local cc=($c); exp=${cc[$((5 + stage))]}
    if [[ ${results[$i]} == "$exp" ]]; then mark="✓"; else mark="✗ unexpected"; fi
    printf "   %-44s %-9s %-9s %s\n" "$(describe "$c")" "$exp" "${results[$i]}" "$mark"
    i=$((i + 1))
  done
}

echo "== Creating the app (app.yaml)"
kubectl apply -f app.yaml >/dev/null
for ns in "${NAMESPACES[@]}"; do
  kubectl -n "$ns" delete networkpolicy --all >/dev/null 2>&1    # start clean if you run this twice
done
for ns in "${NAMESPACES[@]}"; do
  kubectl -n "$ns" wait --for=condition=Ready pod --all --timeout=180s >/dev/null
done

for i in "${!STAGE_NAMES[@]}"; do
  echo
  echo "== Step $((i + 1)): ${STAGE_NAMES[$i]}"
  if [[ -n "${STAGE_CMDS[$i]}" ]]; then echo "   \$ ${STAGE_CMDS[$i]}"; eval "${STAGE_CMDS[$i]}" >/dev/null; fi
  run_checks "$i"
done

echo
echo "Done. Everything is still running so you can explore (kubectl get netpol -A)."
echo "Remove this example with:  ./demo.sh cleanup"
