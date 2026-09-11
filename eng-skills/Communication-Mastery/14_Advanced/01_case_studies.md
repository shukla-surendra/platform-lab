# Full Engineering Case Studies

Four complete, end-to-end case studies, each taken through every format covered in this repository: problem, background, architecture, decision, trade-offs, a presentation-slide outline, an interview-length explanation, an executive summary, a technical summary, and likely interviewer questions with excellent answers. Use these as full templates — the **Reusable Case Study Template** at the end shows you how to build your own for any project in your real history (cloud migration, MLOps pipeline, Terraform infra, performance optimization, etc.).

---

# Case Study 1: Cloud Migration (EC2 → Kubernetes/EKS)

## Problem
A fleet of 40+ services ran on hand-provisioned EC2 instances with manual deploys via SSH and shell scripts. Deploys took 25+ minutes, rollbacks were manual and error-prone, and there was no standard health-check or autoscaling behavior across services — each was configured slightly differently by whoever built it.

## Background
The team had grown from 8 to 35 engineers over 18 months. The EC2 approach had worked at the earlier scale but was now the top source of deploy-related incidents (6 in the prior quarter) and was blocking a push toward more frequent, smaller deploys.

## Architecture (Before → After)

```
BEFORE:
  Engineer → SSH → shell script → EC2 instance (manual health check)
  40+ instances, each configured slightly differently, no central
  orchestration, autoscaling handled by ad hoc CloudWatch alarms.

AFTER:
  Engineer → git push → CI builds image → EKS deploys via Helm →
  readiness/liveness probes gate traffic → HPA + cluster autoscaler
  handle scaling automatically.
```

## Decision
Migrate to EKS, using Helm for deployment templating, with a phased per-service migration rather than a big-bang cutover (strangler-fig pattern, `05_Phrase_Library/02`).

## Trade-offs
- **Gained:** standardized deploys, automated rollback, self-healing (pod restarts on failed health checks), consistent autoscaling.
- **Cost:** real operational learning curve — the team spent roughly 6 weeks building internal Kubernetes fluency before the first production migration; added a genuinely new failure mode class (pod scheduling, resource limits) that didn't exist before.
- **Explicit non-goal:** this migration did not attempt to also introduce a service mesh — deliberately scoped out to avoid compounding two major changes at once.

## Presentation Slide Outline (5 slides, for a leadership readout)

```
SLIDE 1 — Headline: "Migrating from EC2 to EKS: 6 incidents/quarter → 0,
           25-min deploys → 4-min deploys"
SLIDE 2 — The problem, in incident/cost terms (not technical terms)
SLIDE 3 — Before/after architecture diagram (simple, 2-box comparison)
SLIDE 4 — Rollout plan and timeline (phased, with risk mitigation)
SLIDE 5 — Results + what's next (numbers + one sentence on the
           deliberately-deferred service mesh work)
```

## Interview-Length Explanation (~90 seconds, STAR-shaped)

> "At my last role, our deploy process was still fundamentally manual — SSH onto EC2 instances, run a shell script — even though the engineering team had tripled in size. That was directly costing us reliability: six deploy-related incidents in one quarter alone.
>
> I led the migration to EKS. The key decision was going phased rather than big-bang — we migrated one low-risk internal service first, used it to build real operational muscle with Kubernetes, then moved the remaining 40 services over about 10 weeks, ordered from lowest to highest risk. The part that didn't go smoothly: about halfway through, we discovered our resource limit defaults were too conservative, causing OOM kills on a few memory-heavier services — that cost us about four days of firefighting mid-migration.
>
> End state: deploy time went from 25 minutes to about 4, rollback became a one-command operation instead of a manual SSH exercise, and we went a full quarter with zero deploy-related incidents after completion. If I did it again, I'd load-test resource limits per service before migrating it, not after — that gap is what caused the OOM issues."

## Executive Summary

> **We migrated our deployment infrastructure from manual EC2 to Kubernetes (EKS), eliminating deploy-related incidents (6/quarter → 0) and cutting deploy time by 85%.** The migration took 10 weeks, phased to minimize risk, with one week of unplanned firefighting from a resource-configuration gap that's now fixed and documented as a pre-migration checklist item for future services.

## Technical Summary

> Migrated 40+ services from EC2/shell-script deploys to EKS with Helm-templated manifests, readiness/liveness-probe-gated rollouts, and HPA + cluster-autoscaler-driven scaling. Phased migration ordered by risk, strangler-fig style. Key learning: default resource requests/limits need per-service load testing before migration, not after — codified as a pre-migration checklist item.

## Likely Interviewer Questions + Excellent Answers

**Q: "Why EKS over ECS?"**
> "We evaluated both. ECS would've been simpler operationally, but we were already trending toward needing more portability — we had an early conversation about a second cloud provider for a specific enterprise customer's compliance requirement — and Kubernetes' portability was worth the steeper learning curve given that trajectory. If that multi-cloud conversation hadn't existed, I think ECS would've been the better call for our team size at the time."

**Q: "What would you do differently?"**
> "Load-test resource limits before migrating each service, not after — we found that gap the hard way with a mid-migration OOM issue that cost us about four days. It's now a standard pre-migration step."

**Q: "How did you handle the risk of a 10-week migration touching 40 services?"**
> "Ordered by risk, lowest first, and treated the first two migrations as deliberately over-instrumented learning exercises — we expected to find problems there and budgeted extra time for them, so that by the time we hit our highest-risk, highest-traffic services, the process itself was already de-risked."

---

# Case Study 2: MLOps Pipeline (Ad Hoc Notebooks → Production ML Platform)

## Problem
Data scientists trained models in local Jupyter notebooks, manually exported them, and handed them to engineers to "productionize" — a process taking 3-6 weeks per model and causing frequent train/serve skew (the production model behaving differently from what was validated in the notebook).

## Background
The ML team had shipped 12 models this way over a year. Two had been rolled back in production due to train/serve skew that wasn't caught until after launch — a direct cost in both engineering time and, in one case, a customer-facing quality regression.

## Architecture (Before → After)

```
BEFORE:
  Notebook (local) → manual export (pickle file) → Slack message to
  eng → eng manually rebuilds serving code → deploy → hope it matches

AFTER:
  Databricks notebook (feature engineering uses the SAME feature
  store used at serving time) → MLflow tracks experiment + registers
  model → CI validates the registered model against a golden test
  set → automated deploy to a model-serving endpoint, versioned,
  with automatic rollback on quality-metric regression.
```

## Decision
Build a feature store (ensuring training and serving read features from the identical source) and adopt MLflow for experiment tracking and model registry, with CI-gated promotion from staging to production.

## Trade-offs
- **Gained:** train/serve skew eliminated at the architecture level (not just process discipline), model deploy time cut from weeks to under a day, full experiment lineage/reproducibility.
- **Cost:** meaningful upfront investment (roughly one quarter, two engineers) before any new model shipped faster — a real "slow down to speed up" case that required executive buy-in to fund without an immediate visible payoff.
- **Explicit non-goal:** did not attempt real-time feature computation in this phase — batch features only, with real-time deferred as a documented future phase once the foundational platform proved out.

## Interview-Length Explanation (~90 seconds)

> "Our ML team was shipping models by handing pickle files to engineers over Slack, who'd then manually rebuild serving code — that process took 3-6 weeks per model, and worse, we'd had two production rollbacks from train/serve skew, where the production behavior didn't match what was validated offline.
>
> I proposed and led building a feature store plus an MLflow-based registry, so training and serving read features from the same source by construction, not by discipline. The hard sell was that this was a quarter of investment with zero new models shipping faster during that quarter — I had to make the case to leadership using the cost of the two rollbacks, translating engineering pain into a dollar figure they could weigh against the investment.
>
> Once live, model deploy time dropped from weeks to under a day, and we haven't had a train/serve skew incident since — it's now architecturally prevented, not just process-discouraged. The part I'd do differently: I scoped out real-time features entirely for this phase, which was the right call, but I underestimated how much some stakeholders wanted that immediately — better upfront expectation-setting on the phased scope would have saved some friction mid-project."

## Executive Summary

> **We eliminated train/serve skew — the root cause of two production ML rollbacks — by investing one quarter in a feature store and MLflow-based model registry, cutting model deploy time from 3-6 weeks to under a day.** This was upfront investment with no immediate output; payback was realized starting the following quarter and continues to compound as more models ship.

## Likely Interviewer Questions + Excellent Answers

**Q: "How did you get buy-in for a quarter of investment with no immediate visible output?"**
> "I translated the pain into numbers leadership already cared about — the two rollbacks had cost roughly [X] in engineering time plus one customer-facing incident, and I projected that cost forward against our model-shipping roadmap. The investment case wasn't 'this is best practice,' it was 'this specific recurring cost stops happening.'"

**Q: "What was the hardest technical decision?"**
> "Whether to build the feature store ourselves or adopt a managed one. We built a lightweight version ourselves, because at our scale a managed platform's cost didn't pencil out yet, and our feature complexity was still simple enough not to need its more advanced capabilities — I'd revisit that decision at meaningfully larger scale."

---

# Case Study 3: Production Incident (Kubernetes Cluster Autoscaler Failure)

## Problem
During a flash sale, traffic spiked 8x baseline. The cluster autoscaler failed to provision new nodes fast enough, and existing pods were evicted under memory pressure faster than new capacity came online, causing a 22-minute period of significantly elevated error rates.

## Background
The cluster had handled smaller spikes (2-3x) without issue before. This was the first time traffic exceeded the node group's pre-warmed capacity buffer.

## Root Cause (Five Whys)
Elevated errors → because pods were being evicted → because nodes hit memory pressure → because new nodes weren't provisioned fast enough → because the cluster autoscaler's node provisioning lag (roughly 90 seconds) combined with an undersized pre-warmed buffer that had never been recalculated after a 3x traffic baseline increase over the prior two quarters.

## Fix
Immediate: manually scaled the node group during the incident. Long-term: increased the pre-warmed buffer size (recalculated against current baseline, not the baseline from two quarters ago), added a pre-scaling hook triggered by marketing-calendar-known traffic events, and added an alert on "eviction rate" as a leading indicator, not just error rate as a lagging one.

## Interview-Length Explanation (~90 seconds)

> "We had a 22-minute period of elevated errors during a flash sale — traffic hit 8x baseline, and our cluster autoscaler couldn't provision nodes fast enough to keep up, so pods started getting evicted under memory pressure faster than new capacity arrived.
>
> The root cause wasn't really the autoscaler being 'slow' — a 90-second provisioning lag is normal — the actual gap was that our pre-warmed capacity buffer had been sized for a baseline that was two quarters stale; we'd grown 3x in traffic since that buffer was last calculated, and nobody had revisited it because it hadn't been a problem yet.
>
> Immediate fix was a manual scale-up during the incident. The systemic fix was recalculating the buffer against current baseline, adding a pre-scaling hook we now trigger before known high-traffic events like sales, and — the part I think was most valuable — adding an eviction-rate alert as a leading indicator, since by the time our error-rate alert fired, we were already in the failure mode, not catching it early."

## Likely Interviewer Questions + Excellent Answers

**Q: "Why hadn't the buffer been recalculated as traffic grew?"**
> "Honestly, a gap in our capacity-planning process — it wasn't tied to any recurring review cadence, it was a one-time initial calculation. That's the systemic fix that mattered most: we now review capacity buffers quarterly, tied to actual traffic trend data, not just when something breaks."

**Q: "How do you balance leading vs. lagging indicators in your alerting generally?"**
> "I try to make sure every critical path has at least one leading indicator — something that predicts a problem before customer impact — not just lagging indicators like error rate, which by definition mean impact has already started. This incident was a direct case of that gap; eviction rate was a leading indicator we simply hadn't wired up yet."

---

# Reusable Case Study Template

Use this to build your own case study for any real project — cloud migration, Terraform infrastructure work, Databricks migration, performance optimization, architecture review, leadership presentation, or anything else in your history.

```markdown
## Problem
[One or two sentences — the pain, stated concretely, ideally with a number]

## Background
[Why this was happening — team size, history, prior attempts, constraints]

## Architecture (Before → After)
[Simple before/after, described using the verbal-diagram techniques in
07_Architecture_Communication/02]

## Decision
[The core call you made, one sentence]

## Trade-offs
- Gained: [specific]
- Cost: [honest, specific]
- Explicit non-goal: [what you deliberately scoped out]

## Presentation Slide Outline
[5 slides max — headline, problem in business terms, before/after,
plan/timeline, results + what's next — see 06_Project_Presentation]

## Interview-Length Explanation (~90 sec, STAR-shaped)
[Situation/Task brief, Action detailed, Result quantified, one honest
"what I'd do differently" — see 08_Interview_Communication]

## Executive Summary
[One paragraph, outcome-first, business terms — see 06_Project_Presentation/01]

## Technical Summary
[2-4 sentences, full technical precision, for an engineering audience]

## Likely Interviewer Questions + Excellent Answers
[3-5 questions a sharp interviewer would ask about THIS specific
project, with PREP-shaped answers — see 03_Explanation_Frameworks/01]
```

Build 4-6 of these from your own real work before any interview cycle or promotion cycle — they become your story bank (`08_Interview_Communication/01`) and your fastest reference for any "walk me through a project" ask.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Big-bang** (cutover) | Doing an entire change all at once, in a single step, rather than gradually (contrasted with a phased approach). |
| **De-risked** | Made less likely to fail or cause serious harm, through deliberate mitigation. |
| **Firefighting** | Reactive, urgent problem-solving in response to something already breaking, rather than planned work. |
| **Pencil out** | For numbers or a plan to add up favorably when actually calculated (usually used in the negative — "didn't pencil out"). |
| **Codified** | Turned into a formal, written rule or standard procedure. |
| **Leading indicator** | A signal that predicts a problem before its impact is felt. |
| **Lagging indicator** | A signal that only shows up after impact has already occurred. |
| **Payback** | The point at which an investment's returns offset its original cost. |
| **Trajectory** | The path or direction something is heading, especially over time. |
| **Buy-in** | Genuine agreement and support from stakeholders for a plan or decision. |
| **Scoped out** | Deliberately excluded from a project's boundaries, decided in advance rather than by omission. |

**Next:** [`02_challenges_30_60_90.md`](./02_challenges_30_60_90.md) — structured multi-week challenges that sequence this entire repository into a concrete program.
