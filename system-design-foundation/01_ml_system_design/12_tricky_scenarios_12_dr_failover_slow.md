# 12. DR Failover Took 8x Longer Than Planned

**Primary topic:** [Cost, Security & Multi-Region Governance](10_cost_security_multiregion.md)

## The Situation

Your primary region's model-serving cluster goes down (a real outage, not a drill). Your
documented disaster-recovery plan targets a 5-minute RTO via failover to a standby
region. Actual failover took 40 minutes. Service was degraded, though not fully down, for
most of that window. Leadership wants to know why the plan didn't hold up, and whether
the 5-minute target is even real.

## First Questions to Ask

- Had this specific failover ever actually been tested end-to-end before this incident, or
  only reviewed on paper?
- Was the standby region "warm" (running, minimal traffic, ready to absorb load
  immediately) or "cold" (infrastructure defined but not actually running)?
- What specifically took the most time during the 40 minutes — DNS propagation, replica
  warm-up, data replication catch-up, or a manual decision/approval step in the failover
  process itself?
- Was the failover triggered automatically (health-check based) or did it require a human
  to notice, diagnose, and manually initiate it?

## Likely Root Causes (ranked)

1. **The plan assumed a warm standby but the standby was actually cold (or under-scaled).**
   A "5-minute RTO" target only holds if the standby region can absorb full production
   load essentially immediately — if the standby's serving replicas were scaled down to
   near-zero for cost reasons (a very common, very reasonable-seeming cost optimization
   that directly conflicts with an aggressive RTO target), spinning them up to full
   capacity, pulling container images, and warming caches easily accounts for most of a
   40-minute gap. This is the classic **cost vs. RTO trade-off** that needs to be made
   explicit, not discovered during an actual incident.
2. **A manual decision step in the failover path.** If "failover" requires a human to
   notice the outage, diagnose that it's not transient, and manually trigger the
   failover process (rather than automated health-check-based failover), human response
   time alone can consume a large fraction of the target RTO before any technical
   failover work even begins.
3. **Feature-store or data replication lag meant the standby region wasn't actually
   serving-ready** even once compute capacity was available — if the standby's online
   feature store was replicating asynchronously and had fallen behind (or needed to
   "catch up" before being considered safe to serve from), that adds a data-readiness
   delay on top of any compute warm-up time.
4. **DNS/traffic-manager propagation delay** — if failover relies on DNS TTL-based
   propagation rather than a faster health-check-based global traffic manager, client-side
   caching of the old endpoint can extend perceived downtime well past the point where the
   standby was actually ready — TTL is a hint resolvers can ignore, not an enforceable
   contract, per the [DNS/BGP prerequisite
   primer](../00_prerequisite_concepts/09_dns_bgp_and_the_edge.md#ttl-a-hint-not-a-promise-and-why-that-breaks-failover).

## Diagnostic Path

1. **Reconstruct a timeline of the actual 40 minutes**, minute by minute if possible, from
   incident logs, alerting timestamps, and deployment/scaling events — identify exactly
   which phase (detection, decision, compute warm-up, data readiness, traffic cutover)
   consumed the most time. This single exercise usually makes the dominant root cause
   obvious.
2. **Check the standby region's actual running state at the moment of the incident** —
   replica count, whether it was serving any live traffic already, versus its documented
   "standby" configuration.
3. **Check whether failover was automated or manual**, and if manual, how long between
   the primary region going down and a human actually initiating failover.
4. **Check feature-store/data replication lag metrics for the standby region** at the time
   of incident, to determine if data readiness (not just compute) was a gating factor.

## The Fix

- **Immediate mitigation**: none applicable retroactively — this is a post-incident
  process, not a live scenario, so the "fix" is entirely about the long-term corrections
  below plus an honest incident report.
- **Long-term fix**: either (a) invest in a genuinely warm standby (running at some
  meaningful fraction of production capacity continuously) if the 5-minute RTO is a real
  business requirement — accepting the cost of that idle capacity as the price of that
  RTO — or (b) revise the documented RTO to match what a cold/warming standby can
  actually achieve, so the organization is planning against a real number instead of an
  aspirational one. Either is defensible; **silently keeping an aspirational RTO that's
  never been tested is not.**

## Prevention

The systemic lesson, stated directly in the
[cost/security tutorial](10_cost_security_multiregion.md#multi-region-disaster-recovery):
**a DR plan that's never been tested is not a DR plan.** RTO/RPO targets need to be
validated via actual scheduled failover drills, not assumed from architecture diagrams —
and any cost optimization applied to a standby region (scaling it down, replicating
asynchronously) needs to be evaluated explicitly against the RTO target it would
otherwise satisfy, since these two concerns trade off directly against each other and one
frequently undermines the other silently until a real incident reveals it.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Untested-plan framing (the default for this scenario):** "A DR plan that's never been
  tested is not a DR plan, it's a hypothesis. I'd say that directly to leadership rather
  than softening it — the 5-minute RTO was aspirational until this incident, whether or not
  anyone had said so out loud before."
- **Trade-off-made-explicit framing (good for explaining the cost-vs-RTO tension):** "Cost
  optimization on a standby region and an aggressive RTO target trade off directly against
  each other. Scaling the standby down for cost reasons is defensible — but only if it's
  evaluated explicitly against the RTO it would otherwise satisfy, not decided
  independently by two different conversations."
- **Timeline-reconstruction framing (good for the diagnostic approach):** "I'd reconstruct
  the 40 minutes minute by minute — detection, decision, warm-up, data readiness, cutover —
  because that single exercise usually makes the dominant cause obvious without needing to
  guess between four plausible hypotheses."

### Vocabulary Builder

- **warm standby vs. cold standby** (adj. phrase) — infrastructure already running and
  ready to absorb load immediately, versus infrastructure that's defined but not actually
  running until failover is triggered.
- **aspirational** (adj.) — a stated target that hasn't been validated as actually
  achievable. *"An aspirational RTO that's never been drilled is worse than an honest,
  tested, slower one."*
- **"…is the price of that RTO"** — a fluent way to frame ongoing idle-capacity cost as the
  necessary cost of a real reliability guarantee, not wasted spend.

---

**Previous:** [11. Serving Cost Doubled After a "Routine" Upgrade](12_tricky_scenarios_11_serving_cost_doubled.md)  |  **Next:** [13. Eval Passed, Guardrail Bypassed in Production](12_tricky_scenarios_13_eval_passed_guardrail_bypassed.md)
