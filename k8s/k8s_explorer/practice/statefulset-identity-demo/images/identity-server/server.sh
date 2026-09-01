#!/bin/sh
# Two things happen here, deliberately: (1) a background loop APPENDS this pod's
# own name + a timestamp to a file on the StatefulSet's per-replica PersistentVolume
# every 5s, and (2) busybox's own tiny httpd serves that same directory over HTTP.
# The append (not overwrite) is what makes the demo's key proof visible: if this
# pod gets deleted and recreated, StatefulSet reattaches it to the SAME PVC (the
# whole point of volumeClaimTemplates), so the log picks up growing from where it
# left off instead of starting over — a Deployment replica couldn't show this, it
# would land on fresh/no storage with a brand-new random name.
set -eu
mkdir -p /data
(
  while true; do
    echo "pod=${POD_NAME} time=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /data/identity.log
    sleep 5
  done
) &
exec httpd -f -p 8080 -h /data
