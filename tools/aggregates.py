"""
GCP Compute MCP Server - Aggregate Tools

Tools for project health and high-level metrics queries.
"""

from datetime import datetime, timedelta
from data_store import (
    VMS, ZONES, PERFORMANCE, LOGS,
    resolve_project_id, count_vms_by_status
)

# Anchor time for queries
ANCHOR_TIME = datetime(2026, 3, 10, 12, 0, 0)


def get_project_health(project_id: str) -> dict:
    """
    Get project health status at a glance.

    Returns VM summary, zone breakdown, alerts (high CPU, errors),
    and recently stopped VMs. This is the primary "status at a glance" tool.

    Args:
        project_id: Full or partial project ID or name
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

    vms = VMS.get(project.project_id, [])
    zones = ZONES.get(project.project_id, [])

    # VM status counts
    status_counts = count_vms_by_status(project.project_id)

    # Zone breakdown
    zone_breakdown = []
    for zone in zones:
        zone_vms = [vm for vm in vms if vm.zone == zone.zone_id]
        zone_breakdown.append({
            "zone": zone.zone_id,
            "running": sum(1 for vm in zone_vms if vm.status == "RUNNING"),
            "stopped": sum(1 for vm in zone_vms if vm.status == "STOPPED"),
            "terminated": sum(1 for vm in zone_vms if vm.status == "TERMINATED")
        })

    # Alerts: high CPU and error logs
    alerts = []
    high_cpu_count = 0
    error_count = 0

    cutoff_24h = ANCHOR_TIME - timedelta(hours=24)
    cutoff_str = cutoff_24h.strftime("%Y-%m-%dT%H:%M:%SZ")

    for vm in vms:
        # Check CPU for running VMs
        if vm.status == "RUNNING":
            perf = PERFORMANCE.get(vm.vm_id)
            if perf and perf["cpu"]:
                last_cpu = perf["cpu"][-1]
                if last_cpu.value is not None and last_cpu.value > 80:
                    high_cpu_count += 1
                    alerts.append({
                        "type": "HIGH_CPU",
                        "vm_id": vm.vm_id,
                        "vm_name": vm.name,
                        "zone": vm.zone,
                        "value": round(last_cpu.value, 1)
                    })

        # Check for ERROR logs in last 24h
        vm_logs = LOGS.get(vm.vm_id, [])
        for log in vm_logs:
            if log.severity == "ERROR" and log.timestamp >= cutoff_str:
                error_count += 1
                alerts.append({
                    "type": "ERROR_LOG",
                    "vm_id": vm.vm_id,
                    "vm_name": vm.name,
                    "zone": vm.zone,
                    "message": log.message,
                    "timestamp": log.timestamp
                })

    # Recently stopped VMs (stopped in last 24h)
    recent_stops = []
    for vm in vms:
        if vm.status == "STOPPED":
            vm_logs = LOGS.get(vm.vm_id, [])
            for log in vm_logs:
                if log.event_type == "STOP" and log.timestamp >= cutoff_str:
                    recent_stops.append({
                        "vm_id": vm.vm_id,
                        "vm_name": vm.name,
                        "zone": vm.zone,
                        "stopped_at": log.timestamp
                    })
                    break

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "vm_summary": {
            "total": len(vms),
            "running": status_counts.get("RUNNING", 0),
            "stopped": status_counts.get("STOPPED", 0),
            "terminated": status_counts.get("TERMINATED", 0)
        },
        "zone_breakdown": zone_breakdown,
        "alerts": alerts,
        "high_cpu_count": high_cpu_count,
        "error_count": error_count,
        "recent_stops": recent_stops
    }


def get_high_utilization_vms(
    project_id: str,
    metric: str = "cpu",
    threshold: float = 80.0
) -> dict:
    """
    Get VMs exceeding a utilization threshold.

    Returns VMs where the last data point for the specified metric
    exceeds the threshold, sorted by value descending.

    Args:
        project_id: Full or partial project ID or name
        metric: "cpu", "memory", or "disk" (default: "cpu")
        threshold: Utilization threshold percentage (default: 80.0)
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

    metric = metric.lower()
    if metric not in ["cpu", "memory", "disk"]:
        return {
            "error": "Invalid metric",
            "hint": f"Metric must be 'cpu', 'memory', or 'disk'. Got '{metric}'."
        }

    threshold = max(0, min(100, threshold))

    vms = VMS.get(project.project_id, [])
    results = []

    for vm in vms:
        # Only check running VMs
        if vm.status != "RUNNING":
            continue

        perf = PERFORMANCE.get(vm.vm_id)
        if not perf or not perf[metric]:
            continue

        data_points = perf[metric]
        last_point = data_points[-1]

        if last_point.value is None:
            continue

        current_value = last_point.value
        if current_value <= threshold:
            continue

        # Calculate 24h stats
        values = [dp.value for dp in data_points if dp.value is not None]
        avg_24h = sum(values) / len(values) if values else 0
        max_24h = max(values) if values else 0

        results.append({
            "vm_id": vm.vm_id,
            "name": vm.name,
            "zone": vm.zone,
            "machine_type": vm.machine_type,
            "current_value": round(current_value, 2),
            "avg_24h": round(avg_24h, 2),
            "max_24h": round(max_24h, 2)
        })

    # Sort by current value descending
    results.sort(key=lambda x: x["current_value"], reverse=True)

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "metric": metric,
        "threshold": threshold,
        "count": len(results),
        "vms": results
    }
