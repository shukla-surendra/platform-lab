# Architect & Influence Register — Flat Word Table

One row per entry from `architect-influence-active-rotation.md`, in a single table instead
of split across six function sections — for scanning, printing, or drilling straight down
the list without jumping between headings. Meanings and examples are unchanged from the
source; `architect-influence-active-rotation.md` remains the canonical version if the two
ever drift.

| # | Term / Phrase | Type | Function | Meaning | Example |
|---|---|---|---|---|---|
| 1 | The way I'd frame this is… | Phrase | Opening a Position | Introduces a deliberate lens before the opinion itself | "The way I'd frame this is a build-vs-buy question, not a performance question." |
| 2 | My read on this is… | Phrase | Opening a Position | States an assessment while marking it as judgment, not fact | "My read on this is the bottleneck is the schema, not the query." |
| 3 | The design goal here is… | Phrase | Opening a Position | Anchors the discussion to intent before mechanism | "The design goal here is to keep the write path idempotent, everything else is negotiable." |
| 4 | Trade-off | Word | Naming the Trade-off | A gain accepted at the cost of something else | "There's a trade-off between latency and consistency here." |
| 5 | That buys us X at the cost of Y | Phrase | Naming the Trade-off | States what's gained and what's given up in one breath | "Caching buys us latency at the cost of staleness." |
| 6 | Directionally | Word | Naming the Trade-off | Correct in overall trend, without claiming precision | "Directionally, this is the right call — the exact numbers need a spike." |
| 7 | Calibrated | Word | Signaling Calibrated Judgment | Adjusted to match actual confidence or scale, not over- or under-stated | "I'd call this a calibrated guess — 70% confidence, not certainty." |
| 8 | First-order / second-order (effect) | Phrase | Signaling Calibrated Judgment | The direct consequence vs. the consequence of that consequence | "The first-order effect is faster deploys; the second-order effect is less review discipline." |
| 9 | Conviction | Word | Signaling Calibrated Judgment | The strength of belief behind a stated position | "I'll say this with low conviction — I haven't seen the traffic data." |
| 10 | Orthogonal | Word | Structural Precision | Independent of, with no bearing on, another factor | "That concern is orthogonal to this decision — it doesn't change the outcome either way." |
| 11 | Load-bearing | Word | Structural Precision | Something the rest of the system silently depends on, expensive to remove | "That retry logic is load-bearing — three other services assume it exists." |
| 12 | Decouple / Coupling | Word | Structural Precision | Separating (or the degree two components depend on) each other | "This is a tight-coupling problem — decoupling the two services solves it upstream." |
| 13 | Surface area | Phrase | Structural Precision | The scope of what a change or system touches or exposes | "That approach has a much smaller surface area — fewer places it can break." |
| 14 | I'd push back on… | Phrase | Disagreeing With Authority | Disagrees while framing it as a considered position, not a reflex | "I'd push back on that — it optimizes for the common case and breaks the tail case." |
| 15 | I'd flag… | Phrase | Disagreeing With Authority | Raises a concern without yet demanding it be resolved | "I'd flag the retry storm risk before we ship this." |
| 16 | Where this breaks down is… | Phrase | Disagreeing With Authority | Locates precisely the point a proposal stops holding, rather than rejecting it wholesale | "Where this breaks down is at write volume above 10k/s." |
| 17 | Steelman | Word | Disagreeing With Authority | To argue the strongest version of a position, including one you disagree with, before critiquing it | "Let me steelman the other approach before I say why I'd still pick this one." |
| 18 | My recommendation is… | Phrase | Closing the Decision | States the owned conclusion after the trade-offs are on the table | "My recommendation is we go with the managed service — the operational cost isn't worth owning." |
| 19 | I'd bias toward… | Phrase | Closing the Decision | States a leaning where the evidence isn't fully conclusive | "I'd bias toward simplicity here — we can always add the abstraction later." |
| 20 | The call I'd make is… | Phrase | Closing the Decision | Explicitly takes ownership of a decision, inviting challenge rather than hiding behind consensus | "The call I'd make is ship behind a flag and roll out gradually." |

No item in this set is a phrasal verb — the register leans on fixed phrases and single
precise words, not verb-particle combinations. If phrasal verbs get added to a future
architect/influence pull from `surface-vs-deep-lexicon.md`, add them here as additional
rows rather than a separate table, so this stays one flat list.
