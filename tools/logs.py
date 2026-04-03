"""
GCP Compute MCP Server - Log Tools

Tools for querying VM event logs.
"""

from datetime import datetime, timedelta
from data_store import VM_BY_ID, VMS, LOGS, resolve_project_id

# Anchor time for log queries
ANCHOR_TIME = datetime(2026, 3, 10, 12, 0, 0)


def get_vm_logs(
    vm_id: str,
    hours: int = 24,
    event_type: str = None
) -> dict:
    """
    Get event logs for a specific VM.

    Returns logs sorted newest first with summary counts.

    Args:
        vm_id: The VM ID
        hours: Number of hours to look back (1-168, default: 24, max: 168 = 7 days)
        event_type: Optional filter ("START", "STOP", "RESTART", "ERROR")
    """
    vm = VM_BY_ID.get(vm_id)
    if not vm:
        return {
            "error": "VM not found",
            "hint": f"No VM with ID '{vm_id}'. Call tool_list_vms with a valid project_id to find VM IDs, or call tool_search_vms to search by name."
        }

    logs = LOGS.get(vm_id, [])

    # Validate and clamp hours
    hours = max(1, min(168, hours))

    # Calculate cutoff time
    cutoff = ANCHOR_TIME - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Filter by time
    filtered = [log for log in logs if log.timestamp >= cutoff_str]

    # Filter by event type if specified
    if event_type:
        event_type_upper = event_type.upper()
        valid_types = ["START", "STOP", "RESTART", "ERROR", "WARNING"]
        if event_type_upper not in valid_types:
            return {
                "error": "Invalid event type",
                "hint": f"Event type must be one of {valid_types}. Got '{event_type}'."
            }
        filtered = [log for log in filtered if log.event_type == event_type_upper]

    # Sort newest first
    filtered.sort(key=lambda x: x.timestamp, reverse=True)

    # Build summary
    summary = {
        "total_events": len(filtered),
        "errors": sum(1 for log in filtered if log.severity == "ERROR"),
        "warnings": sum(1 for log in filtered if log.severity == "WARNING"),
        "restarts": sum(1 for log in filtered if log.event_type == "RESTART")
    }

    # Build log entries
    entries = []
    for log in filtered:
        entries.append({
            "log_id": log.log_id,
            "event_type": log.event_type,
            "timestamp": log.timestamp,
            "initiated_by": log.initiated_by,
            "message": log.message,
            "severity": log.severity
        })

    return {
        "vm_id": vm.vm_id,
        "vm_name": vm.name,
        "hours_queried": hours,
        "event_type_filter": event_type,
        "summary": summary,
        "logs": entries
    }


def get_recent_events(
    project_id: str,
    hours: int = 24,
    event_type: str = None,
    severity: str = None
) -> dict:
    """
    Get recent events across all VMs in a project.

    Cross-VM query sorted newest first. Useful for answering
    "what happened in this project today?" or "any errors in the last hour?"

    Args:
        project_id: Full or partial project ID or name
        hours: Number of hours to look back (1-168, default: 24)
        event_type: Optional filter ("START", "STOP", "RESTART", "ERROR")
        severity: Optional filter ("INFO", "WARNING", "ERROR")
    """
    try:
        project = resolve_project_id(project_id)
    except ValueError as e:
        return {"error": "Ambiguous project ID", "message": str(e)}

    if not project:
        return {
            "error": "Project not found",
            "hint": f"No project matches '{project_id}'. Call tool_list_projects first to get valid project IDs."
        }

    # Validate hours
    hours = max(1, min(168, hours))
    cutoff = ANCHOR_TIME - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Validate event_type
    if event_type:
        event_type_upper = event_type.upper()
        valid_types = ["START", "STOP", "RESTART", "ERROR", "WARNING"]
        if event_type_upper not in valid_types:
            return {
                "error": "Invalid event type",
                "hint": f"Event type must be one of {valid_types}."
            }
    else:
        event_type_upper = None

    # Validate severity
    if severity:
        severity_upper = severity.upper()
        valid_severities = ["INFO", "WARNING", "ERROR"]
        if severity_upper not in valid_severities:
            return {
                "error": "Invalid severity",
                "hint": f"Severity must be one of {valid_severities}."
            }
    else:
        severity_upper = None

    # Collect logs from all VMs in project
    vms = VMS.get(project.project_id, [])
    all_logs = []

    for vm in vms:
        vm_logs = LOGS.get(vm.vm_id, [])
        for log in vm_logs:
            # Time filter
            if log.timestamp < cutoff_str:
                continue
            # Event type filter
            if event_type_upper and log.event_type != event_type_upper:
                continue
            # Severity filter
            if severity_upper and log.severity != severity_upper:
                continue

            all_logs.append({
                "log_id": log.log_id,
                "vm_id": vm.vm_id,
                "vm_name": vm.name,
                "zone": vm.zone,
                "event_type": log.event_type,
                "timestamp": log.timestamp,
                "initiated_by": log.initiated_by,
                "message": log.message,
                "severity": log.severity
            })

    # Sort newest first
    all_logs.sort(key=lambda x: x["timestamp"], reverse=True)

    # Build summary
    summary = {
        "total_events": len(all_logs),
        "errors": sum(1 for log in all_logs if log["severity"] == "ERROR"),
        "warnings": sum(1 for log in all_logs if log["severity"] == "WARNING"),
        "starts": sum(1 for log in all_logs if log["event_type"] == "START"),
        "stops": sum(1 for log in all_logs if log["event_type"] == "STOP"),
        "restarts": sum(1 for log in all_logs if log["event_type"] == "RESTART"),
        "vms_affected": len(set(log["vm_id"] for log in all_logs))
    }

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "hours_queried": hours,
        "filters": {
            "event_type": event_type,
            "severity": severity
        },
        "summary": summary,
        "events": all_logs
    }
