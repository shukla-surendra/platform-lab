# Databricks AI Architect Tutorial

A tutorial covering the Databricks AI platform end to end: Genie's conversational analytics,
building custom agents with Agent Framework and Agent Bricks, unstructured-document knowledge
bases, where graphs do and don't fit natively, and the MLOps stack that runs all of it in
production.

## Everything here is dated

Databricks ships fast and renames things. Every chapter below is written against docs and blog
posts pulled **2026-08-13**, with the current product name and, where it changed recently, what it
used to be called. Chapter 0 is the single reference table for this — read it first if you read
nothing else, since half the platform's product names changed at least once in the last year.

## Chapters

| # | Chapter | You'll learn |
|---|---------|---------------|
| 0 | [Platform Map & Naming](00-platform-map-and-naming.md) | The 2025→2026 renames, and how the pieces fit together end to end |
| 1 | [Genie Agents & Genie One](01-genie-agents-and-genie-one.md) | NL2SQL over Unity Catalog, trusted-asset config, Conversation API, Genie-as-a-tool |
| 2 | [Genie Ontology](02-genie-ontology.md) | The auto-inferred semantic/context graph behind Genie — what it is and, honestly, what it isn't |
| 3 | [Agent Framework & Agent Bricks](03-agent-framework-and-agent-bricks.md) | Code-first agents, UC Functions as tools, Supervisor Agent, Unity AI Gateway |
| 4 | [Knowledge Bases & Unstructured Doc Q&A](04-knowledge-bases-unstructured-doc-qa.md) | `ai_parse_document`, chunking, AI Search, Knowledge Assistant, IDP |
| 5 | [Knowledge Graphs on Databricks](05-knowledge-graphs-on-databricks.md) | GraphFrames vs. Genie Ontology vs. bring-your-own graph DB — the honest maturity picture |
| 6 | [MLOps on Databricks](06-mlops-on-databricks.md) | MLflow 3 GenAI, UC Model Registry, Model Serving, guardrails, monitoring |
| 7 | [Building an NL2SQL Agent](07-usecase-nl2sql-agent.md) | The same capability three ways, and when each is the right call |
| 8 | [Building Unstructured Doc Q&A](08-usecase-unstructured-doc-qa.md) | The same capability two ways, custom pipeline vs. Knowledge Assistant |
| 9 | [Putting It Together](09-putting-it-together.md) | The full stack as one architecture, and answers to the questions that come up once you try to build on it |

## How this relates to the rest of this repo

- [`RAG_Knowledge_Base_Starter/`](../RAG_Knowledge_Base_Starter/index.md) covers the
  vendor-neutral RAG concepts (embeddings, chunking, HNSW) this tutorial assumes.
- [`Similarity_Search_Methods/08_Databricks_Vector_Search.md`](../Similarity_Search_Methods/08_Databricks_Vector_Search.md)
  already covers AI Search (formerly Vector Search) at the algorithm level — Chapter 4 here
  cross-links to it rather than repeating it.
- [`Agentic_Concepts/`](../Agentic_Concepts/00-agentic-concepts.md) covers framework-agnostic
  agent concepts (tool calling, multi-agent, guardrails) that Chapter 3 maps onto their Databricks
  equivalents.

## Sourcing

Every product-name and mechanism claim in this tutorial traces to a docs.databricks.com or
databricks.com/blog page fetched 2026-08-13, cited inline per chapter. Anything third-party,
Databricks Labs (experimental, non-GA), or otherwise not an official supported product is flagged
⚠️ at the point it's mentioned — that distinction matters for any architecture built on top of it.
