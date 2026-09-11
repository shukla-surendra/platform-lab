# Removing Hurry: Pausing Before You Respond or Fix

Two habits that look unrelated — re-editing a reply for spelling/grammar right after sending it, and copy-pasting a fix into code before you understand the bug — are actually the same failure mechanism wearing two outfits. Both are ways of closing an uncomfortable gap *fast* instead of closing it *well*. This chapter names that mechanism and gives a specific pause-point for each context.

## The Single Root Cause: The Hurry Impulse

Between "I've been asked something" and "I've actually answered it," there's a gap — a few seconds of not-yet-resolved tension. The hurry impulse treats that gap itself as the problem to eliminate, so it reaches for whatever closes it quickest: hit send, paste the fix, watch the symptom disappear. The relief of *the gap being closed* gets mistaken for *the problem being solved*. It isn't the same thing, and the tell is always the same — you're doing cleanup work afterward (correcting the reply, re-fixing the bug) that a few seconds of pause up front would have prevented entirely.

This is the same mechanism as `13_Common_Mistakes/01` #10 ("Speeding Up When Uncertain") and `03_debugging_and_architectural_decision_making.md`'s failure mode #1 ("Jumping to a fix before you have a model") — this chapter is about the impulse underneath both.

## Pattern A: Reply-Then-Correct (Written Communication)

**What it looks like:** you answer a question, hit send/post, and immediately start noticing and fixing typos, grammar, or awkward phrasing — sometimes across several follow-up edits.

**Why it happens:** the moment you hit send, your brain logs the gap as *closed* — the social tension of "I haven't responded yet" is what it was actually racing to resolve, not correctness. Proofreading that should happen *before* send instead happens *after*, in public, where it costs more (visible corrections read as sloppy) than it would have cost as a silent step beforehand.

**The fix — separate compose from send as two distinct steps, always in that order:**

1. **Draft** the reply — get the content right, don't touch phrasing yet.
2. **Pause.** One full breath, or a deliberate two-second stop, before your hand moves to send. This is the step hurry skips.
3. **Read it back once, silently, as if someone else wrote it** — scanning specifically for spelling/grammar/clarity, not content. This is a different pass than drafting; don't try to do both at once.
4. Send.

For anything longer than a couple of sentences (a PR description, a Slack update, an email), draft it somewhere you're not being watched typing — a scratch note, a comment box you haven't posted yet — so step 2's pause is actually possible instead of happening under the pressure of a visibly-open reply box.

## Pattern B: Copy-Paste-Fix Before Understanding (Debugging/Development)

**What it looks like:** you find something that looks like the same error — Stack Overflow, another file, an old PR — paste it in, run it, and check whether the symptom went away, without ever stating what you think is actually happening.

**Why it happens:** identical mechanism. The gap is "this is broken and I don't know why," and the hurry impulse resolves the *discomfort* of that gap (by making the error message disappear) rather than the *problem* (understanding the cause). A fix that works without a model is luck — covered in full in `03_debugging_and_architectural_decision_making.md`'s OBSERVE → MODEL → HYPOTHESIS → TEST → ISOLATE loop; this section is the discipline for not skipping straight past MODEL.

**The fix — state the hypothesis before you touch the fix:**

Before pasting or typing any change, answer one question, out loud or in writing: *"What do I think is causing this, in one sentence?"* A scratch comment or a line in your terminal scrollback is enough — it doesn't need to be formal. If you can't write that sentence, you're not ready to apply the fix; you're about to gamble, and gambling is what produces the "worked, then broke again differently" pattern that eats far more time than the pause would have.

This single rule — **no change without a written hypothesis first** — is cheaper than it sounds. It usually takes ten to twenty seconds. What it removes is the ten-minute cycle of pasting three different "fixes" in sequence and being unable to say afterward which one actually mattered, or why.

## Why the Pause Feels Expensive When It Isn't

Hurry always overestimates the cost of pausing and underestimates the cost of the cleanup it causes. A two-second pause before sending feels like friction in the moment; three rounds of visible correction afterward feels like nothing because it happens off to the side, in small pieces. Same for debugging: stating a one-sentence hypothesis feels like it's slowing you down while the fix is *right there*; a fix applied without one often has to be redone once, or debugged again later when it turns out to have only masked the symptom.

The honest comparison isn't "pause vs. no pause" — it's "pause once, deliberately, up front" vs. "pay the same cost later, repeatedly, and less visibly."

## Building the Pause as a Habit

- **Two-pass rule for writing:** content pass, then a separate correctness pass, every time, with the send action only ever coming after both. Never merge them.
- **One-sentence-hypothesis rule for debugging:** no code change — not even a "quick test" — without first writing or saying what you expect it to fix and why.
- **Timeboxing isn't the same as rushing.** `03_debugging_and_architectural_decision_making.md` recommends timeboxed exploration ("20 minutes on this hypothesis") — that's a bound on how long you explore, not permission to skip stating the hypothesis before you start.
- **Make the pause physical, not just mental.** A breath, a hand off the keyboard, a two-second count — something with an actual sensory marker is easier to install as a habit than "remember to slow down," which is too abstract to catch you in the moment.
- **Notice the tell.** If you're correcting something you just sent, or re-fixing something you just "fixed," that's the signal the pause got skipped — not a reason to feel bad, a data point for the next rep.

## Self-Check

- [ ] Did I read my message once, silently, before sending — specifically for spelling/grammar/clarity, as a separate pass from writing the content?
- [ ] Can I state, in one sentence, what I believe is causing this bug before I change any code?
- [ ] Am I applying this fix because I understand why it will work, or because it looked similar to something that worked somewhere else?
- [ ] Am I currently cleaning up after something I sent or applied too fast — and if so, what would the pause-point have been?

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Wearing two outfits** | Idiom (used here): the same underlying mechanism appearing in two superficially different forms. |
| **Tell** | A giveaway sign that reveals what's actually happening underneath (borrowed from poker). |
| **Gamble / gambling** | Acting on a chance without real justification, risking an unknown outcome. |
| **Install** (a habit) | To deliberately build a behavior into oneself until it runs automatically. |
| **Masked** (a symptom) | Concealed or hidden without actually being resolved. |
| **Eats** (time) | Consumes or wastes time, often unnoticed until the total adds up. |
| **Sensory marker** | A tangible, physical cue (a breath, a pause) used to anchor a habit in the body, not just the mind. |

**See also:** [`03_debugging_and_architectural_decision_making.md`](./03_debugging_and_architectural_decision_making.md) — the full OBSERVE→MODEL loop this chapter's debugging half draws from; [`../13_Common_Mistakes/01_mistakes_causes_fixes.md`](../13_Common_Mistakes/01_mistakes_causes_fixes.md) #10 ("Speeding Up When Uncertain") — the same impulse showing up in live delivery instead of writing or debugging.
