# Phrase Library: Incidents, RCA, Performance, and Postmortems

## 1. Opening an Incident Communication (Impact First)

- "Current status: [X] is [degraded/down], affecting [scope]."
- "We're seeing [symptom] starting at [time], impacting [%/scope] of [users/requests]."
- "Customer-visible impact: [specific description]. No data loss."
- "This is contained to [component] — [other component] is unaffected."
- "Severity [X], based on [scope/impact], per our incident matrix."
- "We're actively investigating — next update in [timeframe]."

## 2. Giving Incident Status Updates (Ongoing)

- "Update as of [time]: we've identified [likely cause], working on [mitigation]."
- "We've ruled out [X] — currently focused on [Y] as the leading hypothesis."
- "Mitigation is in progress — expect resolution within [estimate], though I'll caveat that estimate is uncertain."
- "We've applied a temporary fix — monitoring to confirm stability before declaring resolved."
- "No change in status since the last update — still investigating [X]."
- "We're seeing early signs of recovery — [specific metric] is trending back to baseline."

## 3. Declaring Resolution

- "This is resolved as of [time] — [metric] has been stable for [duration]."
- "Root cause identified and mitigated. Full RCA to follow within [timeframe]."
- "Resolved, with a temporary fix in place — permanent fix tracked as [ticket], expected by [date]."
- "We're calling this resolved, with continued monitoring for the next [X hours] as a precaution."

## 4. Root Cause Analysis (RCA) Language

- "The root cause was [X], not [initial suspicion] — here's how we narrowed it down."
- "This is a five-whys situation: [symptom] → because [X] → because [Y] → because [Z, the actual root cause]."
- "The proximate cause was [X]; the systemic/contributing cause was [Y] — fixing only the proximate cause wouldn't prevent recurrence."
- "There were two contributing factors, not one — [X] alone wouldn't have caused this, but combined with [Y], it did."
- "This was a latent issue that had existed for [duration] — it only surfaced now because [trigger condition]."
- "The failure mode was [specific mechanism] — worth being precise here because the fix depends entirely on getting this right."
- "We validated the root cause by [reproducing it / correlating with metrics / checking logs] — this isn't a guess."

## 5. Distinguishing Contributing Factors From Root Cause

- "It's tempting to stop at [X], but that's a contributing factor, not the root cause — the root cause is [Y], which is why [X] was able to cause damage in the first place."
- "If we only fix the symptom, this recurs in [timeframe] — the actual fix has to address [systemic issue]."
- "This is a 'why did the system allow this' question, not just a 'what triggered this' question."

## 6. Performance Discussion Language

- "The bottleneck is [component] — everything downstream has headroom, but [component] is at [%] utilization."
- "p50 is fine at [X]ms; the problem is entirely in the tail — p99 is [Y]ms, which is [Z]x our SLA."
- "This is a throughput problem, not a latency problem — individual requests are fast, we just can't process enough concurrently."
- "We profiled this and [%] of time is spent in [specific function/query/stage] — that's where optimization effort should go, not [where we initially guessed]."
- "This scales sub-linearly because of [specific reason — lock contention, N+1 queries, a shared resource] — here's the fix."
- "We're CPU-bound, not I/O-bound here, which changes the fix from 'add more disks' to 'reduce compute per request.'"
- "The regression started at [commit/deploy] — bisecting narrowed it to [specific change]."
- "This is a classic N+1 — [X] queries per request instead of 1, and it only shows up at [scale] because below that the absolute numbers are small enough not to matter."

## 7. Presenting Project/Incident Status (Status Reports)

- "On track: [X]. At risk: [Y], because [reason] — mitigation in progress. Blocked: [Z], need [specific unblock]."
- "Green overall. One yellow flag: [X], being actively managed."
- "We're two days behind the original estimate, for [reason] — revised ETA is [date], and here's what changed my confidence."
- "No surprises this week — everything is tracking to plan."
- "I want to flag early, not late: [risk], even though it hasn't materialized yet."
- "Confidence level on hitting [date]: [high/medium/low], based on [specific remaining unknown]."

## 8. Postmortem-Specific Language (Blameless Framing)

- "The system allowed this failure mode — the question isn't who missed it, it's why our safeguards didn't catch it."
- "This wasn't a mistake in judgment given what was known at the time — it's a gap in what information was visible."
- "Anyone on the team could have hit this same issue under the same conditions — that's exactly why it's worth fixing systemically."
- "The process, not the person, is what we're examining here."
- "In hindsight this looks obvious — it wasn't, given the information available in the moment, which is worth being honest about."
- "The goal of this doc is prevention, not attribution."

Full postmortem facilitation norms and template live in `09_Meeting_Communication/01_standups_reviews_incidents_execs.md`.

## 9. Action Items and Follow-Through

- "Action item: [specific, owned, dated] — not 'we should look into X' but '[owner] will do [specific thing] by [date].'"
- "This becomes a P1 follow-up, not a someday-maybe — here's why it's time-sensitive."
- "We're tracking three action items: a fast mitigation (done), a systemic fix (in progress, [ETA]), and a monitoring gap closure (backlog, [priority])."
- "I want an owner and a date on every item before we close this doc, or they don't happen — that's just how backlogs work."

## 10. Communicating During a Live Incident (Calm, Precise, No Speculation)

- "I don't have a confirmed cause yet — what I know for certain is [X]. What I suspect but haven't confirmed is [Y]."
- "Let's not speculate on cause in the incident channel — I'll take that offline and report back with something verified."
- "I'm going to focus on mitigation first, root cause after — customer impact takes priority."
- "Can I get a second pair of eyes on [specific hypothesis] while I check [other hypothesis]?"
- "I want to avoid a fix that masks the symptom without addressing the cause — let's take 5 more minutes to be sure before we apply this."
- "Who's driving, who's scribing, who's communicating externally? Let's make sure those are three different people."

## Quick-Reference: Incident Severity Language

| Severity | Framing phrase |
|---|---|
| SEV1 (major, customer-facing, revenue-impacting) | "This is customer-facing and revenue-impacting — treating as SEV1, all hands." |
| SEV2 (degraded, contained) | "Degraded but contained — SEV2, core team engaged, no need for broader escalation yet." |
| SEV3 (minor, internal) | "Low customer impact, internal-facing — SEV3, normal working hours is fine." |
| Near-miss (no impact, but close) | "No customer impact, but this was one config value away from a real incident — worth a lightweight retro." |

**Next:** [`05_stakeholder_leadership_interview.md`](./05_stakeholder_leadership_interview.md) — phrases for stakeholder communication, leadership conversations, and interview answers.
