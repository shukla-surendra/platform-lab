#!/usr/bin/env bash
# Walks through the egress-app test: works -> blocked -> DNS only -> HTTPS allowed.
# Usage: ./run.sh          (pauses between steps)
#        ./run.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=egress-app
YES=${1:-}

ctx=$(kubectl config current-context)
case "$ctx" in
  *eks-egress-lab*) ;;
  *) echo "kubectl context is '$ctx', not the EKS lab. Run ../connect.sh first." >&2; exit 1 ;;
esac

step()  { echo; echo "=== $* ==="; }
pause() { [ "$YES" = "--yes" ] || read -r -p "(Enter to continue) " _; }
logs()  { sleep "${1:-15}"; kubectl -n $NS logs -l app=egress-app --tail=1 --prefix=false --max-log-requests=5; }

step "1. Deploy: no policy yet, expect dns=OK https=OK"
kubectl apply -f 00-namespace.yaml -f 01-deployment.yaml
kubectl -n $NS rollout status deploy/egress-app --timeout=120s
logs 15
echo "egressIP should equal a node EXTERNAL-IP:"; kubectl get nodes -o wide | awk '{print $1, $7}'
pause

step "2. default-deny egress: expect dns=FAILED https=FAILED"
kubectl apply -f 02-netpol-default-deny-egress.yaml
logs 25
pause

step "3. allow DNS only: expect dns=OK https=FAILED"
kubectl apply -f 03-netpol-allow-dns.yaml
logs 25
pause

step "4. allow HTTPS: expect dns=OK https=OK again"
kubectl apply -f 04-netpol-allow-https.yaml
logs 25

echo; echo "Done. Remove with ./cleanup.sh"
