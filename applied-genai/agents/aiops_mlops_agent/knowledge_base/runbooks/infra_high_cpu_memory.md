# Runbook: Infra Host CPU / Memory Pressure

## When to use this runbook
A host reports `cpu_percent` or `mem_percent` above 85%, `status: degraded`, or
`running_count < desired_count` from `get_host_metrics`.

## Triage steps
1. `tail_service_logs` for the service running on the affected host. `OutOfMemoryError` or
   `connection pool exhausted` in the tail strongly indicates a resource leak or an undersized
   fleet for current load, not a code regression -- these two symptoms call for different fixes.
2. Compare `running_count` against `desired_count`. If tasks have already died and not been
   replaced, the fleet is under-provisioned for current traffic right now, not just trending
   that way -- treat as more urgent than a host that is merely hot but still at full count.
3. Check whether other hosts running the same service are also degraded (a fleet-wide pattern)
   or only one host (a single bad instance, often transient).

## Decision guide
- **Single host degraded, others on the same service healthy**: restart the affected host's
  service (`restart_service`) -- a single-host memory leak clears on restart and does not need a
  fleet-wide scale change.
- **All hosts on a service degraded, or `running_count < desired_count` on multiple hosts**: this
  is a capacity problem, not a leak. Scale the service up (`scale_service` with a higher
  `desired_count`) before or alongside a restart -- restarting an under-provisioned fleet just
  reproduces the pressure once traffic resumes.
- **Connection-pool-exhausted errors specifically**: restarting clears the immediate symptom but
  does not fix a genuinely undersized pool for current QPS; if this is the second occurrence for
  the same service within a day, escalate for a config change rather than auto-remediating again.

## Escalation
Escalate to `critical` if the degraded service backs a customer-facing checkout or payment path
and `running_count` has dropped below half of `desired_count`. A single degraded host with the
fleet otherwise at full count is `medium` severity and safe to auto-remediate without a human
in the loop.
