#!/usr/bin/env bash
# Removes everything from this lab (the whole ingress-p1 namespace). Does not touch the ingress controller.
set -euo pipefail
cd "$(dirname "$0")"
NS=ingress-p1
source ../lib.sh
need_cluster
kubectl delete namespace $NS --ignore-not-found --wait=false
echo "waiting for the namespace to disappear..."
for _ in $(seq 1 45); do
  kubectl get namespace $NS >/dev/null 2>&1 || { ok "clean: namespace $NS is gone"; exit 0; }
  sleep 3
done
bad "still terminating; check: kubectl get ns $NS"; exit 1
