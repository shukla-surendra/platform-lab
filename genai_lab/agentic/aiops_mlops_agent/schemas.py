"""Structured-output schemas for the two LLM calls in the graph: classifying a free-text query
(automode events skip this -- their domain/entity are already explicit) and diagnosing root
cause + recommended action once context and knowledge have been gathered.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Domain = Literal["model_drift", "infra_anomaly", "pipeline_failure", "unknown"]

# The set of mutating actions diagnose() is allowed to recommend, keyed by domain. "monitor"
# is always available and means "watch, don't act."
ACTIONS_BY_DOMAIN: dict[str, list[str]] = {
    "model_drift": ["rollback_model", "trigger_retrain", "monitor"],
    "infra_anomaly": ["restart_service", "scale_service", "monitor"],
    "pipeline_failure": ["retry_pipeline", "rollback_deployment", "monitor"],
}


class EventClassification(BaseModel):
    """Extracted from a free-text on-call query: which domain and which entity it concerns."""

    domain: Domain = Field(description="Which of the three domains this query is about")
    entity: str = Field(
        description="The specific model_name, host_id/service_name, or pipeline_id the query "
        "refers to. Must match a real entity name mentioned or clearly implied in the query."
    )
    reasoning: str = Field(description="One sentence on why this domain/entity was chosen")


class Diagnosis(BaseModel):
    """Produced after gathering domain context and retrieving relevant knowledge-base passages."""

    reasoning: str = Field(
        description="Step-by-step reasoning grounded in the gathered context and retrieved "
        "knowledge-base passages. Reference specific numbers/log lines, not vague generalities."
    )
    root_cause: str = Field(description="One or two sentence root-cause statement")
    recommended_action: str = Field(
        description="Exactly one action name from the allowed list for this domain"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the diagnosis, 0-1")
    escalate: bool = Field(
        description="True if this should go to a human regardless of confidence -- e.g. the "
        "knowledge base explicitly says no automated action resolves this category"
    )
