"""Typed shapes shared between graph.py and daemon.py."""

from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field
from typing_extensions import NotRequired

Category = Literal["oom", "upstream_stale", "schema_drift", "transient", "unknown"]


class Diagnosis(BaseModel):
    """Structured output the LLM must produce for a failed run. Field order matters here:
    `reasoning` is defined before `category` so the model writes its reasoning first, in the
    same structured call — a "think, then answer" ordering shown to noticeably improve category
    accuracy over asking for the category field first (see README's Reliability notes).
    """

    reasoning: str = Field(description="Step-by-step reasoning about the error message and context, before deciding a category.")
    category: Category = Field(
        description=(
            "Root cause category, chosen AFTER the reasoning above. "
            "oom = out of memory / heap / driver or executor crash from resource exhaustion. "
            "upstream_stale = a source table has not been updated recently enough. "
            "schema_drift = column/schema mismatch, AnalysisException about columns. "
            "transient = network/timeout/connection errors, likely to succeed on a plain retry. "
            "unknown = none of the above clearly applies."
        )
    )
    confidence: float = Field(description="0.0 to 1.0 confidence in this category.")
    recommended_action: str = Field(description="One short sentence: the recommended remediation.")


class AgentState(TypedDict):
    event: dict
    job_id: str
    event_type: Literal["job_run_started", "job_run_succeeded", "job_run_failed"]
    run_id: str
    error_message: NotRequired[str | None]

    job_history: NotRequired[list[dict]]
    context: NotRequired[dict]
    diagnosis: NotRequired[Diagnosis]
    recurrence_count: NotRequired[int]
    escalated: NotRequired[bool]
    action_taken: NotRequired[str]
    ticket_id: NotRequired[str | None]

    log: list[str]
