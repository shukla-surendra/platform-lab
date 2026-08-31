"""Tools the agent can call. Each is a plain Python function exposed via LangChain's
`@tool` decorator, which turns the type hints and docstring into the JSON schema the
model sees - same convention as `../langgraph_ollama_agent/tools.py`.

Unlike that project's tools (local JSON files, a bundled knowledge base), these hit a
**real** Kubernetes API server (whatever `kubectl config current-context` points at) -
no mocked fleet. Read-only tools work against any namespace; the one mutating tool
(`restart_deployment`) is hard-scoped to `config.DEMO_NAMESPACE` so the agent can never
act on real cluster workloads outside the demo scenario `seed_incident.py` creates.
"""

from __future__ import annotations

from datetime import datetime, timezone

from kubernetes import client, config as kube_config
from kubernetes.client.rest import ApiException
from langchain_core.tools import tool

import config

_loaded = False


def _api() -> client.CoreV1Api:
    global _loaded
    if not _loaded:
        kube_config.load_kube_config()
        _loaded = True
    return client.CoreV1Api()


def _apps_api() -> client.AppsV1Api:
    _api()  # ensures config is loaded
    return client.AppsV1Api()


def _pod_health(pod) -> str | None:
    """Return a short problem description for an unhealthy pod, or None if it's fine."""
    phase = pod.status.phase
    if phase in ("Pending", "Failed", "Unknown"):
        return phase

    for cs in pod.status.container_statuses or []:
        if cs.restart_count and cs.restart_count >= 3:
            waiting = cs.state.waiting.reason if cs.state.waiting else None
            return f"{waiting or 'restarting'} (restarts={cs.restart_count})"
        if cs.state.waiting and cs.state.waiting.reason not in (None, "ContainerCreating"):
            return cs.state.waiting.reason
    return None


@tool
def list_unhealthy_pods(namespace: str | None = None) -> str:
    """List Pods that are not healthy - Pending, Failed, CrashLoopBackOff, ImagePullBackOff,
    or restarting repeatedly (restart count >= 3). Pass a namespace to scope the search, or
    omit it to check the whole cluster. This is the normal first tool to call for "what's
    wrong right now" - it's the real equivalent of `kubectl get pods -A` scanned for problems.
    """
    v1 = _api()
    try:
        pods = (
            v1.list_namespaced_pod(namespace).items
            if namespace
            else v1.list_pod_for_all_namespaces().items
        )
    except ApiException as e:
        return f"Error listing pods: {e.reason}"

    problems = []
    for pod in pods:
        issue = _pod_health(pod)
        if issue:
            problems.append(f"{pod.metadata.namespace}/{pod.metadata.name}: {issue}")

    if not problems:
        scope = f"namespace '{namespace}'" if namespace else "the cluster"
        return f"No unhealthy pods found in {scope}."
    return "\n".join(problems)


@tool
def get_pod_events(namespace: str, pod_name: str) -> str:
    """Get the recent Kubernetes Events for a specific Pod (the same information
    `kubectl describe pod` shows under "Events:") - shows *why* something is happening
    (BackOff, Failed, FailedScheduling), not just the current status.
    """
    v1 = _api()
    try:
        events = v1.list_namespaced_event(
            namespace, field_selector=f"involvedObject.name={pod_name}"
        ).items
    except ApiException as e:
        return f"Error fetching events: {e.reason}"

    if not events:
        return f"No events found for pod {namespace}/{pod_name}."

    events.sort(key=lambda e: e.last_timestamp or e.event_time or datetime.min.replace(tzinfo=timezone.utc))
    lines = [
        f"{e.last_timestamp or e.event_time} [{e.type}] {e.reason}: {e.message}"
        for e in events
    ]
    return "\n".join(lines)


@tool
def get_pod_logs(namespace: str, pod_name: str, tail_lines: int = 50) -> str:
    """Get the last N lines of a Pod's container logs. Use this after events point to an
    application-level problem rather than a scheduling/image issue.
    """
    v1 = _api()
    try:
        # _preload_content=False + manual decode: the default path returns a string that's
        # literally `str(bytes_object)` (i.e. containing "b'...'" as text) rather than decoded
        # log content - a known quirk in this client version's generated deserialization for
        # non-JSON responses. Confirmed empirically: read_namespaced_pod_log() with defaults
        # returned "b'FATAL: ...\\n'" as the actual string value, not real bytes to decode.
        raw = v1.read_namespaced_pod_log(
            pod_name, namespace, tail_lines=tail_lines, _preload_content=False
        )
        logs = raw.data.decode("utf-8", errors="replace")
    except ApiException as e:
        return f"Error fetching logs for {namespace}/{pod_name}: {e.reason}"
    return logs or "(no log output)"


@tool
def check_resource_quota(namespace: str) -> str:
    """Check ResourceQuota usage in a namespace - hard limits vs. current usage for pods,
    CPU, and memory. Use this when pods are stuck Pending with no clear scheduling error;
    an exhausted quota silently blocks new pods from being admitted at all.
    """
    v1 = _api()
    try:
        quotas = v1.list_namespaced_resource_quota(namespace).items
    except ApiException as e:
        return f"Error fetching resource quotas: {e.reason}"

    if not quotas:
        return f"No ResourceQuota objects in namespace '{namespace}'."

    lines = []
    for q in quotas:
        hard = q.status.hard or {}
        used = q.status.used or {}
        for key in hard:
            lines.append(f"{q.metadata.name}: {key} = {used.get(key, '0')} / {hard[key]}")
    return "\n".join(lines)


@tool
def restart_deployment(namespace: str, deployment_name: str) -> str:
    """Trigger a rolling restart of a Deployment (equivalent to
    `kubectl rollout restart deployment/<name>`) - a real, mutating remediation action.

    Only permitted in the demo namespace this agent is scoped to; refuses everything else.
    """
    if namespace != config.DEMO_NAMESPACE:
        return (
            f"Refused: restart_deployment is only permitted in the '{config.DEMO_NAMESPACE}' "
            f"demo namespace, not '{namespace}'. This is a hard safety scope, not a suggestion."
        )

    apps = _apps_api()
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        }
    }
    try:
        apps.patch_namespaced_deployment(deployment_name, namespace, patch)
    except ApiException as e:
        return f"Error restarting deployment: {e.reason}"
    return f"Triggered rolling restart of {namespace}/{deployment_name}."


ALL_TOOLS = [
    list_unhealthy_pods,
    get_pod_events,
    get_pod_logs,
    check_resource_quota,
    restart_deployment,
]
