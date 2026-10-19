# 00. Problem Statement & Requirements — Your Draft

This is a worksheet, not an answer key. Work through it **before** opening
`tutorial.md` — that file already contains the fully-worked Clarify and
Requirements sections, and reading it first defeats the point. Draft your
own answers below, then send them over (paste here or describe them) and
you'll get feedback against the reference answer — what matched, what a
staff-level answer would additionally catch, and why.

## The Prompt

> Design a URL shortening service like TinyURL or bit.ly. Users submit a
> long URL and get back a short link; visiting the short link redirects to
> the original URL.

That's all you'd get from an interviewer. Everything below is on you to
derive.

## Step 1 — Clarifying Questions

Before assuming anything, write down what you'd actually ask. Some angles
worth probing (don't answer them yet — just write the questions you'd
raise): scale in both directions (creates vs. redirects), whether short
keys need to be unguessable, custom aliases, link lifetime/expiration, how
fast a revoked link must stop resolving, analytics needs.

Your questions:

-
-
-
-

## Step 2 — Functional Requirements

Turn your clarified assumptions into a testable FR list — things the
system must *do*. Add or remove rows as needed.

| # | Requirement |
|---|---|
| FR1 | |
| FR2 | |
| FR3 | |
| FR4 | |

## Step 3 — Non-Functional Requirements

For each NFR, name an actual target — a number or an explicit guarantee,
not a word like "fast" or "scalable." A staff-level answer can point to
*why* each target is what it is.

| # | Requirement | Target | Why it matters |
|---|---|---|---|
| NFR1 | | | |
| NFR2 | | | |
| NFR3 | | | |
| NFR4 | | | |

## Step 4 — One Number That Reframes the Problem

Almost every system design question has a single back-of-envelope number
that changes how you think about the whole design — a ratio, a working-set
size, a growth rate. Compute one before you touch architecture. What is
it, and what does it imply about the design?

Your number and what it implies:

## When You're Done

Send over your draft. It'll get checked against `tutorial.md`'s Clarify
and Requirements sections — not just "did you get the same answer" but
whether the *reasoning* traces back to a stated requirement, which is the
actual bar. Don't open `tutorial.md` until then.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

These are about how the first five minutes of the interview sound — how
you *open* the requirements-gathering phase, not how you solve the whole
system.

- **Scale-first framing (the default open):** "Before I design anything, I
  want to pin down scale in both directions separately — how many creates
  versus how many redirects per second — because if those differ by
  orders of magnitude, that asymmetry should drive most of my decisions."
- **Risk-first framing (good when the question has a sensitive-data
  angle):** "One thing I want to clarify early: can the short key be
  guessed or enumerated? If links are ever unlisted-but-sensitive, that
  turns a cosmetic encoding choice into an access-control requirement, so
  I'd rather ask now than assume."
- **Spec-first framing (good for signaling rigor before diving into
  architecture):** "Let me restate what we've clarified as an explicit
  functional and non-functional requirements split, so every design
  decision I make afterward can point back to a specific line here rather
  than a vibe."

### Vocabulary Builder

- **functional requirement (FR)** (n. phrase) — a testable behavior the
  system must perform. *"FR2 is: given a short key, redirect to the
  original URL."*
- **non-functional requirement (NFR)** (n. phrase) — a quality constraint
  on how the system behaves, not what it does — latency, availability,
  consistency. *"The redirect path's NFR is p99 under 50 milliseconds
  globally."*
- **back-of-the-envelope estimate** (n. phrase) — a rough, order-of-
  magnitude calculation used to surface the number that should drive the
  design, before any architecture is drawn.
- **SLO (service-level objective)** (n.) — a target value for a metric
  (latency, availability, etc.) the system commits to. *"Redirect latency
  has a p99 SLO of 50ms."*
- **enumerable** (adj.) — describable by an attacker walking a sequence to
  discover things they weren't given; a security-relevant NFR concern in
  this problem specifically.
- **"let me restate that as an explicit requirement"** — a fluent way to
  convert a vague clarifying answer into something concrete enough to
  design against.

---

Companion worksheet for **[tutorial.md](tutorial.md)** — draft here first,
then compare.
