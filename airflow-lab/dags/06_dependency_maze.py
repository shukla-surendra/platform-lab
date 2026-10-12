"""Lesson 6: a wide, multi-layer dependency graph (29 tasks, 48 dependencies).

Unlike lesson 5 (one story with groups, mapping, branching), this one is about GRAPH SHAPE:

  layer 0  prepare                 one root
  layer 1  4 domain ingests        fan-out
  layer 2  4 x (clean -> enrich)   parallel chains
  layer 3  cross-domain joins      each join needs 2 domains  -> criss-cross edges
  layer 4  3 gold models           each needs several joins   -> diamonds
  layer 5  quality gates           all gold models feed all gates (cross_downstream)
  layer 6  publish                 gates -> 3 outputs -> signoff -> cleanup

Every task sleeps 2-6 seconds, so the Gantt view shows what really runs in parallel.
Open: Graph view (shape), Gantt view (timing), and click a task to highlight its upstream/downstream.
"""
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import chain, cross_downstream, dag


def step(task_id: str, **kwargs) -> BashOperator:
    return BashOperator(
        task_id=task_id,
        bash_command=f"echo 'running {task_id}'; sleep $((RANDOM % 5 + 2))",
        **kwargs,
    )


@dag(
    dag_id="06_dependency_maze",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=8,   # at most 8 tasks at once, so the Gantt shows queuing as well as parallelism
    tags=["lesson"],
)
def dependency_maze():
    prepare = EmptyOperator(task_id="prepare")

    # ---- layers 1-2: four domains, each a short chain, all running side by side ----
    domains = ["sales", "marketing", "finance", "product"]
    ingest, clean, enrich = {}, {}, {}
    for d in domains:
        ingest[d] = step(f"ingest_{d}")
        clean[d] = step(f"clean_{d}")
        enrich[d] = step(f"enrich_{d}")
        prepare >> ingest[d] >> clean[d] >> enrich[d]

    # ---- layer 3: joins across domains (each needs two or three domains) ----
    attribution = step("join_attribution")      # sales + marketing
    margin = step("join_margin")                # sales + finance
    engagement = step("join_engagement")        # marketing + product
    unit_economics = step("join_unit_economics")  # finance + product + sales

    [enrich["sales"], enrich["marketing"]] >> attribution
    [enrich["sales"], enrich["finance"]] >> margin
    [enrich["marketing"], enrich["product"]] >> engagement
    [enrich["finance"], enrich["product"], enrich["sales"]] >> unit_economics

    # ---- layer 4: gold models, each built from overlapping joins (diamonds) ----
    revenue_model = step("gold_revenue")
    growth_model = step("gold_growth")
    profit_model = step("gold_profit")

    [attribution, margin] >> revenue_model
    [attribution, engagement, unit_economics] >> growth_model
    [margin, unit_economics] >> profit_model

    # ---- layer 5: every gold model must pass every gate ----
    gates = [step("gate_row_counts"), step("gate_nulls"), step("gate_freshness")]
    cross_downstream([revenue_model, growth_model, profit_model], gates)

    # ---- layer 6: publish, sign off, clean up ----
    outputs = [step("publish_warehouse"), step("publish_dashboard"), step("publish_api")]
    signoff = EmptyOperator(task_id="signoff")
    archive = step("archive_run")
    cleanup = EmptyOperator(task_id="cleanup", trigger_rule="all_done")

    gates >> outputs[0]                 # warehouse needs all three gates
    [gates[0], gates[2]] >> outputs[1]  # dashboard only cares about counts + freshness
    gates[1] >> outputs[2]              # api only cares about nulls
    outputs >> signoff
    chain(signoff, archive, cleanup)


dependency_maze()
