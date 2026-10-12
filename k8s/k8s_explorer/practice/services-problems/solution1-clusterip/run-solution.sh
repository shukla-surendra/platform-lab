#!/usr/bin/env bash
# Solution 1: a ClusterIP Service gives callers a stable address, so replaced Pods don't break them.
# Fully independent: creates its own backend in its own namespace (solution1). Nothing else is needed.
# Run:  ./run-solution.sh          (pauses between steps)
#       ./run-solution.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=solution1
source ../lib.sh

need_cluster

step 1 "Create the backend (3 Pods)"
say "A Deployment keeps 3 copies of a web server running. Each copy replies with its own Pod name."
run kubectl apply -f 00-backend.yaml
run kubectl -n $NS rollout status deploy/backend --timeout=120s
echo
run kubectl -n $NS get pods -o wide
look "3 Pods, each with a different IP."
pause

step 2 "Start a caller that uses a saved Pod IP (the OLD way, for comparison)"
say "This is the caller from the problem: it saves one Pod's IP and calls it every 2 seconds."
TARGET_POD=$(kubectl -n $NS get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
TARGET_IP=$(kubectl -n $NS get pod "$TARGET_POD" -o jsonpath='{.status.podIP}')
echo "saved: $TARGET_POD at $TARGET_IP"
kubectl -n $NS delete pod caller-pod-ip --ignore-not-found --wait=true >/dev/null
kubectl -n $NS run caller-pod-ip --image=busybox:1.36 --restart=Never -- sh -c \
  "while true; do if out=\$(wget -T 2 -qO- http://$TARGET_IP); then echo \"\$(date +%T) OK     \$out\"; else echo \"\$(date +%T) FAILED calling $TARGET_IP\"; fi; sleep 2; done" >/dev/null
kubectl -n $NS wait --for=condition=Ready pod/caller-pod-ip --timeout=90s >/dev/null
wait_log_lines caller-pod-ip 2 || true
run kubectl -n $NS logs caller-pod-ip --tail=3
look "OK, always from the same Pod. We will break this one later."
pause

step 3 "THE FIX: create a ClusterIP Service"
say "A Service is a stable IP and DNS name. It finds Pods by LABEL (selector: app=backend),"
say "and keeps a live list of them. Open 01-service-clusterip.yaml to read it."
run kubectl apply -f 01-service-clusterip.yaml
echo
run kubectl -n $NS get svc backend-svc
look "TYPE ClusterIP, a CLUSTER-IP, EXTERNAL-IP <none> (it is only reachable inside the cluster)."
pause

step 4 "Check which Pods the Service found"
say "The EndpointSlice is the Service's live list of Pod IPs. If a Service 'does not work', check this first."
echo "${BOLD}Service's list:${RESET}"
kubectl -n $NS get endpointslice -l kubernetes.io/service-name=backend-svc \
  -o jsonpath='{range .items[0].endpoints[*]}  {.addresses[0]}  {.targetRef.name}{"\n"}{end}'
echo "${BOLD}Actual Pods:${RESET}"
kubectl -n $NS get pods -l app=backend -o custom-columns='  IP:.status.podIP,NAME:.metadata.name' --no-headers
look "The two lists match: the same 3 Pod IPs."
pause

step 5 "Start a caller that uses the Service NAME (the FIXED way)"
say "Same kind of caller, but it calls http://backend-svc instead of a Pod IP."
kubectl -n $NS delete pod caller-service --ignore-not-found --wait=true >/dev/null
run kubectl apply -f 02-caller-via-service.yaml
kubectl -n $NS wait --for=condition=Ready pod/caller-service --timeout=90s >/dev/null
wait_log_lines caller-service 4 || true
echo
run kubectl -n $NS logs caller-service --tail=5
look "OK lines, and DIFFERENT Pod names. The Service spreads connections across the 3 Pods."
pause

step 6 "Kill the Pod the old caller saved"
say "Deleting $TARGET_POD. Its replacement gets a new IP, exactly like in the problem."
run kubectl -n $NS delete pod "$TARGET_POD"
kubectl -n $NS rollout status deploy/backend --timeout=120s >/dev/null
say "Waiting for both callers to make a few more requests..."
for _ in $(seq 1 20); do
  [ "$(kubectl -n $NS logs caller-pod-ip | grep -c FAILED)" -ge 2 ] && break
  sleep 2
done
echo
run kubectl -n $NS get pods -o wide
echo
echo "${BOLD}Service's list now:${RESET}"
kubectl -n $NS get endpointslice -l kubernetes.io/service-name=backend-svc \
  -o jsonpath='{range .items[0].endpoints[*]}  {.addresses[0]}  {.targetRef.name}{"\n"}{end}'
look "The dead Pod's IP is gone from the list and the replacement's IP is in it. The Service updated itself."
pause

step 7 "Compare the two callers"
OKS=$(kubectl -n $NS logs caller-service | grep -c OK || true)
FAILS=$(kubectl -n $NS logs caller-service | grep -c FAILED || true)
echo "${BOLD}caller-service${RESET} (uses the Service name):   $OKS OK, $FAILS FAILED"
kubectl -n $NS logs caller-service | grep -E 'OK|FAILED' | tail -3
echo
echo "${BOLD}caller-pod-ip${RESET} (uses the saved Pod IP):"
kubectl -n $NS logs caller-pod-ip | grep -E 'OK|FAILED' | tail -3
echo
if [ "$FAILS" = 0 ]; then
  ok "SOLVED: the Service-based caller never failed. Its code did not change; it just calls a Service name instead of a Pod IP."
else
  bad "caller-service saw $FAILS failures. A very brief blip can happen at the instant a Pod terminates; check the log."
fi
say "Creating the Service did not fix the saved-IP caller. A caller has to USE the Service."
echo
echo "Clean up with: ./cleanup.sh"
