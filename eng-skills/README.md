# English Learning & Communication Toolkit

My vocabulary, phrasal verbs, idioms, and explanations collected over time, cleaned up for revision and accessible from anywhere.

Each file opens with a clickable **A–Z index** — tap a word to jump to it, and use the **↑ Back to index** link under each entry to return. On GitHub (web or mobile) the index links work as anchors; in most editors too.

## Collections

| File | What's in it | Entries |
|------|--------------|--------:|
| [Vocabulary](Vocabulary-Collections/vocab.md) | Single words, with meanings, examples, and spoken usage | ~1,907 |
| [Phrasal Verbs](Vocabulary-Collections/phrasal-verbs.md) | Two/three-word verbs (*get off*, *push back*, …) | ~1,066 |
| [Idioms](Vocabulary-Collections/idioms.md) | Idiomatic expressions and how to use them | ~288 |
| [Grammar Notes](Vocabulary-Collections/grammar-notes.md) | Articles, until/by, frequency adverbs, used to, has/have had, question forms | ~10 |
| [Speaking Toolkit](Vocabulary-Collections/speaking-toolkit.md) | How to explain, frame sentences, use analogies, go deeper without losing the thread, plus connecting/meeting phrases | ~10 |
| [Assertiveness & Vocal Presence](Vocabulary-Collections/assertiveness-vocal-presence.md) | Mindset, hedge-cutting, voice/delivery mechanics, body language, and context playbooks (meetings, 1:1s, presenting, general) | 10 sections |
| [Technical & Architectural English](Vocabulary-Collections/technical-english.md) | Technical/architectural verbs and phrases, A–Z | ~302 |
| [Business Communication](Vocabulary-Collections/business-communication.md) | Business and meeting idioms, diplomatic phrasing | ~117 |
| [Mental Models & Thinking Frameworks](Communication-Mastery/02_Thinking_Frameworks/04_mental_models_operating_system.md) | Operating principles, decision frameworks, and habits for engineering judgment and leadership | 11 sections |
| [Reference Tables](Vocabulary-Collections/reference-tables.md) | Quick phrase → one-line meaning lookup tables | 2 tables |
| [Vocabulary in Context — Stories](Vocabulary-Collections/stories.md) | Short stories that use the vocabulary in context, each with a glossary table | 6 stories |
| [Hindi-Speaker's Fluency Playbook](Vocabulary-Collections/hindi-speaker-fluency-playbook.md) | Breaking the Hindi→English translation loop: interference patterns, register upgrades, real-time repair moves, the full tense/grammar system as production drills, and a Hindi-thought → English-chunk dictionary | 12 sections |

## Curricula

Beyond the flat files above, two larger structured curricula live in their own folders, each with its own `README.md` map:

- **[`Communication-Mastery/`](Communication-Mastery/README.md)** — a full engineering-communication training system: thinking frameworks, explanation frameworks, storytelling, phrase library, interview/meeting/architecture communication, daily practice, common-mistake case studies, and advanced growth tracks.
- **[`Project_Management/`](Project_Management/README.md)** — a PMI/PMBOK literacy curriculum for understanding and speaking project-management vocabulary fluently as an engineer/architect (not a PM certification track): knowledge areas, methodologies, formulas, templates, an MLOps/GenAI/Cloud-specific playbook, and sourced real-project case studies.
- **[`Book-Summaries/`](Book-Summaries/README.md)** — deliberate, detailed summaries of business/strategy/engineering-leadership books, cross-linked into `Communication-Mastery/` and `Project_Management/` wherever a book's argument overlaps material already built out there.

## Revising

- **Search** — use your editor's / GitHub's search (press `/` on GitHub) to find any word instantly.
- **Browse** — open a file and skim the index, or scroll entry by entry.
- **Jump around** — index links go to the entry; the back-link returns you to the index.

## How these were made

The originals were Google Docs exported to Markdown (kept locally in `source/`, not committed). They were restructured to:

- remove the auto-generated table-of-contents and broken page-number links,
- strip embedded base64 images (~17 MB of bloat) — inline pictures were converted to plain external image links,
- drop empty page-break headings and normalize entry titles,
- sort every entry alphabetically and generate a fresh clickable index.

Duplicate entries from the original notes are kept as-is (a word you noted twice appears twice), so nothing you wrote is lost.

## Adding a new source doc

The one-time migration scripts that did the work above (`restructure.py`, `dedupe.py`, `route_vocab_phrasal.py`, and friends) were removed once their job was done; they were shaped around a specific one-off Google Docs export and won't run against a new file. The steps themselves are still the reproducible playbook for bringing in a new source doc by hand:

1. **INGEST** — drop the raw export somewhere under `source/` (gitignored, never committed as-is).
2. **CLEAN** — strip base64 images, broken TOC/page-number links, escape characters, and empty headings; normalize titles to plain `# Title` (no bold, no emoji in the heading itself).
3. **CLASSIFY** — read each block and tag it by type: single word → `Vocabulary-Collections/vocab.md`; two/three-word verb+particle → `Vocabulary-Collections/phrasal-verbs.md`; fixed idiomatic expression → `Vocabulary-Collections/idioms.md`; grammar point → `Vocabulary-Collections/grammar-notes.md`; speaking/framing technique → `Vocabulary-Collections/speaking-toolkit.md`; technical/architectural term → `Vocabulary-Collections/technical-english.md`; anything genuinely ambiguous → a `Miscellaneous Notes` scratch entry in the closest-fitting file rather than guessed into the wrong home, reviewed and routed properly later rather than left unclassified indefinitely.
4. **ROUTE** — append each block to its canonical file, in the correct alphabetical position, converging on a consistent per-entry shape (Meaning/Example, PoS where useful).
5. **DEDUP** — before appending, check the destination file for an existing entry with the same title; if one exists, merge (keep the richer body, append any unique notes) rather than creating a duplicate heading.
6. **INDEX** — add the new entry's link to the file's A–Z index in the matching alphabetical slot; don't rely on regenerating the whole index mechanically unless you've verified every existing link still resolves afterward.
7. **VERIFY** — run `make check` (validates every relative link, then does a full `mkdocs build --strict`) before considering the doc done; treat any heading-count drift you can't explain as a bug, not noise.

`make docs` serves the live MkDocs site locally (`http://localhost:8010`, live-reloads on save) for previewing while working through a new source doc.
