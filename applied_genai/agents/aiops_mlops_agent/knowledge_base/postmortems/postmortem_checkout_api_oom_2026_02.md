# Postmortem: checkout-api OOM cascade, 2026-02-04

## Summary
Both `checkout-api` hosts hit memory pressure within four minutes of each other during a
promotional traffic spike. On-call restarted the first host as soon as it alerted, which briefly
pushed all traffic onto the second host and made its memory pressure worse, triggering a second
alert and a second restart six minutes later. Checkout error rate stayed elevated for the full
ten-minute window instead of recovering after the first restart.

## Timeline
- 14:02 -- `host-web-01` mem_percent crosses 85%, `OutOfMemoryError` in logs.
- 14:03 -- On-call restarts `host-web-01` only, per the single-host branch of the (then-current)
  runbook. `running_count` on that host briefly drops to 0.
- 14:03 - 14:06 -- All checkout traffic routes to `host-web-02`, which was already elevated from
  the same promo traffic. It crosses 90% mem_percent and starts erroring.
- 14:09 -- `host-web-02` restarted. Checkout fully recovers by 14:11.
- Total customer-facing impact: ~9 minutes of elevated checkout errors, most of it caused by the
  restart sequencing, not the original spike.

## Root cause
The original runbook branched purely on "how many hosts are degraded right now," which was one
host at decision time -- but both hosts were on the same upward trend from the same shared
traffic spike. Restarting the first host removed capacity from a fleet that was already at its
limit, guaranteeing the second host would tip over next.

## Lessons / what changed
1. **A traffic-driven spike (promo, campaign, viral event) tends to hit every host on a service
   at once, even if only one has crossed the alert threshold first.** Before restarting a single
   host, check whether `cpu_percent`/`mem_percent` on sibling hosts running the same service are
   also trending up, not just currently below threshold.
2. When multiple hosts on one service are trending together, **scale the service up before or
   instead of restarting** -- adding capacity doesn't create a window with less total headroom
   the way a same-fleet restart does.
3. Restarting one host of a two-host fleet under real load removes half the fleet's capacity for
   the restart's duration -- treat that as a real cost, not a free action, when the fleet is
   already near its limit.
