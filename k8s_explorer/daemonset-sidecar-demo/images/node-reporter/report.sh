#!/bin/sh
# Runs once per node (it's the DaemonSet's container) - NODE_NAME comes from the Downward API
# (spec.nodeName via fieldRef in daemonset.yaml), the same mechanism real node-agents
# (node-exporter, Fluentd, kindnet/kube-proxy's own pods we inspected in kube-proxy-packet-path-demo)
# use to know which node they're actually running on without hardcoding anything per-node.
while true; do
  echo "[node-reporter] node=${NODE_NAME} time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sleep 10
done
