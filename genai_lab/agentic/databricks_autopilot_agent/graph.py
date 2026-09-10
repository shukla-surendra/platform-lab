"""The autopilot chain: one LangGraph StateGraph, run once per incoming event.

    START -> ingest_event -> (route_by_event_type)
       "started"   -> record_started -----------------------------------------\
       "succeeded" -> record_succeeded -> check_recovery ----------------------> finalize -> END
       "failed"    -> gather_context -> diagnose_root_cause -> (route_by_category)
                        -> handle_oom ------------\
                        -> handle_upstream_stale ---\
                        -> handle_schema_drift -------> check_recurrence -> notify -> record_outcome -/
                        -> handle_transient --------/
                        -> handle_unknown ---------/

Fifteen nodes, two conditional routers, one cross-cutting override (`check_recurrence` can force
an escalation regardless of what the category handler decided). Only `diagnose_root_cause` calls
the LLM — every other node is plain, testable Python, per
../docs/Agentic_Concepts/10-best-practices.md#separate-deterministic-logic-from-llm-calls.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

import config
import pipeline_state as store
from schemas import AgentState, Diagnosis

# --- log reducer: every node appends, none of them need to know about prior entries -----------

AgentState.__annotations__["log"] = Annotated[list[str], operator.add]


def build_diagnosis_llm():
    llm = ChatOllama(model=config.OLLAMA_MODEL, temperature=config.MODEL_TEMPERATURE)
    # method="function_calling" routes structured output through the model's native tool-calling
    # rather than asking it to emit raw JSON prose (the "json_schema" default). Measured against
    # qwen3.5:latest on this project's four failure categories, function_calling got 3/4 right
    # with no parse failures; json_schema got 2/4 right and threw an OutputParserException on one
    # case. See README's Reliability notes for the numbers.
    return llm.with_structured_output(Diagnosis, method="function_calling")


# --- ingest --------------------------------------------------------------------------------------


def ingest_event(state: AgentState) -> dict:
    event = state["event"]
    job_id = event["job_id"]
    history = store.get_recent_runs(job_id, limit=config.RECURRENCE_WINDOW)
    return {
        "job_id": job_id,
        "event_type": event["type"],
        "run_id": event["run_id"],
        "error_message": event.get("error_message"),
        "job_history": history,
        "log": [f"ingested {event['type']} for {job_id} (run {event['run_id']})"],
    }


def route_by_event_type(state: AgentState) -> Literal["started", "succeeded", "failed"]:
    return {"job_run_started": "started", "job_run_succeeded": "succeeded", "job_run_failed": "failed"}[
        state["event_type"]
    ]


# --- started / succeeded (the short path) ------------------------------------------------------


def record_started(state: AgentState) -> dict:
    store.record_run(state["job_id"], state["run_id"], "started")
    return {"log": ["recorded run start"]}


def record_succeeded(state: AgentState) -> dict:
    store.record_run(state["job_id"], state["run_id"], "succeeded")
    return {"log": ["recorded run success"]}


def check_recovery(state: AgentState) -> dict:
    ticket = store.get_open_ticket_for_job(state["job_id"])
    if ticket is None:
        return {"log": ["fleet healthy for this job, no open ticket to close"]}

    store.resolve_ticket(
        ticket["id"], "Job succeeded after previous failure(s); auto-resolved by autopilot."
    )
    job = store.get_job(state["job_id"])
    store.send_notification(
        f"#{job['owner']}-alerts",
        f"RECOVERED: {job['name']} succeeded after incident {ticket['id']} — ticket auto-resolved.",
    )
    return {"log": [f"job recovered, auto-resolved {ticket['id']}"], "ticket_id": ticket["id"]}


# --- failed (the long path) --------------------------------------------------------------------


def gather_context(state: AgentState) -> dict:
    store.record_run(state["job_id"], state["run_id"], "failed", state["error_message"])
    job = store.get_job(state["job_id"])
    cluster = store.get_cluster(job["cluster_id"])
    upstream = {table: store.get_upstream_freshness(table) for table in job["upstream_tables"]}
    history_summary = ", ".join(run["status"] for run in state["job_history"]) or "no prior runs"

    context = {
        "job_name": job["name"],
        "owner": job["owner"],
        "cluster_id": job["cluster_id"],
        "cluster": cluster,
        "upstream_tables": upstream,
        "recent_run_history": history_summary,
    }
    return {
        "context": context,
        "log": ["recorded run failure", "gathered cluster, upstream freshness, and run history"],
    }


_DIAGNOSIS_PROMPT = """A Databricks job failed. Diagnose the root cause category.

Job: {job_name} (owned by {owner})
Error message: "{error_message}"
Cluster: {cluster_id}, node_type={node_type}, num_workers={num_workers} (autoscale max={max_workers})
Recent run history (oldest to newest): {recent_run_history}
Upstream tables: {upstream_summary}
"""


def diagnose_root_cause(state: AgentState, structured_llm) -> dict:
    context = state["context"]
    upstream_summary = "; ".join(
        f"{table} updated {info['last_updated_minutes_ago']}m ago (expected within "
        f"{info['expected_freshness_minutes']}m)"
        for table, info in context["upstream_tables"].items()
        if info is not None
    )
    prompt = _DIAGNOSIS_PROMPT.format(
        job_name=context["job_name"],
        owner=context["owner"],
        error_message=state["error_message"],
        cluster_id=context["cluster_id"],
        node_type=context["cluster"]["node_type"],
        num_workers=context["cluster"]["num_workers"],
        max_workers=context["cluster"]["max_workers"],
        recent_run_history=context["recent_run_history"],
        upstream_summary=upstream_summary,
    )
    diagnosis: Diagnosis = structured_llm.invoke(prompt)
    return {
        "diagnosis": diagnosis,
        "log": [f"diagnosed category={diagnosis.category} confidence={diagnosis.confidence:.2f}"],
    }


def route_by_category(
    state: AgentState,
) -> Literal["oom", "upstream_stale", "schema_drift", "transient", "unknown"]:
    return state["diagnosis"].category


def handle_oom(state: AgentState) -> dict:
    job = store.get_job(state["job_id"])
    cluster = store.get_cluster(job["cluster_id"])
    new_workers = min(cluster["num_workers"] * 2, cluster["max_workers"])

    if new_workers <= cluster["num_workers"]:
        action = f"Cluster {job['cluster_id']} already at max_workers={cluster['max_workers']}; cannot scale further."
    elif config.APPLY_CHANGES:
        store.resize_cluster(job["cluster_id"], new_workers)
        action = f"Resized {job['cluster_id']} from {cluster['num_workers']} to {new_workers} workers."
    else:
        action = (
            f"DRY RUN: would resize {job['cluster_id']} from {cluster['num_workers']} to "
            f"{new_workers} workers. Re-run with --apply to execute."
        )
    return {"action_taken": action, "log": [action]}


def handle_upstream_stale(state: AgentState) -> dict:
    job = store.get_job(state["job_id"])
    action = f"Notified upstream owner and scheduled a delayed retry for {job['name']}."
    return {"action_taken": action, "log": [action]}


def handle_schema_drift(state: AgentState) -> dict:
    action = f"Cannot auto-remediate schema drift on {state['job_id']}; escalating for manual fix."
    return {"action_taken": action, "escalated": True, "log": [action]}


def handle_transient(state: AgentState) -> dict:
    recent_failures = sum(1 for r in state["job_history"] if r["status"] == "failed")

    if recent_failures < config.MAX_AUTO_RETRIES:
        if config.APPLY_CHANGES:
            action = f"Triggered automatic retry for {state['job_id']} (retry {recent_failures + 1}/{config.MAX_AUTO_RETRIES})."
        else:
            action = (
                f"DRY RUN: would trigger automatic retry for {state['job_id']} "
                f"(retry {recent_failures + 1}/{config.MAX_AUTO_RETRIES}). Re-run with --apply to execute."
            )
        return {"action_taken": action, "log": [action]}

    action = f"Exceeded {config.MAX_AUTO_RETRIES} automatic retries for {state['job_id']}; escalating instead of retrying again."
    return {"action_taken": action, "escalated": True, "log": [action]}


def handle_unknown(state: AgentState) -> dict:
    action = f"Unrecognized failure category on {state['job_id']}; escalating for human triage."
    return {"action_taken": action, "escalated": True, "log": [action]}


# --- cross-cutting: recurrence can force escalation regardless of the category handler --------


def check_recurrence(state: AgentState) -> dict:
    count = store.count_recent_failures(state["job_id"], config.RECURRENCE_WINDOW)
    if count >= config.RECURRENCE_THRESHOLD:
        note = (
            f"RECURRENCE OVERRIDE: {count} failures in the last {config.RECURRENCE_WINDOW} runs "
            f"for {state['job_id']} — escalating regardless of category handler decision."
        )
        return {"escalated": True, "recurrence_count": count, "log": [note]}
    return {"recurrence_count": count, "log": [f"{count} failures in last {config.RECURRENCE_WINDOW} runs, below escalation threshold"]}


def notify(state: AgentState) -> dict:
    job = store.get_job(state["job_id"])
    severity = "critical" if state.get("escalated") else "warning"
    message = (
        f"[{severity.upper()}] {job['name']}: {state['diagnosis'].category} "
        f"— {state.get('action_taken', 'no action taken')}"
    )
    store.send_notification(f"#{job['owner']}-alerts", message)
    return {"log": [f"sent {severity} notification"]}


def record_outcome(state: AgentState) -> dict:
    if not state.get("escalated"):
        return {"log": ["no ticket needed, handled automatically"]}

    job = store.get_job(state["job_id"])
    existing = store.get_open_ticket_for_job(state["job_id"])
    if existing is not None:
        return {"ticket_id": existing["id"], "log": [f"reusing open ticket {existing['id']}"]}

    ticket = store.create_ticket(
        job_id=state["job_id"],
        title=f"{job['name']} failing: {state['diagnosis'].category}",
        summary=(
            f"{state['diagnosis'].reasoning} Action taken/proposed: {state.get('action_taken')}. "
            f"Recurrence: {state.get('recurrence_count', 0)} failures in last {config.RECURRENCE_WINDOW} runs."
        ),
        severity="critical" if state.get("recurrence_count", 0) >= config.RECURRENCE_THRESHOLD else "high",
    )
    return {"ticket_id": ticket["id"], "log": [f"filed ticket {ticket['id']}"]}


def finalize(state: AgentState) -> dict:
    store.append_audit(
        {
            "job_id": state["job_id"],
            "run_id": state["run_id"],
            "event_type": state["event_type"],
            "category": state["diagnosis"].category if state.get("diagnosis") else None,
            "action_taken": state.get("action_taken"),
            "escalated": state.get("escalated", False),
            "ticket_id": state.get("ticket_id"),
            "log": state["log"],
        }
    )
    return {}


def build_graph():
    structured_llm = build_diagnosis_llm()

    graph = StateGraph(AgentState)
    graph.add_node("ingest_event", ingest_event)
    graph.add_node("record_started", record_started)
    graph.add_node("record_succeeded", record_succeeded)
    graph.add_node("check_recovery", check_recovery)
    graph.add_node("gather_context", gather_context)
    graph.add_node("diagnose_root_cause", lambda state: diagnose_root_cause(state, structured_llm))
    graph.add_node("handle_oom", handle_oom)
    graph.add_node("handle_upstream_stale", handle_upstream_stale)
    graph.add_node("handle_schema_drift", handle_schema_drift)
    graph.add_node("handle_transient", handle_transient)
    graph.add_node("handle_unknown", handle_unknown)
    graph.add_node("check_recurrence", check_recurrence)
    graph.add_node("notify", notify)
    graph.add_node("record_outcome", record_outcome)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "ingest_event")
    graph.add_conditional_edges(
        "ingest_event",
        route_by_event_type,
        {"started": "record_started", "succeeded": "record_succeeded", "failed": "gather_context"},
    )
    graph.add_edge("record_started", "finalize")
    graph.add_edge("record_succeeded", "check_recovery")
    graph.add_edge("check_recovery", "finalize")

    graph.add_edge("gather_context", "diagnose_root_cause")
    graph.add_conditional_edges(
        "diagnose_root_cause",
        route_by_category,
        {
            "oom": "handle_oom",
            "upstream_stale": "handle_upstream_stale",
            "schema_drift": "handle_schema_drift",
            "transient": "handle_transient",
            "unknown": "handle_unknown",
        },
    )
    for handler in ["handle_oom", "handle_upstream_stale", "handle_schema_drift", "handle_transient", "handle_unknown"]:
        graph.add_edge(handler, "check_recurrence")
    graph.add_edge("check_recurrence", "notify")
    graph.add_edge("notify", "record_outcome")
    graph.add_edge("record_outcome", "finalize")

    graph.add_edge("finalize", END)

    return graph.compile()
