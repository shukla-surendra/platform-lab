"""Tools the agents can call, grouped by domain. Every tool reads/writes infra_state.json — a
mock fleet, never a real cloud account. Mutating tools (reboot_instance, scale_ecs_service) are
gated by config.APPLY_CHANGES: while it's False (the default) they report what they *would* do
without changing state, mirroring a real SRE agent that proposes a remediation before executing
it.
"""

from __future__ import annotations

from agents import function_tool

import config
import infra_state as state


def _find(items: list[dict], key: str, value: str) -> dict | None:
    return next((item for item in items if item[key] == value), None)


# --- Observability: alarms and logs -----------------------------------------------------------


@function_tool
def list_cloudwatch_alarms(state_filter: str | None = None) -> str:
    """List CloudWatch alarms, optionally filtered by state.

    Args:
        state_filter: Only return alarms in this state, e.g. "ALARM" or "OK". Omit for all alarms.
    """
    alarms = state.load_state()["cloudwatch_alarms"]
    if state_filter:
        alarms = [a for a in alarms if a["state"].lower() == state_filter.lower()]
    if not alarms:
        return "No matching alarms."
    return "\n".join(
        f"{a['id']} ({a['name']}) on {a['resource_id']}: state={a['state']}, "
        f"metric={a['metric']}, threshold={a['threshold']}"
        for a in alarms
    )


@function_tool
def describe_alarm(alarm_id: str) -> str:
    """Get full detail for one CloudWatch alarm by id.

    Args:
        alarm_id: The alarm id, e.g. "alarm-cpu-web01".
    """
    alarm = _find(state.load_state()["cloudwatch_alarms"], "id", alarm_id)
    if not alarm:
        return f"No alarm with id '{alarm_id}'."
    return "\n".join(f"{k}: {v}" for k, v in alarm.items())


@function_tool
def tail_service_logs(service_name: str, lines: int = 10) -> str:
    """Return the most recent log lines for a service, useful for spotting ERROR/WARN patterns.

    Args:
        service_name: The service to fetch logs for, e.g. "checkout-service".
        lines: How many of the most recent log lines to return.
    """
    logs = state.load_state()["service_logs"].get(service_name)
    if logs is None:
        return f"No logs found for service '{service_name}'."
    return "\n".join(logs[-lines:])


# --- Compute: EC2 and ECS --------------------------------------------------------------------


@function_tool
def list_ec2_instances() -> str:
    """List all EC2 instances with their current state, CPU, and health status checks."""
    instances = state.load_state()["ec2_instances"]
    return "\n".join(
        f"{i['id']} ({i['name']}, service={i['service']}): state={i['state']}, "
        f"cpu={i['cpu_percent']}%, status_checks={i['status_checks_passed']}/{i['status_checks_total']}"
        for i in instances
    )


@function_tool
def describe_instance(instance_id: str) -> str:
    """Get full detail for one EC2 instance by id.

    Args:
        instance_id: The instance id, e.g. "i-0a1b2c3d".
    """
    instance = _find(state.load_state()["ec2_instances"], "id", instance_id)
    if not instance:
        return f"No instance with id '{instance_id}'."
    return "\n".join(f"{k}: {v}" for k, v in instance.items())


@function_tool
def reboot_instance(instance_id: str) -> str:
    """Reboot an EC2 instance. Use this to recover an instance with failing status checks or
    runaway resource usage. This is a mutating action, gated behind an explicit --apply flag.

    Args:
        instance_id: The instance id to reboot, e.g. "i-0a1b2c3d".
    """
    fleet = state.load_state()
    instance = _find(fleet["ec2_instances"], "id", instance_id)
    if not instance:
        return f"No instance with id '{instance_id}'."

    if not config.APPLY_CHANGES:
        return (
            f"DRY RUN: would reboot {instance_id} ({instance['name']}), currently "
            f"cpu={instance['cpu_percent']}%, status_checks={instance['status_checks_passed']}/"
            f"{instance['status_checks_total']}. Re-run with --apply to execute."
        )

    instance["state"] = "running"
    instance["cpu_percent"] = 20
    instance["status_checks_passed"] = instance["status_checks_total"]
    state.save_state(fleet)
    return f"Rebooted {instance_id} ({instance['name']}). Status checks now passing, CPU normalized."


@function_tool
def list_ecs_services() -> str:
    """List all ECS services with desired vs running task counts."""
    services = state.load_state()["ecs_services"]
    return "\n".join(
        f"{s['name']} (cluster={s['cluster']}): running={s['running_count']}/{s['desired_count']}"
        for s in services
    )


@function_tool
def scale_ecs_service(service_name: str, desired_count: int) -> str:
    """Set the desired task count for an ECS service. Use this to scale a service back up (or
    down). This is a mutating action, gated behind an explicit --apply flag.

    Args:
        service_name: The ECS service name, e.g. "checkout-service".
        desired_count: The new desired task count.
    """
    fleet = state.load_state()
    service = _find(fleet["ecs_services"], "name", service_name)
    if not service:
        return f"No ECS service named '{service_name}'."

    if not config.APPLY_CHANGES:
        return (
            f"DRY RUN: would scale {service_name} from desired={service['desired_count']} to "
            f"desired={desired_count} (currently running={service['running_count']}). "
            "Re-run with --apply to execute."
        )

    service["desired_count"] = desired_count
    service["running_count"] = desired_count
    state.save_state(fleet)
    return f"Scaled {service_name} to desired={desired_count}; running_count now matches."


@function_tool
def list_s3_buckets() -> str:
    """List S3 buckets with size and last backup time."""
    buckets = state.load_state()["s3_buckets"]
    return "\n".join(f"{b['name']}: {b['size_gb']} GB, last_backup={b['last_backup']}" for b in buckets)


# --- Incident management -----------------------------------------------------------------------


@function_tool
def get_fleet_overview() -> str:
    """Return a one-shot summary of fleet health: instance count, ECS drift, and active alarms.
    Always the right first call when triaging an unfamiliar alert.
    """
    fleet = state.load_state()
    instances = fleet["ec2_instances"]
    services = fleet["ecs_services"]
    active_alarms = [a for a in fleet["cloudwatch_alarms"] if a["state"] == "ALARM"]
    drifted = [s for s in services if s["running_count"] != s["desired_count"]]

    lines = [
        f"{len(instances)} EC2 instances, {len(services)} ECS services, "
        f"{len(active_alarms)} active alarm(s).",
    ]
    for alarm in active_alarms:
        lines.append(f"  ALARM: {alarm['id']} ({alarm['name']}) on {alarm['resource_id']}")
    for service in drifted:
        lines.append(
            f"  DRIFT: {service['name']} running {service['running_count']}/{service['desired_count']}"
        )
    if not active_alarms and not drifted:
        lines.append("  Fleet is healthy.")
    return "\n".join(lines)


@function_tool
def create_incident_ticket(title: str, summary: str, severity: str) -> str:
    """File an incident ticket to record what was found and what remediation was taken/proposed.

    Args:
        title: Short ticket title.
        summary: What was observed and what action was taken or proposed.
        severity: One of "low", "medium", "high", "critical".
    """
    fleet = state.load_state()
    tickets = fleet["tickets"]
    next_id = f"INC-{len(tickets) + 1:04d}"
    tickets.append(
        {
            "id": next_id,
            "title": title,
            "summary": summary,
            "severity": severity,
            "status": "open",
            "resolution": None,
            "created": state.now_iso(),
        }
    )
    state.save_state(fleet)
    return f"Created ticket {next_id} ({severity}): {title}"


@function_tool
def resolve_incident_ticket(ticket_id: str, resolution: str) -> str:
    """Mark an incident ticket resolved with a resolution note.

    Args:
        ticket_id: The ticket id, e.g. "INC-0001".
        resolution: What fixed it.
    """
    fleet = state.load_state()
    ticket = _find(fleet["tickets"], "id", ticket_id)
    if not ticket:
        return f"No ticket with id '{ticket_id}'."
    ticket["status"] = "resolved"
    ticket["resolution"] = resolution
    state.save_state(fleet)
    return f"Resolved {ticket_id}: {resolution}"


@function_tool
def list_incident_tickets() -> str:
    """List all incident tickets and their status."""
    tickets = state.load_state()["tickets"]
    if not tickets:
        return "No tickets filed."
    return "\n".join(f"{t['id']} [{t['status']}] ({t['severity']}) {t['title']}" for t in tickets)


OBSERVABILITY_TOOLS = [list_cloudwatch_alarms, describe_alarm, tail_service_logs]
COMPUTE_TOOLS = [
    list_ec2_instances,
    describe_instance,
    reboot_instance,
    list_ecs_services,
    scale_ecs_service,
    list_s3_buckets,
]
TRIAGE_TOOLS = [
    get_fleet_overview,
    create_incident_ticket,
    resolve_incident_ticket,
    list_incident_tickets,
]
