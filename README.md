# mlops_aiops_toolkits

A personal monorepo — this project's own MLOps/AIOps tooling work, plus
several previously separate practice repos merged in with full commit
history (via `git subtree`, not submodules — each folder below is native
history in this repo now, not a reference to an external one).

## Top-level folders

| Folder | What's in it |
|---|---|
| **`mlops_aiops/`** | This repo's own content: `docs/` (tool write-ups — Evidently, MLflow, Feast, vLLM, Prometheus/Grafana/Loki, ELK/EFK, CloudWatch, observability on EKS) and `projects/` (runnable, uv-managed demos and pipelines for the tools documented in `docs/` — including `fraud-detection-xgboost/`, a full ingest→train→evaluate→monitor→serve MLOps pipeline). |
| **`cloud-practice/`** | AWS/cloud practice notes and Terraform — VPC, EBS/EFS, SageMaker, Bedrock, SQS, and a full Terraform reference. |
| **`k8s/`** | Kubernetes practice, three sub-repos merged under one parent, each split into `docs/` (theory/reference) + `practice/` (runnable demos): **`k8s_explorer/`** (pod/node affinity, service types, Jobs/CronJobs, Helm charts, a Kubeflow pipeline sample, a KServe inference example, a Grafana/Loki log-viewer demo — has its own MkDocs site), **`k8s_mlops/`** (one Helm chart, `evidently_stack/`, deploying a self-hosted Evidently monitoring server + a Jupyter pod that computes reports and pushes them to it), **`k8s_observability/`** (three independent Helm charts, one per signal — `metrics-stack/` for Prometheus+Grafana, `log-stack/` for Loki+Promtail+Grafana, `trace-stack/` for Tempo+Grafana — plus `streaming-drift-detection/`, a 5-stage MLOps drift-monitoring pipeline: Kafka → Feast → Evidently batch/streaming → OTel/Prometheus → Grafana/Alertmanager, scaffolded but not yet installed). |
| **`genai_lab/`** | Agentic AI / LLM tooling practice — MCP (from scratch and official SDKs), FastMCP auth patterns, LangGraph + Ollama, vector DBs (FAISS, Qdrant, pgvector), RAG, and Bedrock AgentCore. Has its own MkDocs site. |
| **`engineering_fundamentals/`** | Interview prep — DSA, system design (foundations + practice), low-level design, security engineering, behavioral. Has its own MkDocs site. |
| **`local_llms/`** | Local LLM/vision-model experimentation — an Ollama-backed chat UI (`ollama-chatbox`), deepfake-detector tests, Vision Transformer experiments (PyTorch/Flax/JAX), and notebooks (Gemma exploration, OCR comparison). uv-managed Python project (`pyproject.toml`/`uv.lock`). |

## Why the split

`cloud-practice`, `k8s/k8s_explorer`, `genai_lab`, `engineering_fundamentals`,
and `local_llms` were each their own repo, each already self-contained —
merging them in with `git subtree` preserved that structure and their full
commit history rather than flattening everything into one undifferentiated
tree. `mlops_aiops/` is where this repo's own work happens going forward.

## Claude Code skills

All skills — whether written for this repo or inherited from a merged
folder — live in one place at the repo root, `.claude/skills/`:

| Skill | Scope | What it does |
|---|---|---|
| `tech-log` | Whole repo | Passively documents tools/technologies discussed in chat into `mlops_aiops/docs/tools/` |
| `commit-policy` | Whole repo | Never commits unless explicitly asked; never adds an AI-attribution trailer |
| `engineering-fundamentals` | `engineering_fundamentals/` content | Two modes: Mode 1 adds/refreshes the "Articulate It" interview-framing section on that repo's tutorial docs (and covers authoring a new first-principles concept-primer doc); Mode 2 runs a live mock system design interview using that repo's tutorials as the answer key |

`engineering-fundamentals` was merged from two originally separate skills
(`articulate-it` and `system-design-interview`, inherited from that repo's
own `.claude/`) — same content tree and audience, so one file now covers
both instead of duplicating the directory/doc-convention context twice.
It still references `engineering_fundamentals/`-specific paths
(`system_design/`, `dsa_prep/`, its own MkDocs config) explicitly, since
it lives outside that folder now.
