"""The agent graph: one LangGraph pipeline shared by all three domains (model_drift,
infra_anomaly, pipeline_failure), used both for one-shot CLI queries and for automode events.

    START -> classify -> gather_context -> retrieve_knowledge -> diagnose -> decide -> act
          -> notify -> record -> END

Only `classify` (free-text queries only) and `diagnose` call the LLM. Every other node is plain,
deterministic Python that calls MCP tools directly by name -- `gather_context` already knows
which tools a given domain needs, so there's no reason to spend a model call deciding that too.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

import config
import mcp_client
import state as state_module
from llm import get_chat_model, structured_output_method
from mcp_client import call_tool
from schemas import ACTIONS_BY_DOMAIN, Diagnosis, EventClassification


class AgentState(TypedDict, total=False):
    input_event: dict | None
    input_query: str | None
    domain: str
    entity: str
    context: dict
    knowledge: list[dict]
    diagnosis: dict
    auto_remediate: bool
    severity: str
    action_result: Any
    ticket: dict | None
    notification: str


# --- Nodes ---------------------------------------------------------------------------------------

async def _invoke_structured(structured_llm, prompt: str, retries: int = 2):
    """`.with_structured_output(method="function_calling")` returns None (not an exception) when
    the model answers without making the expected tool call -- observed occasionally on
    qwen3.5:latest against longer prompts, presumably rarer but not impossible on other models
    too. Retry a few times before giving up; callers decide what a `None` after retries means."""
    for attempt in range(retries + 1):
        result = await structured_llm.ainvoke(prompt)
        if result is not None:
            return result
    return None


async def classify_node(agent_state: AgentState, llm) -> dict:
    event = agent_state.get("input_event")
    if event:
        # Automode events already carry an explicit domain/entity -- no LLM call needed.
        return {"domain": event["domain"], "entity": event["entity"]}

    query = agent_state["input_query"]
    structured_llm = llm.with_structured_output(EventClassification, method=structured_output_method())
    result = await _invoke_structured(
        structured_llm,
        "Classify this on-call query into a domain and the specific entity it concerns.\n\n"
        f"Query: {query}\n\n"
        "Valid domains:\n"
        "- model_drift: the issue is about a deployed ML model's predictions, accuracy, or drift\n"
        "- infra_anomaly: the issue is about a host/service's CPU, memory, latency, or errors\n"
        "- pipeline_failure: the issue is about a CI/CD or data pipeline run failing\n\n"
        "entity must be the exact model_name, service_name, or pipeline_id mentioned or clearly "
        "implied (known models: fraud-detection, churn-prediction, recsys-ranker; known "
        "services: checkout-api, model-serving; known pipelines: pl-daily-etl, "
        "pl-feature-refresh, pl-model-retrain)."
    )
    if result is None:
        # Can't identify domain/entity at all -- fail into "unknown" so decide() escalates
        # instead of the graph crashing on a bad model response.
        return {"domain": "unknown", "entity": query[:80]}
    return {"domain": result.domain, "entity": result.entity}


async def gather_context_node(agent_state: AgentState, ops_tools: dict) -> dict:
    domain, entity = agent_state["domain"], agent_state["entity"]

    if domain == "model_drift":
        status = await call_tool(ops_tools, "get_model_status", model_name=entity)
        version = status["deployed_version"]
        context = {
            "status": status,
            "data_drift": await call_tool(ops_tools, "check_data_drift", model_name=entity, version=version),
            "model_drift": await call_tool(ops_tools, "check_model_drift", model_name=entity, version=version),
            # Per the drift-response runbook and the fraud-detection postmortem: always check
            # the feature pipeline before diagnosing drift as "the model needs retraining."
            "feature_pipeline": await call_tool(ops_tools, "get_pipeline_run", pipeline_id="pl-feature-refresh"),
        }

    elif domain == "infra_anomaly":
        host_ids = await call_tool(ops_tools, "list_hosts")
        hosts = []
        for host_id in host_ids:
            host = await call_tool(ops_tools, "get_host_metrics", host_id=host_id)
            if host["service"] == entity:
                hosts.append({"host_id": host_id, **host})
        context = {
            "hosts": hosts,
            "logs": await call_tool(ops_tools, "tail_service_logs", service_name=entity, lines=50),
        }

    elif domain == "pipeline_failure":
        context = {"run": await call_tool(ops_tools, "get_pipeline_run", pipeline_id=entity)}

    else:
        context = {}

    return {"context": context}


async def retrieve_knowledge_node(agent_state: AgentState, knowledge_tools: dict) -> dict:
    query = f"{agent_state['domain']} {agent_state['entity']} " + json.dumps(agent_state["context"])[:400]
    results = await call_tool(knowledge_tools, "search_knowledge_base", query=query, k=config.RETRIEVAL_K)
    return {"knowledge": results}


async def diagnose_node(agent_state: AgentState, llm) -> dict:
    domain = agent_state["domain"]
    allowed_actions = ACTIONS_BY_DOMAIN.get(domain, ["monitor"])
    passages = "\n\n".join(f"[{k['source']}]\n{k['text']}" for k in agent_state["knowledge"]) or "(none found)"

    prompt = (
        f"Domain: {domain}\nEntity: {agent_state['entity']}\n\n"
        f"Gathered live context:\n{json.dumps(agent_state['context'], indent=2)}\n\n"
        f"Relevant knowledge base passages (runbooks/postmortems/model cards/pipeline docs):\n{passages}\n\n"
        f"Allowed values for recommended_action: {allowed_actions}\n\n"
        "Diagnose the root cause using the live context, grounded in the knowledge base guidance "
        "above where it applies. Recommend exactly one action from the allowed list. Set "
        "escalate=true if the knowledge base indicates no automated action resolves this "
        "situation (e.g. upstream schema drift, a genuine capacity/config problem) even if "
        "you're confident about the root cause itself."
    )
    structured_llm = llm.with_structured_output(Diagnosis, method=structured_output_method())
    result: Diagnosis | None = await _invoke_structured(structured_llm, prompt)
    if result is None:
        # The model never produced a parseable diagnosis after retries -- escalate rather than
        # crash the graph or (worse) silently proceed on a fabricated root cause.
        result = Diagnosis(
            reasoning="Structured diagnosis output failed after retries; escalating instead of guessing.",
            root_cause="Diagnosis unavailable -- the model did not return a parseable structured response.",
            recommended_action="monitor",
            confidence=0.0,
            escalate=True,
        )
    elif result.recommended_action not in allowed_actions:
        result.recommended_action = "monitor"
    return {"diagnosis": result.model_dump()}


def decide_node(agent_state: AgentState) -> dict:
    diagnosis = agent_state["diagnosis"]
    auto_remediate = (
        not diagnosis["escalate"]
        and diagnosis["confidence"] >= config.AUTO_REMEDIATE_CONFIDENCE
        and diagnosis["recommended_action"] != "monitor"
    )
    if diagnosis["escalate"] or diagnosis["confidence"] < 0.5:
        severity = "critical"
    elif not auto_remediate:
        severity = "high"
    else:
        severity = "medium"
    return {"auto_remediate": auto_remediate, "severity": severity}


_ACTION_ARG_BUILDERS = {
    "rollback_model": lambda entity, context: {"model_name": entity},
    "trigger_retrain": lambda entity, context: {"model_name": entity},
    "restart_service": lambda entity, context: {"service_name": entity},
    "scale_service": lambda entity, context: {
        "service_name": entity,
        "desired_count": max((h["desired_count"] for h in context.get("hosts", [])), default=2) + 2,
    },
    "retry_pipeline": lambda entity, context: {"pipeline_id": entity},
    "rollback_deployment": lambda entity, context: {"pipeline_id": entity},
}


async def act_node(agent_state: AgentState, ops_tools: dict) -> dict:
    if not agent_state["auto_remediate"]:
        return {"action_result": "Escalated to human review; no automated action taken."}

    action = agent_state["diagnosis"]["recommended_action"]
    build_args = _ACTION_ARG_BUILDERS.get(action)
    if build_args is None:
        return {"action_result": "No action taken; monitoring."}

    args = build_args(agent_state["entity"], agent_state["context"])
    result = await call_tool(ops_tools, action, **args)
    return {"action_result": result}


def notify_node(agent_state: AgentState) -> dict:
    diagnosis = agent_state["diagnosis"]
    message = (
        f"[{agent_state['severity'].upper()}] {agent_state['domain']}/{agent_state['entity']}: "
        f"{diagnosis['root_cause']} -- {agent_state['action_result']}"
    )
    state_module.add_notification(message, agent_state["severity"])
    print(f"[notify] {message}")
    return {"notification": message}


async def record_node(agent_state: AgentState, ops_tools: dict) -> dict:
    diagnosis = agent_state["diagnosis"]
    title = f"{agent_state['domain'].replace('_', ' ').title()}: {agent_state['entity']}"
    summary = (
        f"{diagnosis['root_cause']} Recommended action: {diagnosis['recommended_action']} "
        f"(confidence {diagnosis['confidence']}). Result: {agent_state['action_result']}"
    )
    ticket = await call_tool(
        ops_tools, "create_incident_ticket",
        title=title, severity=agent_state["severity"], domain=agent_state["domain"], summary=summary,
    )

    applied = isinstance(agent_state["action_result"], str) and agent_state["action_result"].startswith("APPLIED")
    if applied:
        ticket = await call_tool(
            ops_tools, "resolve_incident_ticket",
            ticket_id=ticket["ticket_id"], resolution="Automated remediation applied and confirmed.",
        )

    _append_audit_log(agent_state, ticket)
    return {"ticket": ticket}


def _append_audit_log(agent_state: AgentState, ticket: dict) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "domain": agent_state["domain"],
        "entity": agent_state["entity"],
        "severity": agent_state["severity"],
        "diagnosis": agent_state["diagnosis"],
        "auto_remediate": agent_state["auto_remediate"],
        "action_result": agent_state["action_result"],
        "ticket_id": ticket["ticket_id"],
        "ticket_status": ticket["status"],
    }
    with open(config.AUDIT_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# --- Graph assembly --------------------------------------------------------------------------

async def build_graph(apply_changes: bool = False):
    tools = await mcp_client.load_tools(apply_changes)
    ops_tools = {t.name: t for t in tools["ops"]}
    knowledge_tools = {t.name: t for t in tools["knowledge"]}
    llm = get_chat_model()

    # Plain lambdas here would return an un-awaited coroutine object (LangGraph only detects a
    # node as async by inspecting the callable itself with `iscoroutinefunction`); these small
    # `async def` wrappers are needed so the closures over llm/ops_tools/knowledge_tools stay
    # genuinely async.
    async def classify(s: AgentState) -> dict:
        return await classify_node(s, llm)

    async def gather_context(s: AgentState) -> dict:
        return await gather_context_node(s, ops_tools)

    async def retrieve_knowledge(s: AgentState) -> dict:
        return await retrieve_knowledge_node(s, knowledge_tools)

    async def diagnose(s: AgentState) -> dict:
        return await diagnose_node(s, llm)

    async def act(s: AgentState) -> dict:
        return await act_node(s, ops_tools)

    async def record(s: AgentState) -> dict:
        return await record_node(s, ops_tools)

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("gather_context", gather_context)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("diagnose", diagnose)
    graph.add_node("decide", decide_node)
    graph.add_node("act", act)
    graph.add_node("notify", notify_node)
    graph.add_node("record", record)

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "gather_context")
    graph.add_edge("gather_context", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "diagnose")
    graph.add_edge("diagnose", "decide")
    graph.add_edge("decide", "act")
    graph.add_edge("act", "notify")
    graph.add_edge("notify", "record")
    graph.add_edge("record", END)

    return graph.compile()
