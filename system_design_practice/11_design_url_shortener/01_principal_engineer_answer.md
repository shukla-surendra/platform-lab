# 01. The Question, and What a Principal-Level Answer Adds

`tutorial.md` in this folder is already a strong **staff-level** answer —
correct architecture, the four deep-dives, trade-offs stated when probed.
This doc doesn't re-derive that design. It states the question as it would
actually be posed, then layers on **exactly what changes when the bar is
Principal**, using the three extra axes from
[`00_staff_level_signal/tutorial.md`](../00_staff_level_signal/tutorial.md#build-vs-buy-as-organizational-strategy-not-just-a-technical-choice):
influence without authority, build-vs-buy as strategy, and multi-year
technical strategy — on top of the four senior-vs-staff axes (scope, time
horizon, ambiguity, trade-offs), which a Principal answer must also clear,
not skip.

## The Question, As It Would Actually Be Posed

> "Design a URL shortening service like TinyURL or bit.ly."

At Principal round, the prompt is deliberately this short — the brevity
itself is part of the test. A senior candidate treats the shortness as
"not enough information yet" and asks clarifying questions until the
*technical* spec is pinned down. A Principal candidate additionally
notices that the prompt doesn't say **who this is for or why the org is
building it** — internal marketing tool? A standalone product? A feature
inside a larger platform? — and treats that as a real ambiguity worth
surfacing, because it changes the build-vs-buy answer, the multi-year
trajectory, and who else has a stake in the design, not just the FR list.

**Time-box**: same as staff (~5 min clarify, ~10 high-level, ~20
deep-dive, ~10 trade-offs) — Principal doesn't get more time, it gets
judged on using the same time to cover more altitude, not more technical
depth. If you're spending the deep-dive time re-deriving key generation
from scratch, you've already lost time you needed for the organizational
axes below.

## Scope: Who Else Builds Against This

A staff answer designs the service. A Principal answer designs the
**interfaces**, because a URL shortener inside any real org is never used
by only one team:

- **Growth/marketing** wants bulk creation (campaign links, thousands at
  once), branded custom domains, and UTM-style metadata attached to a
  link — not the one-link-at-a-time creation flow FR1 in `tutorial.md`
  implies. That's a different API shape (batch endpoint, quota per team)
  layered on the same key-generation core.
- **Trust & Safety** needs to consume the revocation path
  ([deep-dive](tutorial.md#deep-dive-revocation-vs-edge-caching-the-real-conflict))
  as a first-class capability with its own SLA, not a side effect of the
  abuse scanner — they need an API to query link status and force-revoke,
  independent of whoever created the link.
- **Data platform / analytics** consumes the click-event stream
  downstream. A Principal answer treats that stream's **schema** as a
  contract to version explicitly, because breaking it silently breaks
  every downstream dashboard and model that depends on it — this is the
  same "narrate the organizational consequence" habit from the staff
  tutorial, applied to a data contract instead of a service contract.

**The Principal-specific move**: design a versioned, self-service creation
API with per-team quotas from day one, rather than a single internal
endpoint the shortener team gates by hand — because gating every other
team's usage through your team manually is *the* way a Principal-scope
service quietly becomes an organizational bottleneck.

## Time Horizon: Where This Goes in 2-3 Years

`tutorial.md`'s design (7-char random key, 3.5 trillion key space, ~1%
occupancy after 10 years) already has enormous headroom on raw key
capacity — that's not the constraint that bites first. What actually
changes over 2-3 years, and what a Principal answer names explicitly:

- **From "shortener" to "link platform."** Branded custom domains, QR
  code generation, deep-link routing (mobile app vs. web), and per-link
  A/B redirect targets are the natural next asks once this ships. The
  data model (a flat `key -> URL` mapping) should not have to be redesigned
  to add a domain dimension or a redirect-rules field later — that's the
  expensive-to-change part worth spending extra design effort on *now*,
  per the "expensive vs. cheap to change" heuristic in the staff tutorial.
- **Multi-tenancy.** If custom domains ship, key uniqueness moves from
  global to per-domain — say this explicitly rather than discovering it
  when the first branded-domain request lands, since it changes the
  sharding key discussed in the
  [key-generation deep-dive](tutorial.md#deep-dive-key-generation-an-access-control-decision-not-an-encoding-one).
- **Name where the current design breaks.** The write path is trivially
  small (~10K/s peak) and stays that way even at 10x growth — this is
  *not* where the design needs headroom. The read path's edge/regional
  cache tier is where 10x growth first matters, and it's already the
  layer designed for it. Saying this out loud — confirming *what doesn't
  need to change* as clearly as what does — is itself a signal a
  Principal round rewards; over-designing the write path "to look
  thorough" is the wrong instinct here.

## Ambiguity: The Real Stakeholder Tension

A staff answer notices requirement gaps and asks. A Principal answer
notices when two stakeholders **want incompatible things** and names it
rather than picking a side silently. Here, that tension is real and
specific:

> Growth wants maximum flexibility on custom aliases and instant
> availability for campaign launches. Trust & Safety wants tight control
> over what can be created and the ability to kill anything, globally, in
> seconds. Those pull in opposite directions on the same surface: alias
> creation.

The Principal move isn't to silently favor one side (e.g., "custom
aliases just go through review" — that breaks Growth's campaign-launch
timelines) or the other ("aliases are unrestricted" — that's the
enumerable/abuse problem the key-gen deep-dive already rejects for
*random* keys, and is far worse for human-chosen ones). Name the
tension out loud, then propose a design that serves both: random keys
issue instantly with no review (Growth's default path is unaffected),
custom aliases go through an **async** review with a stated SLA (minutes,
not days) so campaign teams can plan around it, and *revocation* — the
one thing Trust & Safety actually needs to be fast — stays decoupled from
creation-time review entirely, on the out-of-band channel already in the
design.

## Trade-offs, Framed Organizationally (Proactive, Not Prompted)

Same technical trade-offs as `tutorial.md`, one layer further:

- "I'd use eventual consistency for cross-region replication of new
  links" (senior) → "...which means a link created in one region may
  404 for a few seconds in another before replication catches up — I'd
  want Growth's campaign-launch runbook to account for that window, or
  we pre-warm high-visibility campaign links before a launch, rather than
  Growth discovering it live during a product launch."
- "Revocation propagates out-of-band in seconds" (senior/staff) →
  "...which means Trust & Safety's global-takedown SLA is only as good
  as that push pipeline's health. I'd want that pipeline on their
  on-call's paging list, not just ours, with a defined escalation path —
  otherwise the org has a false sense of a fast-revocation guarantee that
  silently depends on a system they can't see."

## Influence Without Authority: Getting This Built

A likely Principal-round follow-up: *"Trust & Safety, the CDN/edge team,
and Growth all need to sign off on different parts of this. You don't
manage any of them — how do you get alignment?"*

- **Bring data to the tension named above**, not a proposal to debate as
  opinion: current abuse-report volume and time-to-takedown on whatever
  exists today (a spreadsheet, a manual process), projected under the
  proposed design. A concrete number ("takedown currently takes 4 hours
  because it's a manual DNS change; this design gets it to under 30
  seconds") resolves the alignment conversation faster than "I think
  this is safer."
- **Pilot the async-alias-review flow with one team before mandating it
  org-wide.** Ship random-key creation to everyone immediately (no
  review needed, no one's velocity is blocked), pilot custom aliases with
  one design-partner team, then generalize once the review SLA is proven
  — rather than asking every team to adopt an unproven review process on
  day one.
- **Find the shared incentive with the CDN/edge team**, who don't
  inherently care about *this* service — frame the out-of-band revocation
  channel as infrastructure they'll want for other services too (any
  edge-cached, revocable resource has the same problem), not a one-off
  request bolted onto their platform.

## Build vs. Buy, as Strategy

Whether to build this at all is itself a Principal-level question the
staff answer doesn't reach:

- **Is URL shortening the org's differentiator, or undifferentiated heavy
  lifting?** If this is an internal tool supporting Growth/Marketing (the
  common case), it is almost never the competitive edge — a managed
  offering (an enterprise link-shortener SaaS, or building the redirect
  layer on a CDN vendor's edge-KV product instead of a bespoke regional
  cache) is very likely the right call, and *building* the bespoke version
  in `tutorial.md` should be justified, not assumed. If the interview
  context is instead "you *are* bit.ly" — the shortener is the product —
  building is obviously correct, and this whole section should be stated
  as a conditional ("if this is a supporting tool, I'd lean buy; if it's
  the product, everything in `tutorial.md` is the right call") rather
  than silently picking one interpretation.
- **Total cost of ownership, not just build cost.** A self-hosted
  regional cache tier is "free" in licensing and costs an on-call
  rotation, a scaling runbook, and institutional knowledge concentrated in
  whoever built it. Naming that cost explicitly, even when still choosing
  to build, is the Principal-level habit a staff answer often skips.
- **Reversibility as a tie-breaker.** A managed edge-KV product with a
  clean data-export path is a safer bet than one that locks link data
  into a proprietary format — independent of which is technically
  "better" today, because the exit cost if the vendor choice is wrong
  differs enormously.

## Multi-Year Technical Strategy

- **What's expensive to change later:** the key format/length and the
  external API contract (`GET /{key}`, the creation request/response
  shape) — once billions of links and every consumer's integration depend
  on these, changing them is a migration project. **What's cheap:**
  which KV store or cache technology sits behind the interface — that can
  be swapped without any external consumer noticing.
- **Name the point where this design breaks.** The design as specified
  holds comfortably through the stated 10-year, 365B-key horizon in
  `tutorial.md`'s back-of-envelope. It does *not* automatically hold if
  multi-tenancy (per-domain key namespaces) ships — that's the actual
  next inflection point, not raw scale.
- **Name the debt being taken on, not just the design.** E.g.: "I'm
  accepting a synchronous, in-request safety scan at launch even though
  the async version in `tutorial.md` is architecturally cleaner, because
  standing up the async pipeline and its monitoring is more launch-week
  risk than the extra latency is worth at current volume. I'd revisit
  this once abuse-scan latency starts showing up in the p99 redirect
  budget, or once volume crosses roughly 10x current peak." Stating the
  condition under which the debt gets paid down is what separates this
  from an unexamined shortcut.

## What This Answer Deliberately Does Not Do

Restraint is itself part of the signal. This answer does not: propose
redesigning the write path for scale it doesn't need (see Time Horizon,
above), does not silently pick a side in the Growth-vs-Trust&Safety
tension, and does not assume "build" without stating the condition under
which "buy" would be the actual right call. All three are the specific
over-eager mistakes a strong staff candidate makes trying to sound like
Principal.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Layering framing (the default — use this to explicitly signal you're
  not re-deriving the whole system):** "The core technical design here —
  key generation, caching, revocation — doesn't change at Principal bar.
  What changes is that I'd also name who else builds against this, where
  the real stakeholder tension is, and whether we should even be building
  this ourselves."
- **Named-tension framing (good when asked how you'd resolve the
  Growth-vs-Trust&Safety conflict):** "This isn't a missing piece of
  information I can resolve by asking one more question — Growth and
  Trust & Safety genuinely want different things from the same alias-
  creation surface. I'd name that explicitly and design something that
  serves both — instant random keys, async-reviewed custom aliases —
  rather than quietly picking a side."
- **Conditional-strategy framing (good for the build-vs-buy follow-up):**
  "Whether we build this depends on whether it's the product or a
  supporting tool — I'd state that as an explicit fork rather than
  assuming one interpretation, because the two branches lead to
  genuinely different designs, not just different vendors."

### Vocabulary Builder

- **design partner** (n. phrase) — the first team a new capability ships
  to as a pilot, before a broader/mandatory rollout. *"I'd pilot the
  custom-alias review flow with one design-partner team before
  generalizing it."*
- **undifferentiated heavy lifting** (n. phrase) — infrastructure work
  that costs engineering effort but produces no competitive advantage;
  the strongest argument for buying instead of building.
- **exit cost** (n. phrase) — what it costs to leave a vendor or
  architecture choice if it turns out wrong; a build-vs-buy tie-breaker
  independent of which option looks technically better today.
- **paging path / on-call ownership** (n. phrase) — which team's pager
  actually fires when a system fails; naming this explicitly for a
  cross-team dependency (like an out-of-band revocation pipeline) is a
  concrete way to make an SLA claim credible rather than aspirational.
- **"...rather than a missing piece of information I can resolve by
  asking one more question"** — the precise phrase for distinguishing
  real stakeholder disagreement from ordinary ambiguity.
- **"...stated as an explicit fork, not an assumed interpretation"** — a
  fluent way to signal you noticed a question has two legitimately
  different readings, without stalling the interview picking one.

---

Reads after **[00. Problem & Requirements](00_problem_and_requirements.md)**
and the full **[tutorial.md](tutorial.md)** design — this doc assumes both.
