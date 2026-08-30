#!/usr/bin/env bash
# Reverse order of deploy.sh, and for the same safety reason: delete the webhook
# CONFIGS first, so nothing in the cluster can be blocked by a dangling registration
# pointing at a server that's about to disappear.
set -euo pipefail
cd "$(dirname "$0")"

kubectl delete validatingwebhookconfiguration admission-webhook-demo-validating --ignore-not-found
kubectl delete mutatingwebhookconfiguration admission-webhook-demo-mutating --ignore-not-found
kubectl delete -f deployment.yaml --ignore-not-found
kubectl delete secret admission-webhook-tls -n default --ignore-not-found
kubectl delete namespace admission-webhook-demo --ignore-not-found
echo "torn down."
