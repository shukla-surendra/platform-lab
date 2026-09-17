# 2. Genie Ontology

## First: it's a real product name, not a garbled one

Worth stating up front because it's easy to assume it's a mistranscription of something more
familiar — it isn't. **Genie Ontology** is a genuine, currently-shipping Databricks product,
announced 2026-06-16 alongside Genie One and the Genie Agents rename.

**Source:** [Introducing Genie One, Genie Ontology, and Genie Agents](https://www.databricks.com/blog/introducing-genie-one-genie-ontology-and-genie-agents)
(Databricks Blog, primary source), corroborated by third-party coverage (⚠️ [Atlan's
explainer](https://atlan.com/know/ai-agent/databricks/genie-ontology/) — useful for a second
framing, not the source of record).

## What it is

Databricks describes it as a "living graph of how a company works" — an automatically inferred,
continuously updating context layer that extracts:

- Metric definitions, business terms, and unique calculations
- Relationships between concepts, tables, metrics, and teams

Pulled from Unity Catalog tables, queries, dashboards, and pipelines, plus 50+ connected apps. It's
built on top of **Unity Catalog Metric Views** — the semantic/metrics layer is the foundation;
Genie Ontology is the auto-inferred graph Databricks builds *on top of* that foundation, connecting
metrics to the tables, people, and usage patterns around them.

It ranks and weights what it extracts using a PageRank-like authority signal: source origin, author
authority, usage frequency, certification status, and freshness. And it enforces whatever Unity
Catalog / source-native ACLs already apply — it is a read layer over already-governed data, not a
separate permission model you configure again.

**Purpose:** ground Genie's answers in something more structured than "raw schema plus the model's
best guess," which cuts token cost and reduces hallucination on ambiguous business questions
("revenue" meaning five different things across five teams is exactly the kind of ambiguity this
is meant to resolve).

## What it honestly is *not*

This is the part worth stating carefully — overclaiming it in an architecture proposal is a worse
mistake than the underlying capability gap itself:

> Genie Ontology is described in Databricks' own marketing language as a "living graph," but
> nothing in the documentation reachable as of 2026-08-13 exposes it as a queryable RDF or property
> graph you can point external tools at. As documented, it functions as an **internal context and
> ranking layer that improves Genie's own answer quality** — not a general-purpose knowledge-graph
> product you'd build a separate GraphRAG pipeline on top of.

Stated plainly: Genie Ontology is Databricks' auto-built semantic context layer that powers
Genie's own grounding — it's the closest thing Databricks has to a native knowledge graph, but
it's not exposed as a graph database you'd query directly. If a design needs a real queryable
knowledge graph over Unity Catalog data, that's a different piece — covered in Chapter 5.

## Where this fits the diagram in Chapter 0

Genie Ontology sits in the **Knowledge** layer, built from UC Metric Views and raw UC assets, and
feeds directly into Genie Agents (Chapter 1) as their grounding context — it's the mechanism, not
just a marketing claim, behind why a well-populated Genie Agent gives noticeably better answers
than one pointed at bare tables with no instructions or certified answers.

## The one line that answers "why does this exist"

Text-to-SQL over raw schema fails on ambiguity — a column named `revenue` doesn't tell you if it's
net or gross, and a raw schema graph doesn't tell you which of five `customer_id` columns across
five tables is the one people actually join on in practice. Genie Ontology's job is to encode that
tribal knowledge automatically, from usage and certification signals, instead of requiring someone
to hand-write it once and let it rot.
