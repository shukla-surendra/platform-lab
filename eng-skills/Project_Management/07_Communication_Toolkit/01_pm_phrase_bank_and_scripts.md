# PM Phrase Bank and Scripts — Speaking the Vocabulary Fluently

The payoff chapter for everything else in this folder: knowing what CPI means is not the same as being able to use it, live, in a sentence, under mild pressure, in a way that sounds like it belongs to you rather than something recently memorized. This is a drillable phrase bank organized by situation, in the same spirit as `../../Communication-Mastery/05_Phrase_Library/`, scoped tightly to project-management contexts.

## Index

1. [Talking About Estimates](#1-talking-about-estimates)
2. [Talking About Status (Using RAG and EVM Language)](#2-talking-about-status-using-rag-and-evm-language)
3. [Talking About Risk](#3-talking-about-risk)
4. [Talking About Scope Changes](#4-talking-about-scope-changes)
5. [Talking About Blockers and Dependencies](#5-talking-about-blockers-and-dependencies)
6. [Talking to Different Altitudes](#6-talking-to-different-altitudes)
7. [Talking About Contracts and Engagement Terms](#7-talking-about-contracts-and-engagement-terms)
8. [A Worked Full Status Update, Assembled](#8-a-worked-full-status-update-assembled)
9. [Glossary — Vocabulary Used in This Chapter](#9-glossary--vocabulary-used-in-this-chapter)

---

## 1. Talking About Estimates

| Situation | Phrase |
|---|---|
| Giving a range instead of a point estimate | "I'd put this at five to eight days — the swing factor is whether the VPC peering approval comes through this week or next." |
| Stating confidence explicitly | "That's roughly a 70% confidence estimate, assuming the data's in the shape the platform team described." |
| Distinguishing effort from duration | "It's three days of actual work, but with the security review in the middle, calendar time is closer to a week." |
| Declining to fabricate a number | "I can't responsibly estimate that yet — give me a two-day spike and I'll come back with a real number and the top risks." |
| Re-estimating after an assumption breaks | "The estimate assumed X; X turned out not to hold, so I need to revise it — here's the new number and why." |

[↑ Back to index](#index)

## 2. Talking About Status (Using RAG and EVM Language)

| Situation | Phrase |
|---|---|
| Flagging amber early | "This is amber, not red — it needs attention this week or it becomes a date risk, but it's not blocking anything yet." |
| Explaining a CPI below 1.0 | "Our CPI is running at 0.85 — we're getting 85 cents of value for every dollar spent so far, mainly from the rework on the schema migration." |
| Explaining SPI | "SPI's at 0.9 — we're about 10% behind the planned pace, driven by the access-provisioning delay in week two." |
| Giving an honest forecast (EAC) | "At the current burn rate, this trends toward finishing about 15% over the original budget unless we course-correct — here's the specific driver and the option to fix it." |
| Refusing to melt straight from green to red | "I want to flag this now while it's still fixable, rather than wait and have it show up as a red surprise next week." |

[↑ Back to index](#index)

## 3. Talking About Risk

| Situation | Phrase |
|---|---|
| Raising a risk in proper four-slot grammar | "Risk for the log: [event]. I'd put it at [probability] within [timeframe]; if it happens, [impact]. Mitigation is [action], about [cost]. I'd like that scheduled this sprint." |
| Distinguishing mitigation from contingency | "The mitigation reduces the odds of this happening; the contingency is what we do if it happens anyway — we should have both written down." |
| Naming a risk acceptance decision explicitly | "We're choosing to accept this one rather than spend the two days mitigating it — I want that decision on record as a call, not a default." |
| Escalating a risk above your authority | "This is a platform-wide risk, not something I can own the response to — I'll write it up and bring it to [decision-maker]." |
| Calling out an unlogged risk | "Has this gone in the RAID log? If it's only been said out loud, it's not actually being tracked." |

[↑ Back to index](#index)

## 4. Talking About Scope Changes

| Situation | Phrase |
|---|---|
| Naming scope creep without conflict | "Happy to take this on — I want to make it official rather than accidental, since it wasn't in the original scope. Should I file a change request, or is this swapping out for something else?" |
| Distinguishing gold-plating from a real requirement | "That's good robustness, but it's not what was actually asked for — should I add it as a formal change, or leave it out of this pass?" |
| Pushing back on an unbudgeted addition | "Adding that means the triangle has to give somewhere — later date, more budget, or we cut something else. Which do you want to move?" |
| Requesting a formal change request for a real addition | "This is a legitimate need, but it's outside the current baseline — let's get it into a change request so it's tracked properly and doesn't quietly eat the schedule." |

[↑ Back to index](#index)

## 5. Talking About Blockers and Dependencies

| Situation | Phrase |
|---|---|
| Reporting a blocker (full form) | "I'm blocked on [X]. I've tried [A] and [B]. I need [specific thing] from [specific party]. Meanwhile I'm working on [next-best task]. If unresolved past [date], the impact is [consequence] — it's [on / not on] the critical path." |
| Asking whether something is on the critical path | "Is this task on the critical path right now, or does it carry float? That changes how urgently I should treat a delay here." |
| Flagging a dependency at risk | "Dependency D2 — the reserved GPU capacity — is at risk of slipping past its needed-by date. Flagging now so it doesn't become a surprise at cutover." |
| Declining to silently absorb someone else's delay | "I can't start my piece until [dependency] lands — I want that visible on the schedule rather than quietly eating into my own buffer." |

[↑ Back to index](#index)

## 6. Talking to Different Altitudes

| Audience | Register | Example |
|---|---|---|
| **Peer engineer** | Full technical detail, informal | "The schema drift is breaking the feature join — I'm adding a contract check at ingestion." |
| **PM / delivery lead** | Impact-and-plan framing, moderate detail | "The upstream schema changed again — it's a medium risk, 2-day mitigation, I've logged it and I'm starting the fix today." |
| **Sponsor / steering committee** | Business consequence, minimal technical detail | "We caught a data-quality risk before it hit production; a two-day fix keeps us on the current timeline." |
| **Cross-functional peer (security, platform)** | Precise, requirement-oriented | "I need the schema contract validated against your ingestion spec before I can close this out — can you confirm the current version?" |

The underlying rule, restated from `../02_Knowledge_Areas/03_communications_management.md` §6: **compress detail as altitude rises, and always end at the altitude's native currency** — technical fact for a peer, plan/impact for a PM, business consequence for a sponsor.

[↑ Back to index](#index)

## 7. Talking About Contracts and Engagement Terms

For a contractor specifically — phrasing that stays professional while asserting the contract's actual terms:

| Situation | Phrase |
|---|---|
| Naming a T&M engagement's actual risk allocation | "Since this is T&M, schedule risk on new scope sits with the client side by design — happy to take it on, we just need to agree it's additive rather than absorbed into the existing estimate." |
| Handling an out-of-SOW request | "That's a good ask and I can do it — it's outside the current SOW, so let's decide: swap it for something in scope, or treat it as a change order." |
| Asking for the economic buyer to see delivered value | "Could I get five minutes with [budget owner] this month? I want to make sure the value delivered is visible to whoever makes the renewal call, not just tracked in my own updates." |
| Responding to a vague performance concern | "I want to respond to that properly — could you help me understand the specific deliverables or dates that concern traces back to? I have the full delivery record and want to compare it against the actual timeline." |

[↑ Back to index](#index)

## 8. A Worked Full Status Update, Assembled

Putting several of the above together into one realistic weekly update — the kind that reads as senior on sight:

> **Status: Feature-store migration — Week 6**
> 🟡 Amber
>
> **Delivered:** Pipeline A ported and validated (parallel-run diff < 0.1%). Access provisioning for the new platform completed.
>
> **In flight:** Pipeline B port — 60% complete, on track for Friday.
>
> **Blocked:** Observability re-instrumentation is blocked on the monitoring team's alert-schema doc. I've pinged twice; need it by Wednesday or drift monitoring slips into next sprint. This item carries float, so it's not yet a date risk for the overall migration — flagging now so it stays that way.
>
> **Risk update:** New risk logged — R4, GPU reserved-capacity lead time is longer than assumed (2 weeks, not the 3 days in the original estimate). Probability 4, impact 3, score 12. Mitigation: submitted the reservation request today rather than waiting for pipeline completion, to de-risk the dependency early.
>
> **Metrics:** CPI 0.95, SPI 0.98 — tracking close to plan; the small dip is entirely the access-provisioning delay in week 2, already absorbed.
>
> **Decision needed:** None this week.

Every clause in that update maps to a specific piece of vocabulary from this folder — RAG status, parallel-run validation, critical path/float, four-slot risk grammar, EVM indices with a stated cause — deployed in service of a genuinely readable, three-paragraph update rather than as a vocabulary display. That's the actual target: the terms should disappear into fluency, not announce themselves.

[↑ Back to index](#index)

## 9. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Swing factor | The variable that determines which end of an estimate range materializes |
| Melt (green to red) | A status that jumps straight from healthy to critical without an intermediate warning |
| Four-slot grammar | The event/likelihood/impact/response structure for raising a risk clearly |
| Change order | A formal amendment adding or swapping work in a contract |
| Native currency | (figurative) The form of value or detail a given audience actually cares about |
| Additive | Added on top of the existing scope/estimate, rather than absorbed into it |
| De-risk | To take action reducing the probability or impact of a risk |
| On sight | Immediately, on first impression |

[↑ Back to index](#index)
