#!/bin/bash
# ValidateService: CodeDeploy calls this AFTER ApplicationStart and only marks
# the deployment (on this instance) successful if it exits 0 — the actual
# smoke test, not just "the process started."
curl -sf http://localhost/ >/dev/null
