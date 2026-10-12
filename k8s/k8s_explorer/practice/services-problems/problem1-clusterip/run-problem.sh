#!/usr/bin/env bash
# Problem 1: shows that a caller using a saved Pod IP breaks when the Pod is replaced.
# Run:  ./run-problem.sh          (pauses between steps)
#       ./run-problem.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=problem1
source ../lib.sh

need_cluster

step 1 "Create the backend (3 Pods)"
say "A Deployment keeps 3 copies of a web server running. Each copy replies with its own Pod name."
run kubectl apply -f 00-backend.yaml
run kubectl -n $NS rollout status deploy/backend --timeout=120s
echo
run kubectl -n $NS get pods -o wide
look "3 Pods, each with a DIFFERENT value in the IP column. There is no single backend address."
pause

step 2 "Check the backend answers"
say "Pod IPs only exist inside the cluster, so your laptop cannot call them."
say "We start a throwaway Pod inside the cluster and call the first backend Pod from there."
TARGET_POD=$(kubectl -n $NS get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
TARGET_IP=$(kubectl -n $NS get pod "$TARGET_POD" -o jsonpath='{.status.podIP}')
echo "calling $TARGET_POD at $TARGET_IP"
in_cluster wget -qO- "http://$TARGET_IP"
look "'Hello from $TARGET_POD'  ->  the backend works."
pause

step 3 "Start a caller that SAVES that Pod's IP"
say "This imitates an app whose config says 'the backend is at $TARGET_IP'."
say "It calls that IP every 2 seconds and prints OK or FAILED."
kubectl -n $NS delete pod caller-pod-ip --ignore-not-found --wait=true >/dev/null
kubectl -n $NS run caller-pod-ip --image=busybox:1.36 --restart=Never -- sh -c \
  "while true; do if out=\$(wget -T 2 -qO- http://$TARGET_IP); then echo \"\$(date +%T) OK     \$out\"; else echo \"\$(date +%T) FAILED calling $TARGET_IP\"; fi; sleep 2; done" >/dev/null
kubectl -n $NS wait --for=condition=Ready pod/caller-pod-ip --timeout=90s >/dev/null
wait_log_lines caller-pod-ip 3 || true
run kubectl -n $NS logs caller-pod-ip
look "OK lines, always 'Hello from $TARGET_POD'. One IP means one Pod answers."
pause

step 4 "Kill that Pod"
say "We delete $TARGET_POD. The Deployment is told 'keep 3 Pods', so it creates a replacement."
run kubectl -n $NS delete pod "$TARGET_POD"
kubectl -n $NS rollout status deploy/backend --timeout=120s >/dev/null
echo
run kubectl -n $NS get pods -o wide
look "A NEW Pod name with a NEW IP. The old IP $TARGET_IP is gone."
pause

step 5 "See the problem"
say "Waiting for the caller to hit the dead IP..."
for _ in $(seq 1 30); do
  [ "$(kubectl -n $NS logs caller-pod-ip | grep -c FAILED)" -ge 2 ] && break
  sleep 2
done
echo "${BOLD}\$ kubectl -n $NS logs caller-pod-ip   (the last lines)${RESET}"
kubectl -n $NS logs caller-pod-ip | grep -E 'OK|FAILED' | tail -5
echo
bad "THE PROBLEM: 3 healthy backend Pods are running right now, but the caller keeps calling $TARGET_IP, which no longer exists."
say "The backend is fine. The caller has no way to learn the new IP."
echo
echo "Next (independent of this folder, you can run it any time): cd ../solution1-clusterip && ./run-solution.sh"
echo "Clean up this lab with: ./cleanup.sh"
