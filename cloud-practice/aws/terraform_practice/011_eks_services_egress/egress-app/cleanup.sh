#!/usr/bin/env bash
# Deletes the egress-app namespace (Deployment and NetworkPolicies go with it). Does not touch the `lab` namespace.
set -euo pipefail
kubectl delete namespace egress-app --ignore-not-found
