#!/bin/sh
# The "main" container in the sidecar pod - it has no idea a sidecar exists. It just writes
# events to a file on what it thinks is local disk. That file is actually a shared emptyDir
# volume (see deployment.yaml) - the entire mechanism the sidecar pattern relies on.
mkdir -p /var/log/app
i=0
while true; do
  i=$((i + 1))
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) event #${i} from $(hostname)" >> /var/log/app/events.log
  sleep 5
done
