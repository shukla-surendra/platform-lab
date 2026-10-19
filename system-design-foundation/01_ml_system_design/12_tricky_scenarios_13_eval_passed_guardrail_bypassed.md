# 13. Eval Passed, Guardrail Bypassed in Production

**Primary topic:** [11. LLMOps: Prompting, Fine-Tuning, Evals & Guardrails](11_llmops.md)

## The Situation

A customer-support chatbot's prompt template was updated last week to make responses more
concise, per user feedback. The change passed the offline eval gate with a higher aggregate
LLM-as-judge score than the previous version. Three days after promotion, a support
escalation reveals a user got the assistant to reveal internal pricing-override logic by
pasting a block of "customer feedback" text that actually contained embedded instructions.
The guardrail suite is enabled and, on paper, includes prompt-injection detection.

## First Questions to Ask

- Was the injection-detection guardrail actually re-validated against *this* prompt
  version, or was it built and tuned against an earlier template and assumed to still
  apply?
- Does the golden eval set used to gate this change contain **any** adversarial/injection
  examples, or only "normal" support queries?
- Did the "more concise" prompt change alter how user-supplied text is delimited or framed
  relative to system instructions — even subtly?
- Is the injection-detection check applied to *all* user-supplied text paths, or only the
  primary chat input (missing, say, a "paste feedback" field that reaches the same prompt
  through a different code path)?

## Likely Root Causes (ranked)

1. **The golden eval set has no adversarial coverage.** If every item in the golden set is
   a well-behaved support query, an eval gate can only ever measure "does this help
   legitimate users," never "does this resist misuse" — the aggregate score going *up* is
   real but irrelevant to the incident, because the eval never tested the failure surface
   that broke.
2. **The prompt-change altered instruction/content separation.** "More concise" often means
   trimming boilerplate — if that trim removed or weakened the structural separation between
   system instructions and user-supplied content (e.g. collapsing distinct role blocks into
   a flatter, shorter prompt), the injection-detection guardrail's assumptions about *where*
   untrusted content lives may no longer match the new prompt's actual structure.
3. **Guardrail coverage gap across input paths.** If the "paste feedback" field feeds the
   same prompt through a different code path than the main chat box, and the guardrail was
   wired into only one of them, the check is bypassed by construction, not defeated by a
   clever attack.

## Diagnostic Path

1. **Pull the exact injected input and replay it against both the old and new prompt
   versions** with the guardrail active — determine whether the guardrail would have caught
   it under the *previous* prompt (points to root cause #2) or fails regardless of prompt
   version (points to root cause #3, a wiring gap).
2. **Audit the golden eval set for adversarial/injection cases** — count them. Zero or
   near-zero is itself the finding, independent of anything else.
3. **Trace the "paste feedback" field's code path end-to-end** to confirm whether it passes
   through the same guardrail middleware as the primary chat input, or reaches the LLM call
   through a different route that skips it.
4. **Check whether the injection-detection guardrail was re-run/re-tuned as part of this
   prompt change's review**, or treated as a static, "already handled" component that didn't
   need re-validation when the prompt changed.

## The Fix

- **Immediate mitigation**: roll back to the previous prompt version while the gap is
  fixed — the eval score regression from rolling back is an acceptable trade against an
  active data-exposure risk. In parallel, patch the "paste feedback" path (or whichever path
  is confirmed bypassed) to route through the same guardrail middleware as the primary
  input, with no exceptions.
- **Long-term fix**: add a standing adversarial/injection subset to the golden eval set
  (seeded from this incident and known injection patterns), require it to pass at 100% —
  not just contribute to an aggregate score — as a hard gate distinct from the general
  quality score, and require guardrail re-validation as an explicit, non-skippable step
  whenever the prompt structure changes, not just when guardrail code itself changes.

## Prevention

The systemic lesson: **an eval gate and a guardrail are not redundant, and a passing eval
says nothing about guardrail coverage** — they test different things (see the distinction
drawn in the [LLMOps tutorial](11_llmops.md#guardrails-safety)), and an
aggregate quality score improving can coexist with a safety regression the golden set was
never built to catch. The deeper lesson underneath that: any "concise" or otherwise
seemingly cosmetic prompt edit can change the *structural* assumptions a guardrail depends
on, so prompt changes and guardrail validation can't be treated as independent, siloed
review steps.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Different-tests framing (the default for this scenario):** "An eval gate and a
  guardrail test different things, and they're not redundant — a passing eval says
  'legitimate users are better served,' nothing about 'this resists misuse.' An aggregate
  quality score going up can coexist with a safety regression the eval was never built to
  catch."
- **Cosmetic-change-isn't-cosmetic framing (good for explaining the root cause):** "'Just
  making it more concise' sounds low-risk because it's a wording change, not a logic
  change — but trimming boilerplate can quietly weaken the structural separation between
  instructions and user content a guardrail depends on. I'd treat any prompt-structure
  change as guardrail-relevant by default, not exempt it because it 'looks' cosmetic."
- **Coverage-gap framing (good for the diagnostic approach):** "I'd replay the exact
  injected input against both prompt versions with the guardrail active first — that one
  test tells me immediately whether this is a guardrail-assumption break or a wiring gap
  where a second input path never went through the guardrail at all."

### Vocabulary Builder

- **adversarial example** (n. phrase) — an input specifically crafted to defeat a system's
  intended behavior, as opposed to a naturally-occurring difficult case; the category
  missing from the golden set here.
- **structural separation** (n. phrase) — keeping system instructions and untrusted content
  in distinct, clearly-delimited roles, the property a prompt-injection guardrail typically
  depends on.
- **"…are not redundant"** — a precise, quotable way to argue two safeguards that sound
  similar (eval, guardrail) actually cover different failure surfaces, so passing one says
  nothing about the other.

---

**Previous:** [12. DR Failover Took 8x Longer Than Planned](12_tricky_scenarios_12_dr_failover_slow.md)  |  **Next:** [14. GPU Sitting Idle 75% of the Time](12_tricky_scenarios_14_gpu_underutilized_sequential_pipeline.md)
