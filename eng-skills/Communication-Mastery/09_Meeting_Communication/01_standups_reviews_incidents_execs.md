# Meeting Communication: Standups, Design Reviews, Incident Calls, and Executive Conversations

Each recurring meeting type has its own correct format, length, and altitude. Using the wrong one — giving standup-length answers in a design review, or design-review depth in a standup — is a common, easily fixed mistake.

## Standups

### The Standup Formula (15-20 seconds per person, no exceptions)

```
YESTERDAY  — one line, outcome not activity
TODAY      — one line, outcome not activity
BLOCKER    — only if real; "none" is a complete answer
```

**"Outcome not activity" is the entire skill here.** "Worked on the auth service" is activity — it tells the listener nothing about state. "Finished the auth service migration, in code review" is outcome — it tells the listener exactly where things stand.

| Activity-framed (weak) | Outcome-framed (strong) |
|---|---|
| "Worked on the ingestion pipeline." | "Ingestion pipeline handles the new schema now — deployed to staging." |
| "Looked into the latency issue." | "Found the latency issue — it's a missing index, fix is up for review." |
| "Had some meetings about the migration." | "Migration scope is locked — three services, starting Monday." |
| "Still debugging the flaky test." | "Flaky test is down to one specific race condition — expect a fix today." |

### Handling "This Needs More Discussion" in Standup

Standups aren't the venue for a design debate. The correct move is to name it and defer, not to start debating live and eat the whole meeting:

- "That needs more discussion than standup allows — can [person] and I grab 15 minutes after?"
- "There's a decision needed here — I'll write up the two options and send async rather than debate it live."
- "Flagging as a blocker, but let's take the details offline so we don't hold up everyone else's updates."

## Design Reviews

Covered in full in `07_Architecture_Communication/01_architecture_walkthrough_and_design_review.md` — this section adds meeting-logistics specifics.

### Opening a Design Review (as facilitator or presenter)

> "We're here to decide on [specific decision]. I'll walk through the design in about 15 minutes, then I want structured feedback — please hold blocking concerns until the end so we get through the full picture first, unless something changes how I should present the rest."

### Keeping a Design Review On Time

- "Let's park that — it's important but out of scope for today's decision. I'll capture it and we'll follow up."
- "We have 10 minutes left and two more sections — I'll speed through the failure-mode discussion unless someone has a blocking concern there specifically."
- "I want to make sure we land a decision today, not just discussion — where are we on [specific open question]?"

## Incident Calls

Full incident-specific phrase bank in `05_Phrase_Library/04_incidents_rca_performance_risk.md`. This section covers call structure and roles.

### Assigning Roles at Incident Start

- "I'll drive — [name], can you scribe the timeline in the incident doc? [name], can you own external comms so the rest of us can focus on mitigation?"
- "Let's keep this channel to signal, not speculation — if you have a hypothesis, say 'hypothesis:' before it so it's clear it's not confirmed."
- "I want one person actively debugging at a time per hypothesis, to avoid us stepping on each other's changes — who's got [hypothesis A]?"

### Running an Effective Incident Call

- "Status check — what's confirmed, what's hypothesis, what's ruled out?"
- "Let's timebox this hypothesis to 10 minutes — if it's not confirmed by then, we move to the next one in parallel."
- "I'm going to declare this SEV1 given the customer impact — that pulls in [escalation path]."
- "Someone give me a one-line status I can paste into the exec channel."

## Blameless Postmortem Meetings

### Opening the Meeting (Setting Blameless Norms Explicitly)

> "Before we start: this is about the system and the process, not any individual's judgment call in the moment. If you find yourself about to say 'X should have known Y,' reframe it as 'the system didn't surface Y where it needed to be visible' — that's the more useful and more accurate framing anyway, since anyone on the team could have hit the same gap."

### Facilitation Phrases for Staying Blameless

- "Let's rephrase that as a system gap rather than a person's miss — what would have needed to be true for this to have been caught automatically?"
- "I want to hear the reasoning at the time, not judge it with hindsight — what did you know at that point, and did the decision make sense given that?"
- "This is exactly the kind of thing that's obvious in hindsight and wasn't in the moment — worth naming that explicitly so we don't set an unrealistic bar for next time."

### Structuring the Discussion

Use the six-beat incident shape from `04_Technical_Storytelling/02` (impact → timeline → investigation → root cause → fix → prevention), with the majority of meeting time spent on **prevention** — the timeline and root cause should already be documented before the meeting (async, in the postmortem doc), so live time is spent on the forward-looking action items, not re-narrating what already happened.

## Talking With Managers (1:1s and Async)

### Bringing a Problem to Your Manager

- "I want to flag something before it becomes urgent: ..."
- "I have a decision I'm leaning toward, and I want a second opinion before I commit: ..."
- "I don't need you to solve this — I want to think out loud and get your read."
- "This is going to need [resource/decision] from you — here's the specific ask and by when."

### Giving Your Manager a Status They Can Use Upward

- "Here's what I'd tell your boss if they asked, in one sentence: ..."
- "Green, with one thing to watch: ..."
- "If this comes up in your leadership sync, the line to use is: ..."

## Executive Conversations and All-Hands

Covered in depth in `05_Phrase_Library/05_stakeholder_leadership_interview.md` and `06_Project_Presentation/01`. Meeting-specific additions:

### Handling a Surprise Question From an Executive

- "Good question — the short answer is [X]. I can go deeper if useful, but that's the headline."
- "I don't have that number memorized precisely — I'll get you an exact figure by end of day rather than guess."
- "That's slightly outside what I directly own — [name] would have a more precise answer, but my rough understanding is..."

### Recovering From Losing Your Structure Mid-Answer (Live, In Any Meeting)

Everyone loses their thread occasionally, even with full preparation. The recovery matters more than never losing it:

- "Let me restart that more cleanly — the core point is..."
- "I'm going to back up — the short version is [X], and I got lost in the detail. Let me try again."
- "Sorry, let me re-anchor — the question was [X], and my answer is..."

This recovery move — explicitly naming that you're resetting, then giving the answer-first version — reads as composed, not weak, because it demonstrates exactly the self-monitoring and structural awareness this entire repository is built to train. See `13_Common_Mistakes` for more on why a visible, deliberate recovery beats an invisible, meandering one.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Park (an issue)** | To set a topic aside deliberately for later, rather than dealing with it now. |
| **Eat (a meeting/time)** | To consume time or attention that was meant for something else. |
| **Scribe** | To record something, especially a timeline or discussion, in writing as it happens. |
| **Step on (each other's changes)** | To interfere with or overwrite someone else's concurrent work. |
| **Re-narrate** | To retell or recount something that has already happened, rather than adding new information. |
| **Re-anchor** | To reestablish orientation or context after losing one's train of thought. |
| **Meandering** | Wandering without a clear direction or endpoint. |

**Next:** [`../10_Daily_Practice/01_daily_and_weekly_practice_system.md`](../10_Daily_Practice/01_daily_and_weekly_practice_system.md) — the training system that turns everything covered so far into automatic, reliable behavior under real meeting pressure.
