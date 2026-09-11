# 2. Canary Passed, P1 Two Days Later

**Primary topic:** [Model Serving & Deployment](04_model_serving_deployment.md)

## The Situation

A new recommendation model version passed its canary — latency, error rate, and
prediction-distribution guardrails all stayed within threshold across a 4-hour, 10%-traffic
canary window, and it was ramped to 100%. Two days later, a P1 is declared: a significant
drop in a key downstream business metric (click-through rate), only noticed once the
weekly dashboard refreshed.

## First Questions to Ask

- What exactly did the canary's guardrails measure — latency/errors/prediction
  distribution only, or any business/quality metric?
- Was the 4-hour canary window representative of the traffic pattern that later caused the
  regression — same time-of-day, same user segments, same day-of-week?
- Is CTR monitored continuously, or only via a weekly dashboard? (This detail alone
  explains the 2-day detection delay regardless of root cause.)
- Did anything else change in that 2-day window besides the model — a concurrent feature
  rollout, a UI change, seasonal traffic shift?

## Likely Root Causes (ranked)

1. **The guardrails measured the wrong things.** Latency/error/prediction-distribution
   guardrails catch *infrastructure* regressions, not *quality* regressions in the
   business sense — a model can serve perfectly healthy-looking 200s with subtly worse
   recommendations. This is the most likely root cause: the canary was validated on the
   wrong signal for what actually broke.
2. **A 4-hour window doesn't cover the relevant segment/time-pattern.** If the regression
   is concentrated in a segment underrepresented in that specific 4-hour window (e.g.
   weekend users, a specific geography with different behavior), the canary would look
   healthy while missing the actual failure population entirely.
3. **A delayed-effect issue** — e.g. the model's recommendations degrade a *personalization
   feedback loop* over time (users engage less, the model gets less positive-signal
   training data, next update makes it worse) — this genuinely wouldn't show up in any
   short-window canary regardless of what it measures, since the effect compounds over
   days, not minutes.

## Diagnostic Path

1. **Slice CTR by segment and time** for the 2-day post-rollout window — confirm whether
   the drop is uniform or concentrated, and if concentrated, check whether that segment
   was proportionally represented in the canary window.
2. **Check whether the canary's guardrail metrics would have caught this at all** even in
   hindsight — pull the canary-window prediction distribution and business metrics (if
   logged) and see if a CTR-relevant signal was already trending down during the canary,
   just not measured.
3. **Rule out confounds** — check for any other concurrent change in the affected window
   (feature flag rollout, unrelated UI A/B test) that could explain the CTR drop
   independent of the model.
4. **Check whether this is a delayed feedback-loop effect** by comparing engagement-rate
   trends (not just CTR) day-by-day since rollout — a compounding pattern (small drop day
   1, bigger day 2) points to a feedback-loop cause; a step-change on a specific day points
   to something else changing on that day instead.

## The Fix

- **Immediate mitigation**: roll back to the previous model version (a registry-metadata
  operation per the [serving tutorial](04_model_serving_deployment.md)) while
  investigating — don't wait for root cause before mitigating a confirmed P1.
- **Long-term fix**: add the business metric (or a fast-computable proxy for it) as an
  explicit canary guardrail, and extend the canary window (or specifically stratify canary
  traffic) to guarantee coverage of the segments/time-patterns that matter, not just a
  fixed wall-clock duration.

## Prevention

The systemic lesson: **a canary is only as good as the metrics it checks and the traffic
it samples.** Infra health (latency/errors) is necessary but not sufficient — quality/
business metrics need their own guardrails, ideally computable fast enough to gate a
canary rather than only visible on a weekly dashboard. See the canary-evaluation-loop
deep-dive in the [model serving tutorial](04_model_serving_deployment.md#deep-dive-designing-the-canary-evaluation-loop)
for what a more complete guardrail set looks like.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Metric-scope framing (the default for this scenario):** "A canary is only as good as
  what it measures. Latency and error rate catch infrastructure regressions, not quality
  regressions — a model can serve perfectly healthy 200s with subtly worse
  recommendations. The guardrails here measured the wrong axis entirely."
- **Coverage framing (good for the 'was the window representative' question):** "Passing a
  canary proves the sampled traffic was fine, not that all traffic is fine. I'd always ask
  whether the canary window's segments and timing actually matched the population that
  later broke."
- **Compounding-effect framing (good for the feedback-loop hypothesis):** "Some
  regressions don't announce themselves in a 4-hour window at all — they compound over
  days, like a personalization feedback loop quietly starving itself of good signal. I'd
  distinguish a step-change from a compounding pattern before assuming a single cause."

### Vocabulary Builder

- **feedback loop** (n. phrase) — a delayed effect where a model's own output changes the
  future data it learns from, degrading gradually rather than immediately.
- **confound** (n.) — a second, unaccounted-for change that could explain an observed
  effect independent of the suspected cause. *"Rule out confounds before attributing the
  CTR drop to the model alone."*
- **"…necessary but not sufficient"** — a reusable template for arguing one guardrail
  category (infra health) doesn't cover another (business quality), without dismissing its
  value entirely.

---

**Previous:** [1. Regional Feature Staleness](12_tricky_scenarios_01_regional_feature_staleness.md)  |  **Next:** [3. Silent Drift, No Alert](12_tricky_scenarios_03_silent_drift_no_alert.md)
