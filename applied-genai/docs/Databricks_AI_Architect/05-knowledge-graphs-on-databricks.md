# 5. Knowledge Graphs on Databricks

The honest answer, stated first: **there is no native, GA, queryable knowledge-graph database
product on Databricks.** Two
genuinely different things get called "graph" in Databricks material, and conflating them is the
mistake to avoid.

## The two things that are actually native

1. **GraphFrames** — a Spark DataFrame-based graph *analytics* library, pre-installed on Databricks
   Runtime for ML: motif finding, PageRank, connected components. This is graph **compute**, over
   data you already have as DataFrames — not a semantic graph store, not something you query with
   a graph query language, not something an LLM agent talks to as a knowledge base.
   **Source:** [How to use GraphFrames on Databricks](https://docs.databricks.com/aws/en/integrations/graphframes/),
   [Graph and network analysis on Databricks](https://docs.databricks.com/aws/en/machine-learning/graph-analysis).

2. **Genie Ontology** (Chapter 2) — the closest thing Databricks has to a native "knowledge graph"
   feature, in the sense of connecting metrics/tables/teams/usage into a graph structure — but as
   documented it's an internal context/ranking layer that powers Genie's own answers, not exposed
   as a general graph API you'd build a separate application against.

## What "a knowledge graph on Databricks" actually means, and the honest gap

If the requirement is "build a knowledge graph that feeds a GraphRAG-style retrieval system," the
accurate answer is: **that's bring-your-own-graph-DB, integrated via Unity Catalog**, not a native
Databricks product. The concrete options that exist, all flagged for maturity level:

- ⚠️ **PuppyGraph** (third-party) — a graph query engine positioned as "first graph compute engine
  partner for the newly open-sourced Unity Catalog." Lets you run graph queries directly over UC
  tables without ETL-ing the data into a separate graph database. Not a Databricks product — a
  partner integration.
- ⚠️ **OntoBricks** (`databrickslabs/ontobricks`) — a **Databricks Labs** project, meaning
  experimental/community-maintained, explicitly *not* GA or officially supported. Materializes UC
  tables into a Delta-backed triple store with ontology/reasoning exposed via MCP.
- ⚠️ **GraphRAG solution accelerator** (`databricks-industry-solutions/graphrag-demo`) — an
  "industry solutions" reference repo. Same tier as OntoBricks: useful as a reference
  implementation, not a supported product you'd put in a production architecture diagram without
  caveating it.

## Stated plainly

This is a place where overclaiming actively hurts an architecture proposal — knowing the
difference between "GA product" and "solution accelerator" and stating it clearly matters more
than a confident-sounding answer that blurs the two:

> Databricks doesn't ship a native knowledge-graph database. What it has natively is GraphFrames
> for graph analytics on Spark, and — new in 2026 — Genie Ontology, which is an auto-inferred
> context graph that powers Genie's own grounding but isn't exposed as a general graph API. For an
> actual GraphRAG knowledge-graph requirement, the real pattern is bring-your-own graph engine
> integrated against Unity Catalog — PuppyGraph is the one partner-level option, and there's a
> Databricks Labs project, OntoBricks, doing something similar at an experimental tier. Which of
> those fits should get scoped before committing to an architecture, because none of them are at
> the same support tier as, say, AI Search or Model Serving.

## Where this fits the diagram in Chapter 0

If a design needs a real knowledge graph, it's an addition *to* the Chapter 0 diagram's Knowledge
layer, sitting alongside Genie Ontology and AI Search — not a substitute for either, and not
something Genie Ontology already gives you for free.
