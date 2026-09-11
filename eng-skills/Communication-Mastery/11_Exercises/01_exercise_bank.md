# Exercise Bank

Ordered by difficulty tier. Use these to fill Block 3 and Block 4 of the Daily Practice routine (`10_Daily_Practice/01`). Each exercise should be done **out loud, ideally recorded** (`12_Recording_Analysis`) — silently thinking through an answer does not build the same skill (see the testing-effect discussion in `01_Foundations/02`).

---

## Tier 1: Foundational (Weeks 1-3)

### 1.1 — Explain to Five Audiences

Pick one technical concept (Docker, Kubernetes, a consistent hash ring, CI/CD, eventual consistency). Explain it, timed, to five audiences in a row, adjusting altitude each time (`01_Foundations/03`):

1. A child (10 years old)
2. A junior engineer (6 months experience)
3. A senior engineer outside your domain (e.g., a frontend engineer, if you're explaining Spark)
4. A CTO with a business-outcomes lens
5. A customer evaluating whether to trust your platform

**Success criteria:** each version should genuinely differ — not just in vocabulary, but in *what content you include*. If your "child" and "junior engineer" versions are nearly identical, you're not actually altitude-shifting.

### 1.2 — Timed Micro-Explanations

- Explain Docker in **30 seconds**.
- Explain Kubernetes in **1 minute**.
- Explain Terraform in **30 seconds**.
- Explain the difference between a container and a VM in **20 seconds**.
- Explain what a load balancer does in **15 seconds**, to a non-technical friend.
- Explain CI/CD in **45 seconds**, framed entirely around business risk reduction, zero jargon.

### 1.3 — Analogy Construction

For each, build an analogy, then pressure-test it by asking "where does this analogy break down?" (per the analogy-risk discussion in `01_Foundations/02`):

- Spark's lazy evaluation
- A message queue vs. a direct API call
- Database indexing
- Kubernetes pods vs. nodes
- Eventual vs. strong consistency
- A CDN
- Horizontal vs. vertical scaling
- A circuit breaker pattern
- MLOps feature stores
- Database connection pooling

### 1.4 — PREP Reflex Drill

10 facts, 10-second timer each, full PREP out loud (see `02_Thinking_Frameworks/01`). Sample prompts:

- Why do we use Infrastructure as Code?
- Why do we containerize our applications?
- Why does our team use trunk-based development / feature branches (pick your team's actual choice)?
- Why do we monitor p99 instead of just average latency?
- Why do we use a message queue instead of direct service calls here?
- Why do we run database migrations in a separate pipeline step?
- Why do we use immutable infrastructure?
- Why do we version our ML models?
- Why do we run canary deployments?
- Why do we separate staging from production?

---

## Tier 2: Applied (Weeks 4-7)

### 2.1 — Summarize a Talk

Watch or recall a conference talk (AWS re:Invent, a Databricks Data + AI Summit talk, a KubeCon talk). Summarize it in exactly 3 sentences using the Rule of Three (`02_Thinking_Frameworks/02`). Then summarize the SAME talk in exactly 1 sentence.

### 2.2 — Present a Migration Project

Using the Project Story shape (`04_Technical_Storytelling/02`), present a real or hypothetical migration (e.g., EC2 → Fargate, self-managed Kafka → MSK, on-prem → cloud) in exactly 2 minutes, hitting all 5 beats: starting state, hard decision, obstacle, quantified outcome, what you'd do differently.

### 2.3 — Present an RCA

Pick a real or plausible incident from your domain. Deliver a full RCA using the 6-beat incident shape (`04_Technical_Storytelling/02`) in under 90 seconds, then again in under 20 seconds (impact + cause + fix only).

Sample incident prompts if you need one:
- A Kubernetes cluster autoscaler failed to scale up during a traffic spike.
- A Terraform apply accidentally destroyed a production resource due to state drift.
- A Spark job silently produced incorrect output due to a schema mismatch.
- An ML model's performance degraded in production due to feature drift.
- A CI/CD pipeline deployed a broken build because a flaky test was marked as passing.

### 2.4 — Defend an Architecture Decision Under Challenge

Have a practice partner (or imagine a skeptical senior engineer) challenge a real architecture decision you've made. Practice the disagreement-handling pattern from `05_Phrase_Library/03`: acknowledge → position → reason → invite. Sample challenges:

- "Why not just use a managed service instead of building this yourself?"
- "Isn't this over-engineered for our current scale?"
- "Why didn't you just use [competing technology]?"
- "This adds a lot of operational complexity — was it worth it?"
- "What happens when this breaks at 3am — who can actually debug it?"

### 2.5 — Explain a Bug

Pick a real bug you've fixed. Explain it twice: once as a dry technical report (root cause + fix only), once as a full story with the investigation/tension beat (`04_Technical_Storytelling/01`). Notice the difference in how each version would land with a teammate vs. in a postmortem vs. in an interview.

### 2.6 — Explain an Algorithm

Pick an algorithm or data structure relevant to your work (consistent hashing, a B-tree index, a LRU cache, leader election, a bloom filter). Explain the mechanism using the Feynman Technique (`03_Explanation_Frameworks/02`) — teach it to a junior engineer first, notice your own gaps, then re-deliver at senior altitude.

---

## Tier 3: Advanced (Weeks 8-12)

### 3.1 — Full System Design Interview Simulation

Pick a system design prompt, run the full framework (`08_Interview_Communication/01`) solo, out loud, narrating every step, 30-45 minutes, recorded. Sample prompts:

- Design a feature store for an ML platform.
- Design a rate limiter for a public API.
- Design a distributed job scheduler.
- Design a real-time analytics pipeline processing 1M events/sec.
- Design a multi-region deployment strategy with a 99.99% availability target.
- Design a CI/CD system for 200 microservices with independent deploy cadences.
- Design a cost-allocation system for shared cloud infrastructure across 20 teams.

### 3.2 — Full Behavioral Interview Simulation

Using your story bank (`08_Interview_Communication/01`), answer 8 behavioral questions back to back, timed at 90 seconds each, recorded, with a "what would you do differently" follow-up on each.

### 3.3 — Impromptu / Random Object Explanation

Pick a random household object (a stapler, a thermostat, a coffee maker). Explain how it works, then explain it again as if it were a distributed system (e.g., "the thermostat is like a control loop with a feedback mechanism..."). This trains structured thinking under genuinely zero preparation, which is the closest simulation of an unexpected question in a live meeting.

### 3.4 — Whiteboard-Free Diagram Description

Using the techniques in `07_Architecture_Communication/02`, describe a complex system (your most complex production system, or one of the system design prompts from 3.1) entirely verbally, with no visual aid, to a partner who then tries to sketch what they heard. Compare their sketch to the real architecture — gaps reveal exactly where your traversal order or chunking broke down.

### 3.5 — Executive Summary Speed Round

Take 5 technical facts/decisions from your recent work. Write (or say) a 3-sentence executive summary for each in under 2 minutes total per fact, using the Executive Summary shape (`06_Project_Presentation/01`).

### 3.6 — The Compression Ladder

Pick one real project or incident. Explain it at 4 different lengths back to back: 10 seconds, 30 seconds, 90 seconds, 5 minutes. This drills the compression skill from `04_Technical_Storytelling/02` directly and is one of the highest-value single exercises in this repository — do it weekly even after Week 12.

### 3.7 — Cold Disagreement Drill

Have a partner (or imagine) state a technical opinion you genuinely disagree with, with no warning. Practice responding using the full disagreement phrase pattern (`05_Phrase_Library/03`) with zero prep time. This builds the reflex for real meetings, where disagreement rarely comes with advance notice.

---

## Difficulty Self-Assessment

After 12 weeks, you should be able to:

- [ ] Produce a clean PREP answer to an unexpected question with under 3 seconds of visible hesitation.
- [ ] Tell a 90-second STAR story with no notes, hitting all four beats, with genuine tension included.
- [ ] Shift altitude mid-explanation when a listener asks a follow-up, without restarting from scratch.
- [ ] Complete a full system design narration for 30+ minutes without losing structure.
- [ ] Compress any real project/incident to 4 different lengths (10 sec / 30 sec / 90 sec / 5 min) on demand.

If any of these still feel hard, repeat the corresponding tier rather than advancing — this is not a race, and per the spaced-repetition logic in `10_Daily_Practice`, repetition at the right difficulty beats premature advancement.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Pressure-test** | To deliberately probe something (an argument, an analogy) for weakness by challenging it. |
| **Impromptu** | Done without preparation, on the spot. |
| **Chunking** | Grouping information into meaningful units so it's easier to process and recall. |
| **Cold** (unprepared) | Attempted without advance warning or preparation, as in "cold call." |
| **Back to back** | One immediately after another, with no gap in between. |
| **Reflex** | An automatic, near-instantaneous response produced without conscious deliberation. |
| **Premature** | Happening before the proper or optimal time. |

**Next:** [`../12_Recording_Analysis/01_how_to_record_and_review.md`](../12_Recording_Analysis/01_how_to_record_and_review.md) — how to actually review the recordings these exercises produce.
