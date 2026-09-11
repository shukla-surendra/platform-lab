# Incident and Project Narratives

Two story types cover almost every technical narrative you'll ever need to tell: the **incident story** (something broke, here's what happened) and the **project story** (something was built or changed over time, here's the arc). Each has its own shape layered on top of the general four-beat arc from `01_storytelling_fundamentals.md`.

## Part 1: Incident Narratives

### The Incident Story Shape

```
1. IMPACT FIRST     What broke, for whom, for how long — stated in
                     business/user terms before technical terms.
2. TIMELINE          The key moments, compressed to 3-5, not a full
                     minute-by-minute log.
3. INVESTIGATION     The genuine wrong turns (tension beat) — this is
                     what makes it a story, not a report.
4. ROOT CAUSE        The actual mechanism, stated precisely.
5. FIX               What resolved it, immediate and long-term.
6. PREVENTION        What changes to stop recurrence — this is often
                     the part the listener cares about most.
```

Notice this leads with **impact**, not chronology — a specific application of answer-first thinking (`02_Thinking_Frameworks/01`) to incidents specifically: the listener's first question is always "how bad was it," not "what happened first."

### Full Worked Script — Production Incident, Spoken Version (~90 seconds)

> "Quick summary: we had a 40-minute partial outage on the recommendations service yesterday — about 30% of homepage requests fell back to a generic 'popular items' list instead of personalized recommendations. No data loss, no impact on checkout.
>
> Timeline-wise: it started right after a routine model deployment at 2:15pm, we got paged at 2:19 from elevated latency alerts, and it was fully resolved by 2:55.
>
> The investigation took a wrong turn early — the deploy had just gone out, so our first assumption was a bad model artifact, and we spent about 15 minutes trying to validate the new model version before ruling it out. What we eventually found was that the new model was actually fine, but it was roughly 3x the size of the previous one, and it was blowing past the memory limit on our inference pods during the rolling deploy, causing OOM kills and retries that cascaded into the latency spike we saw.
>
> The immediate fix was rolling back to the previous model version. The longer-term fix, which we shipped this morning, was adding a model-size check to the CI pipeline that fails the build if a new model artifact exceeds 120% of the current one's memory footprint without an explicit override — so this specific failure mode can't reach production silently again."

Walk through the six beats against this script: impact ("30% of homepage requests," "no impact on checkout"), timeline (three timestamps, not a full log), investigation with a genuine wrong turn (the model artifact red herring), root cause (memory limit + OOM + retry cascade), fix (rollback), prevention (the CI check). Every beat present, ~90 seconds, no filler.

### Written Postmortem Version (Same Incident)

Written postmortems follow the same six beats but benefit from the Pyramid Principle's structure (`03_Explanation_Frameworks/02`) — a one-paragraph summary up top containing beats 1, 4, 5, 6, with the full timeline and investigation narrative below for anyone who wants depth:

```markdown
## Summary
40-minute partial outage on the recommendations service (2026-XX-XX,
14:15-14:55 UTC). ~30% of homepage requests served a generic fallback
list instead of personalized recommendations. No data loss, no checkout
impact. Root cause: a routine model deploy shipped an artifact 3x the
previous size, exceeding inference pod memory limits and triggering OOM
kills. Fixed via rollback; prevented via a CI-enforced model-size gate
shipped the following morning.

## Timeline
[full timestamped log]

## Investigation
[the narrative, including the false lead — see 09_Meeting_Communication
for blameless postmortem norms on how to write this section without
assigning blame]

## Root Cause
[precise technical mechanism]

## Action Items
[owner, item, due date — see the postmortem template in 09_Meeting_Communication]
```

Full postmortem meeting facilitation guidance (including how to keep it blameless) lives in `09_Meeting_Communication/01_standups_reviews_incidents_execs.md`. Full incident-specific phrase bank lives in `05_Phrase_Library/04_incidents_rca_performance_risk.md`.

---

## Part 2: Project Narratives

Project stories cover a longer arc — weeks or months — and are the backbone of promotion packets, performance reviews, and "walk me through a project you led" interview questions. The shape is different from an incident because there's no single disruption moment; instead, there's a starting constraint and a series of decisions.

### The Project Story Shape

```
1. STARTING STATE & WHY IT MATTERED   The constraint or problem that
                                        made this project necessary —
                                        framed in terms of cost, risk,
                                        or business impact, not just
                                        "the code was messy."
2. THE HARD DECISION(S)               1-2 genuinely non-obvious calls
                                        you made, and the trade-off
                                        reasoning behind them — this is
                                        the load-bearing part for
                                        demonstrating judgment.
3. EXECUTION OBSTACLE                  One real thing that went wrong
                                        or was harder than expected
                                        mid-project (tension beat).
4. OUTCOME, QUANTIFIED                 Numbers: cost, latency,
                                        reliability, team velocity —
                                        whatever the project actually
                                        moved.
5. WHAT YOU'D DO DIFFERENTLY           Optional but powerful — shows
                                        continued judgment beyond the
                                        project's close.
```

### Full Worked Script — Project Story (~2 minutes, interview or promotion-packet length)

> "About a year ago, our ML training pipeline was costing us roughly $40k a month, mostly from GPU clusters that sat provisioned 24/7 even though training jobs only ran for about 6 hours a day on average. I proposed and led a move to on-demand, job-triggered Databricks clusters instead of the always-on setup.
>
> The genuinely hard decision was around cluster warm-start — on-demand clusters take 4-6 minutes to spin up, and a few of our most latency-sensitive retraining jobs couldn't tolerate that. Rather than keep the whole fleet always-on to avoid that cost for a minority of jobs, I split the fleet: a small always-on pool sized only for the handful of latency-sensitive jobs, and everything else moved to on-demand. That meant classifying every one of our ~30 existing jobs by latency tolerance, which took real negotiation with three different teams who each assumed their job was the sensitive one.
>
> The part that went sideways: two weeks after rollout, we hit a wave of job failures because our job-scheduling system wasn't handling on-demand cluster provisioning failures gracefully — a transient capacity issue in one region would just fail the job instead of retrying in another AZ. That cost us about a week of firefighting and a rougher rollout than I'd planned for.
>
> Once that was stable, the outcome was about $23k/month in savings — roughly 55% — with no regression in the latency-sensitive jobs, since those stayed on the always-on pool. If I did it again, I'd build the retry-across-AZ logic before rollout instead of discovering the gap in production — that's now something I check for by default on any job-scheduling change."

Notice: the hard decision (beat 2) is the section that demonstrates the most seniority — not the final number, the *reasoning process* that got there, including a decision that cost extra short-term effort (classifying 30 jobs, negotiating with three teams) for a better long-term outcome. This is the section interviewers and promotion committees actually weigh most heavily; see `08_Interview_Communication` and `14_Advanced/03_assignments_12_weeks.md`.

## Compressing Either Story for Time Constraints

Real meetings rarely give you 90 seconds uninterrupted. Practice compressed versions:

| Time budget | What survives |
|---|---|
| 10 seconds | Impact/outcome only — "40-min partial outage, no data loss, root cause was a memory limit, already fixed and prevented." |
| 30 seconds | Impact + root cause + fix (beats 1, 4, 5 for incidents; starting state + outcome for projects) |
| 90 seconds | Full arc, all beats |
| 5+ minutes (design review, deep-dive) | Full arc plus supporting detail on request — see `07_Architecture_Communication` |

Being able to compress on demand — not just having one fixed-length version memorized — is the actual skill. Practice all three lengths for your real incidents and projects; this is drilled explicitly in `11_Exercises/01_exercise_bank.md` and `14_Advanced/03_assignments_12_weeks.md`.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Rock-solid** | Extremely stable and reliable, with no history of trouble. |
| **Went sideways** | Idiom: started going wrong or off-plan, often unexpectedly. |
| **Firefighting** | Reactive, urgent work spent putting out active problems rather than planned work. |
| **Backbone** | The central, load-bearing element that everything else depends on or is built around. |
| **Load-bearing** | Structurally essential — removing it causes the whole thing to fail, borrowed from architecture. |
| **Transient** | Brief and short-lived, passing quickly rather than persisting. |

**Next:** [`../05_Phrase_Library/01_openings_transitions_structure.md`](../05_Phrase_Library/01_openings_transitions_structure.md) — the reusable phrase inventory that fills every framework and story shape covered so far.
