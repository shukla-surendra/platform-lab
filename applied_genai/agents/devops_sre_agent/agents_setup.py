"""Builds the three-agent SRE team and wires it to a local Ollama model.

Triage Agent (entrypoint)
  -- handoff --> Observability Agent (CloudWatch alarms / logs)
                   -- handoff --> Compute Agent (EC2 / ECS)
                                     -- handoff --> back to Triage Agent (files the ticket)

Triage can also hand off straight to Compute when it already has enough to act on. Handoffs are
the OpenAI Agents SDK's multi-agent primitive: a specialist agent is exposed to the
triage agent as a callable tool ("transfer_to_compute_agent"), and once called, control (and the
full conversation) transfers to that agent for the rest of the turn. This is a different mental
model from LangGraph's explicit graph of nodes/edges — the model itself decides whether and when
to hand off, rather than the control flow being fixed in a graph ahead of time.
"""

from __future__ import annotations

from agents import Agent, OpenAIChatCompletionsModel, ModelSettings
from openai import AsyncOpenAI

import config
from tools import COMPUTE_TOOLS, OBSERVABILITY_TOOLS, TRIAGE_TOOLS


def _build_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(base_url=config.OLLAMA_BASE_URL, api_key="ollama")
    return OpenAIChatCompletionsModel(model=config.OLLAMA_MODEL, openai_client=client)


def build_triage_agent() -> Agent:
    model = _build_model()
    settings = ModelSettings(temperature=config.MODEL_TEMPERATURE)

    # Created without handoffs first, then wired into a cycle below — Agent is a plain mutable
    # object, so the three agents can reference each other (Triage -> Observability -> Compute ->
    # Triage) without needing a forward-reference workaround.
    triage_agent = Agent(
        name="Triage Agent",
        instructions=(
            "You are the on-call SRE triage agent, the entry point for every request. "
            "Step 1: call get_fleet_overview to see what's currently active. "
            "Step 2: if there are active alarms, hand off to the Observability Agent to find root "
            "cause — do not try to diagnose alarms or logs yourself, you don't have those tools. "
            "Step 3 (after the Observability/Compute agents hand back to you with findings and any "
            "remediation taken or proposed): file an incident ticket with create_incident_ticket "
            "summarizing root cause and the action taken/proposed, then give the human a clear, "
            "concise final summary including the ticket id. "
            "If the fleet is already healthy, or the human is just asking a status question, answer "
            "directly without handing off."
        ),
        model=model,
        model_settings=settings,
        tools=TRIAGE_TOOLS,
    )

    observability_agent = Agent(
        name="Observability Agent",
        instructions=(
            "You are the observability specialist on an SRE team, handling CloudWatch alarms and "
            "service logs. Find the active alarms (list_cloudwatch_alarms with "
            "state_filter='ALARM'), get detail on each (describe_alarm), and tail logs for any "
            "affected service (tail_service_logs) to find the root cause signal (e.g. an ERROR "
            "pattern). You have no remediation tools. "
            "Required last step, every time: hand off to the Compute Agent with a clear statement "
            "of what's wrong and which resource (instance id / service name) needs attention — "
            "never end the conversation yourself, you can only diagnose, not remediate."
        ),
        model=model,
        model_settings=settings,
        tools=OBSERVABILITY_TOOLS,
        handoffs=[],  # filled in below
    )

    compute_agent = Agent(
        name="Compute Agent",
        instructions=(
            "You are the compute specialist on an SRE team, handling EC2 and ECS. Investigate with "
            "list_ec2_instances/describe_instance and list_ecs_services to confirm the resource the "
            "Observability Agent flagged. reboot_instance and scale_ecs_service are mutating: while "
            "not applied, they return a DRY RUN description instead of taking effect — report that "
            "plainly, don't claim the action happened if the tool says DRY RUN. "
            "Required last step, every time: once you've acted (or proposed an action), you MUST "
            "hand off back to the Triage Agent with a one-paragraph summary of what you found and "
            "did — never end the conversation yourself, only the Triage Agent files the incident "
            "ticket and gives the final answer to the human."
        ),
        model=model,
        model_settings=settings,
        tools=COMPUTE_TOOLS,
        handoffs=[],  # filled in below
    )

    triage_agent.handoffs = [observability_agent, compute_agent]
    observability_agent.handoffs = [compute_agent, triage_agent]
    compute_agent.handoffs = [triage_agent]

    return triage_agent
