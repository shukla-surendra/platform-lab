#!/bin/sh
# The sidecar. It never talks to hit-counter directly - the only thing connecting them is
# the shared emptyDir volume both containers mount at /var/log/app. This is the actual
# mechanism a real log-shipping sidecar (Promtail, Fluent Bit) uses: read whatever the app
# container already writes to disk, no application code changes required.
mkdir -p /var/log/app
touch /var/log/app/events.log
tail -F /var/log/app/events.log | while IFS= read -r line; do
  echo "[log-tailer] forwarded: ${line}"
done
