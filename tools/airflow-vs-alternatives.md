# Airflow vs. the Alternatives: Prefect, Dagster, Argo Workflows

[`airflow/`](airflow/README.md)'s README and production-scenarios doc are grounded in a
real, locally-verified Airflow instance — every claim there was actually run. This doc is
different in kind: Prefect, Dagster, and Argo Workflows aren't running anywhere in this
lab, so what follows is public, well-established knowledge about how each is architected,
not something re-verified here. Treat Airflow's side of each comparison as tested; treat
the others as accurately described but not independently re-confirmed in this workspace.

## The mechanism-level differences

### Airflow: a DAG of tasks, parsed from Python, orchestrated by a separate scheduler process

The DAG's *structure* is determined by parsing the Python file — the scheduler runs that
file repeatedly (verified: `AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL`) to discover the
graph, then decides scheduling independently of any single execution. This split
(structure discovered by parsing, separate from any one run) is *why* Airflow DAGs are
conventionally closer to static — dynamic, runtime-dependent branching is possible
(`BranchPythonOperator`, dynamic task mapping since 2.3) but works *against* the framework's
natural parse-time model, not with it.

### Prefect: the flow *is* the Python function — structure and execution aren't split

A Prefect `@flow`-decorated function runs top to bottom like ordinary Python — `if`/`else`,
loops, and runtime-dependent branching are just Python control flow, not a special DAG
construct layered on top. There's no separate "parse the file to discover the graph" step
the way Airflow has; the graph *is* whatever code path actually executed. This is a real,
structural difference, not a styling preference — it's why genuinely dynamic pipelines
(the exact set of downstream steps depends on data seen at runtime) fit Prefect's model
more naturally than Airflow's.

### Dagster: the core abstraction is the *asset*, not the *task*

Where Airflow and Prefect both ask "what steps need to run, in what order," Dagster's
primary model (**Software-Defined Assets**) asks "what data assets exist, and how is each
one produced" — a table, a model, a file is a first-class object with declared
dependencies on other assets, and Dagster derives the execution graph *from* those asset
dependencies rather than the other way around. This genuinely changes what the tool is
good at surfacing: asset-level lineage, staleness ("is this table's data downstream of a
newer version of its inputs"), and per-asset testing are native concepts, not something
bolted onto a task graph after the fact. Dagster also supports a plain task-centric mode
(`@op`/`@job`) for pipelines that don't fit the asset framing.

### Argo Workflows: Kubernetes-native, each step is its own pod

Workflows are Kubernetes Custom Resources (YAML, or a Python SDK that generates the same
YAML) — every step runs as an actual, isolated Kubernetes pod, scheduled by Kubernetes
itself, not by a separate always-running scheduler process the way Airflow's scheduler is.
Airflow *can* get per-task pod isolation too (`KubernetesExecutor`), but the DAG-authoring
model stays Python either way; Argo's authoring model is the Kubernetes resource model
itself, which is the real draw for teams already deep in Kubernetes-native tooling (Argo
Events for triggering, Argo CD for GitOps deployment of the workflows themselves).

### Worth a one-line mention: Luigi and dbt

**Luigi** (Spotify, pre-dates Airflow) pioneered the task-dependency-graph idea Airflow
built on, but has no built-in scheduler of its own (relies on cron or external triggering)
and has been largely superseded by Airflow for new adoption — mentioned here mainly as the
historical predecessor, not a live contender. **dbt** is not actually an orchestrator at
all — it's a SQL transformation tool with its own internal DAG (of SQL models within a
warehouse) — it's commonly confused with or paired alongside Airflow/Dagster specifically
because a `dbt run` step is itself usually just *one task* inside a larger Airflow/Dagster
pipeline, not a replacement for either.

## Which to use where

**Reach for Airflow when:**
- Broad third-party integration coverage matters — Airflow's provider ecosystem (AWS, GCP,
  Azure, Snowflake, Databricks, and hundreds more) is the deepest and most mature of any
  option here, a real practical factor for a team gluing together many external systems.
- The team already knows it, or hiring for Airflow experience specifically is easier than
  for a newer tool — it remains the most widely deployed orchestrator, a genuine factor
  independent of any technical merit comparison.
- Pipelines are naturally closer to static/scheduled batch ETL — "run this DAG every day
  at 2am" is Airflow's best-fit case, not an edge case.

**Reach for Prefect when:**
- Pipeline structure is genuinely dynamic — the actual steps needed depend on data only
  known at runtime, and expressing that as ordinary Python control flow (not a
  workaround like `BranchPythonOperator`) is a real win.
- A lighter local-development loop matters — running and debugging a flow as a plain
  Python function, without a separate scheduler/webserver/metadata-DB stack running
  locally, is a genuinely different (often faster) iteration experience for smaller teams.

**Reach for Dagster when:**
- The actual problem is "we need to understand and trust our data assets" (lineage,
  freshness, per-asset data quality checks) more than "we need to run steps in order" —
  this is a different question, and Dagster's asset model answers it more directly than
  bolting lineage tracking onto a task-centric tool after the fact.
- The team is already dbt-heavy — Dagster's asset model maps onto dbt models unusually
  cleanly compared to treating each `dbt run` as an opaque task.

**Reach for Argo Workflows when:**
- The organization is Kubernetes-native already, and workflow orchestration living as
  another Kubernetes-native primitive (alongside Argo CD, Argo Events) is a real
  operational win, not added complexity.
- Per-step container isolation is a hard requirement by default, not an opt-in executor
  choice.

**The actual decision variable is rarely "which is more powerful"** — all four can express
most real pipelines. It's whether the team's pipelines are naturally static-batch
(Airflow), dynamically-structured (Prefect), asset/lineage-centric (Dagster), or already
living inside a Kubernetes-native operating model (Argo) — and, in practice, how much
existing integration/hiring-pool gravity Airflow's incumbency carries for the specific
integrations a team actually needs.

## Where the theory lives

- [`airflow/README.md`](airflow/README.md) and
  [`airflow/production-scenarios.md`](airflow/production-scenarios.md) — the
  locally-verified half of this comparison.
- [`18_message_queues_and_event_driven_semantics.md`](../../../fundamentals/system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md) —
  the adjacent-but-distinct problem of continuous data movement (queues/streams), worth
  reading alongside this doc to see the actual boundary between "orchestrate discrete,
  DAG-shaped work" and "move data continuously."
