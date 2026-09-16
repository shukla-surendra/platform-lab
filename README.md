# platform-lab

A personal monorepo — cloud/infra, Kubernetes, MLOps/GenAI, ML fundamentals,
systems programming, and interview prep, each area self-contained in its own
top-level folder. This file is the index: what's where, and where to start
reading in each one.

## How to read this repo

- Most areas follow the same internal shape: `docs/` (theory/reference) +
  `practice/` or numbered example folders (runnable code), sometimes both
  published as their own [MkDocs](https://www.mkdocs.org/) site.
- **`make docs FOLDER=<name>`** (root `Makefile`) serves *any* top-level
  folder's docs locally — `make init FOLDER=<name>` scaffolds an MkDocs site
  for one that doesn't have one yet by symlinking its markdown-bearing
  subdirectories into `<name>/docs/`, the same pattern `fundamentals/`
  uses by hand. `make run FILE=<path>` runs a standalone script against the
  root `pyproject.toml`/`uv.lock` venv — for scripts living directly under a
  repo-root folder (`system_design_foundation/`, `system_design_practice/`)
  rather than inside their own uv sub-project.
- Folders with their own `pyproject.toml`/`uv.lock` (or `package.json`) are
  independent projects — `cd` in and use their own tooling, not the root one.
- **`make serve-all`** builds every folder with its own MkDocs site
  (`fundamentals/`, `genai_lab/`, `k8s/k8s_explorer/`, `eng-skills/`,
  `mini-llms-playground/`) and serves all of them from one local server —
  open `http://127.0.0.1:8000/docs-index.html` and click into whichever one
  you want. `make build-all` does the build step alone, no server.

## Cloud & infrastructure

| Folder | What's in it |
|---|---|
| [`cloud-practice/`](./cloud-practice) | AWS/Azure/GCP at architecture-internals depth — gated modules, one service at a time, plus a full Terraform reference. |
| [`k8s/`](./k8s) | Kubernetes. [`docs/`](./k8s/docs) — general reference, segregated by topic: [`api-server/`](./k8s/docs/api-server) (resources vs. objects, `kube-apiserver` architecture, request lifecycle, extensibility, watch/list, API-group + full built-in-resource reference), [`rbac/`](./k8s/docs/rbac) (RBAC model, verb/permission list, identity, FAQ), [`plugins-and-addons/`](./k8s/docs/plugins-and-addons) (CNI/CSI/CRI/device-plugins/scheduler/CCM vs. the broader add-on ecosystem, and how both relate to CRD+operator). Five sub-projects: [`aks_crd_operator/`](./k8s/aks_crd_operator) (build a CRD + operator from scratch, Go and Python side by side — see [`operators/README.md`](./k8s/aks_crd_operator/operators/README.md)), [`aks_setup/`](./k8s/aks_setup) (deploy an app to AKS via Helm), [`k8s_explorer/`](./k8s/k8s_explorer) (affinity, Services, Jobs/CronJobs, Helm, Kubeflow, KServe — own MkDocs site), [`k8s_mlops/`](./k8s/k8s_mlops) (self-hosted Evidently monitoring), [`k8s_observability/`](./k8s/k8s_observability) (Prometheus/Loki/Tempo stacks + a streaming drift-detection pipeline). |
| [`public_docker_images/`](./public_docker_images) | The *only* place images are built to be pushed to a public registry and pulled by strangers — kept separate so a Dockerfile elsewhere in the repo only ever has to work on this laptop. |

## MLOps, GenAI & agentic AI

| Folder | What's in it |
|---|---|
| [`mlops/`](./mlops) | `docs/` — tool write-ups (Evidently, MLflow, Feast, vLLM, observability stacks); `projects/` — runnable pipelines (`fraud-detection-xgboost/`, `batch-drift-detection-xgboost/`, `evidently-monitoring-demo/`, `feast-demo/`). |
| [`genai_lab/`](./genai_lab) | Agentic AI / LLM tooling — `agentic/` (MCP from scratch and official SDKs, LangGraph+Ollama, Bedrock AgentCore, a k8s on-call agent), `rag/` (FAISS, Qdrant, pgvector, FastMCP auth patterns), `docs/`. Own MkDocs site. |

## Machine learning & deep learning

| Folder | What's in it |
|---|---|
| [`pytorch_exploration/`](./pytorch_exploration) | From-first-principles PyTorch: tensors → autograd → `nn.Module` → losses/optimizers → a full training loop. |
| [`mini-llms-playground/`](./mini-llms-playground) | Small-LM experiments, three tracks: `from_scratch/` (train a GPT-style model from zero), `fine_tuning/` (LoRA on a pretrained model), and serving an unmodified checkpoint as a baseline. |
| [`local_llms/`](./local_llms) | Local LLM/vision experimentation — `ollama-chatbox/` (chat UI), `deepfake-detector/`, `vit/` (Vision Transformer, PyTorch/Flax/JAX), and notebooks (Gemma, OCR). |

## Databases

| Folder | What's in it |
|---|---|
| [`dbms_exploration/`](./dbms_exploration) | `pg_explore/` (disposable Postgres + Liquibase + Faker sandbox), `sql_postgres_practice/` (SQL/Postgres interview prep, fixture DBs), `extending_pg_lab/` (sharding/partitioning/replication/consistent-hashing design notes). |

## Systems programming

| Folder | What's in it |
|---|---|
| [`cpp_cuda_prep/`](./cpp_cuda_prep) | C++ fundamentals for CUDA, progressively, plus a `cuda_fundamentals/` track. |
| [`rust_dsa_practice/`](./rust_dsa_practice) | DSA problems in Rust — one Cargo crate per topic, one binary per problem under `src/bin/`. |

## Interview & CS fundamentals

| Folder | What's in it |
|---|---|
| [`fundamentals/`](./fundamentals) | One MkDocs site (`make docs FOLDER=fundamentals`) covering `dsa_prep/` (LeetCode-pattern algorithms), `os_concepts/`, `lld/` (**object-oriented** design problems — parking lot, elevator, vending machine, LRU cache, rate limiter), `security/`, `ml_fundamentals/`, `gpu_infrastructure/`, `behavioral/` (STAR framework), `interview_qa_bank/`. Also pulls in the next two folders via symlink for its nav. |
| [`system_design_foundation/`](./system_design_foundation) | ML/LLM systems design track — prerequisite concepts + tutorials. Lives at repo root (not nested in `fundamentals/`) so its standalone scripts can use the root uv venv; shows up inside `fundamentals/`'s MkDocs nav via a symlink. |
| [`system_design_practice/`](./system_design_practice) | General distributed-systems design case studies (consensus, sharding, rate limiting, ...) at staff-engineer depth — same repo-root-plus-symlink setup as above. |
| [`low-level-design/`](./low-level-design) | **Concurrency correctness** problems (buggy version → fix → test), following the Hello Interview LLD-concurrency path. Not the same thing as `fundamentals/lld/` above — that's object-oriented design, this is concurrency bugs. Easy to mix up by name; that's the whole reason for this note. |

## Language & data practice

Interview-prep notebooks: markdown explanations paired with runnable code.

| Folder | What's in it |
|---|---|
| [`python_fundamental/`](./python_fundamental) | Core Python (async fundamentals, numbered examples). |
| [`pandas_practice/`](./pandas_practice) | Series/DataFrame, I/O, indexing/merging, groupby/window ops, performance. |
| [`spark_practice/`](./spark_practice) | Spark core/SQL + `pyspark.ml`, architecture through structured streaming. |
| [`fastapi_practice/`](./fastapi_practice) | Routing/validation, Pydantic, DI/middleware, async, data-engineering-flavored API patterns. |

## Career & communication

| Folder | What's in it |
|---|---|
| [`eng-skills/`](./eng-skills) | English/communication toolkit — vocab, phrasal verbs, idioms (own MkDocs site), plus `Communication-Mastery/`, `Project_Management/`, `Book-Summaries/`. Distinct from `fundamentals/behavioral/`, which is interview-specific (STAR stories). |
| [`manual_notes/`](./manual_notes) | Loose standalone notes not yet folded into a bigger track — GPU compute, Kubernetes for AI, drift/observability, distributed training. |

## Reference library

| Folder | What's in it |
|---|---|
| [`tools/`](./tools) | ~47 individual technology write-ups (Kafka, Redis, Airflow, Grafana, Ray, Zookeeper, ...) plus a couple of head-to-head comparison docs (`kafka-vs-rabbitmq.md`, `airflow-vs-alternatives.md`). No index yet — browse by folder name or `grep`. |

## Repo plumbing

- **`Makefile`** — the `make docs/init/serve/build/clean/run` driver described above.
- **`pyproject.toml` / `uv.lock` / `.python-version`** — root venv, only for standalone scripts under repo-root folders that don't have their own uv sub-project.
- **[`scripts/mkdocs_init.sh`](./scripts/mkdocs_init.sh)** — what `make init` runs; scaffolds a folder's `docs/` symlinks + a default `mkdocs.yml`.
- **`.claude/`** — local Claude Code settings only; no repo-specific skills are checked in at present.

## Known naming traps

- `fundamentals/lld/` (object-oriented design) vs. top-level `low-level-design/`
  (concurrency correctness problems) — different content, confusingly similar
  names. See the Interview & CS fundamentals table above.
- `system_design_foundation/` and `system_design_practice/` look like they
  should live inside `fundamentals/` (its own `README.md` describes them as
  part of that site) but are deliberately repo-root siblings instead — see
  the root `Makefile`/`pyproject.toml` comments for why, and the "How to read
  this repo" section above.
