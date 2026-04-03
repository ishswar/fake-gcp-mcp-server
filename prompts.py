"""
GCP Compute MCP Server - Prompts

MCP prompts that return pre-composed, data-rich messages.
"""

from datetime import datetime
from data_store import (
    VMS, ZONES, PERFORMANCE, LOGS,
    resolve_project_id, count_vms_by_status
)
from datetime import timedelta

# Anchor time
ANCHOR_TIME = datetime(2026, 3, 10, 12, 0, 0)
ANCHOR_STR = ANCHOR_TIME.strftime("%Y-%m-%d %H:%M:%S UTC")


def vm_fleet_status(project_id: str, zone: str = "") -> str:
    """
    Generate a fleet status report for a project.

    Provides a formatted overview of VM fleet health including
    zone breakdown, alerts, and suggestions for investigation.

    Args:
        project_id: Full or partial project ID
        zone: Optional zone or region prefix filter
    """
    try:
        project = resolve_project_id(project_id)
    except ValueError as e:
        return f"Error: {e}"

    if not project:
        return f"Error: Project '{project_id}' not found."

    vms = VMS.get(project.project_id, [])
    zones = ZONES.get(project.project_id, [])

    # Filter by zone if specified
    if zone:
        zone_lower = zone.lower()
        vms = [vm for vm in vms if zone_lower in vm.zone.lower()]
        zones = [z for z in zones if zone_lower in z.zone_id.lower()]

    # Count statuses
    running = sum(1 for vm in vms if vm.status == "RUNNING")
    stopped = sum(1 for vm in vms if vm.status == "STOPPED")
    terminated = sum(1 for vm in vms if vm.status == "TERMINATED")
    total = len(vms)

    # Calculate percentages
    running_pct = round(100 * running / total, 0) if total > 0 else 0
    stopped_pct = round(100 * stopped / total, 0) if total > 0 else 0
    terminated_pct = round(100 * terminated / total, 0) if total > 0 else 0

    # Build zone breakdown
    zone_lines = []
    for z in zones:
        zone_vms = [vm for vm in vms if vm.zone == z.zone_id]
        z_running = sum(1 for vm in zone_vms if vm.status == "RUNNING")
        z_stopped = sum(1 for vm in zone_vms if vm.status == "STOPPED")
        z_terminated = sum(1 for vm in zone_vms if vm.status == "TERMINATED")
        zone_lines.append(
            f"{z.zone_id:<20} -> {len(zone_vms):>2} VMs  | "
            f"{z_running} RUNNING | {z_stopped} STOPPED | {z_terminated} TERMINATED"
        )

    # Collect alerts
    alerts = []
    cutoff_24h = ANCHOR_TIME - timedelta(hours=24)
    cutoff_str = cutoff_24h.strftime("%Y-%m-%dT%H:%M:%SZ")

    for vm in vms:
        if vm.status == "RUNNING":
            perf = PERFORMANCE.get(vm.vm_id)
            if perf and perf["cpu"]:
                last_cpu = perf["cpu"][-1]
                if last_cpu.value is not None and last_cpu.value > 80:
                    alerts.append(
                        f"[HIGH CPU] {vm.vm_id} ({vm.name}) in {vm.zone} -> {last_cpu.value:.1f}% CPU"
                    )

        vm_logs = LOGS.get(vm.vm_id, [])
        for log in vm_logs:
            if log.severity == "ERROR" and log.timestamp >= cutoff_str:
                time_ago = _time_ago(log.timestamp)
                alerts.append(
                    f"[ERROR LOG] {vm.vm_id} ({vm.name}) in {vm.zone} -> \"{log.message}\" ({time_ago})"
                )

    # Build report
    lines = [
        "GCP Fleet Status Report",
        "=======================",
        f"Project: {project.name} ({project.project_id})",
        f"Generated: {ANCHOR_STR}",
    ]

    if zone:
        lines.append(f"Zone Filter: {zone}")

    lines.extend([
        "",
        "FLEET OVERVIEW",
        "--------------",
        f"Total VMs : {total}",
        f"Running   : {running} ({running_pct:.0f}%)",
        f"Stopped   : {stopped} ({stopped_pct:.0f}%)",
        f"Terminated: {terminated} ({terminated_pct:.0f}%)",
        "",
        "ZONE BREAKDOWN",
        "--------------",
    ])

    lines.extend(zone_lines)

    if alerts:
        lines.extend([
            "",
            f"ALERTS ({len(alerts)})",
            "--------------",
        ])
        lines.extend(alerts)
    else:
        lines.extend([
            "",
            "ALERTS",
            "--------------",
            "No alerts - all systems normal."
        ])

    lines.extend([
        "",
        "What would you like to investigate? You can ask me to:",
        "- Show performance graphs for any VM",
        "- List all stopped VMs and when they were stopped",
        "- Find VMs with high memory or disk usage",
        "- Show recent error logs across the fleet",
    ])

    return "\n".join(lines)


def vm_health_report(
    project_id: str,
    cpu_threshold: float = 80.0,
    memory_threshold: float = 85.0
) -> str:
    """
    Generate a health report identifying VMs that need attention.

    Finds VMs exceeding CPU or memory thresholds, plus VMs with recent errors.

    Args:
        project_id: Full or partial project ID
        cpu_threshold: CPU percentage threshold (default: 80.0)
        memory_threshold: Memory percentage threshold (default: 85.0)
    """
    try:
        project = resolve_project_id(project_id)
    except ValueError as e:
        return f"Error: {e}"

    if not project:
        return f"Error: Project '{project_id}' not found."

    vms = VMS.get(project.project_id, [])

    cutoff_24h = ANCHOR_TIME - timedelta(hours=24)
    cutoff_str = cutoff_24h.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Find VMs needing attention
    attention_needed = []

    for vm in vms:
        if vm.status != "RUNNING":
            continue

        perf = PERFORMANCE.get(vm.vm_id)
        if not perf:
            continue

        cpu_val = None
        mem_val = None
        flags = []

        if perf["cpu"]:
            last_cpu = perf["cpu"][-1]
            if last_cpu.value is not None:
                cpu_val = last_cpu.value
                if cpu_val > cpu_threshold:
                    flags.append("HIGH CPU")

        if perf["memory"]:
            last_mem = perf["memory"][-1]
            if last_mem.value is not None:
                mem_val = last_mem.value
                if mem_val > memory_threshold:
                    flags.append("HIGH MEMORY")

        # Check for errors
        vm_logs = LOGS.get(vm.vm_id, [])
        for log in vm_logs:
            if log.severity == "ERROR" and log.timestamp >= cutoff_str:
                flags.append("ERROR LOG")
                break

        if flags:
            attention_needed.append({
                "vm_id": vm.vm_id,
                "name": vm.name,
                "zone": vm.zone,
                "cpu": cpu_val,
                "memory": mem_val,
                "flags": flags
            })

    # Get error events for the report
    error_events = []
    for vm in vms:
        vm_logs = LOGS.get(vm.vm_id, [])
        for log in vm_logs:
            if log.severity == "ERROR" and log.timestamp >= cutoff_str:
                error_events.append({
                    "vm_id": vm.vm_id,
                    "timestamp": log.timestamp,
                    "message": log.message
                })

    # Count normal VMs
    normal_count = len([vm for vm in vms if vm.status == "RUNNING"]) - len(attention_needed)

    # Build report
    lines = [
        "GCP VM Health Report",
        "====================",
        f"Project : {project.name} ({project.project_id})",
        f"Period  : Last 24 hours",
        f"Thresholds: CPU > {cpu_threshold}% | Memory > {memory_threshold}%",
    ]

    if attention_needed:
        lines.extend([
            "",
            f"ATTENTION REQUIRED ({len(attention_needed)} VMs)",
            "-" * 30,
        ])

        for item in attention_needed:
            cpu_str = f"{item['cpu']:.1f}%" if item['cpu'] else "N/A"
            mem_str = f"{item['memory']:.1f}%" if item['memory'] else "N/A"
            flag_str = " + ".join(item['flags'])
            lines.append(
                f"{item['vm_id']}  {item['name']:<25}  {item['zone']:<18}  "
                f"CPU: {cpu_str:>6}  MEM: {mem_str:>6}  {flag_str}"
            )
    else:
        lines.extend([
            "",
            "ATTENTION REQUIRED",
            "-" * 30,
            "None - all VMs within thresholds.",
        ])

    lines.extend([
        "",
        f"ALL SYSTEMS NORMAL ({normal_count} VMs)",
        "-" * 30,
        f"Remaining {normal_count} running VMs are within thresholds and have no recent errors.",
    ])

    if error_events:
        lines.extend([
            "",
            "RECENT ERROR EVENTS",
            "-" * 30,
        ])
        for event in sorted(error_events, key=lambda x: x["timestamp"], reverse=True):
            lines.append(f"{event['vm_id']}  {event['timestamp']}  ERROR  \"{event['message']}\"")

    return "\n".join(lines)


def _time_ago(timestamp: str) -> str:
    """Convert timestamp to human-readable time ago string."""
    ts = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    delta = ANCHOR_TIME - ts

    if delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes}m ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(delta.total_seconds() / 86400)
        return f"{days}d ago"


# Prompt registry for server.py
PROMPTS = {
    "vm_fleet_status": {
        "fn": vm_fleet_status,
        "description": "Generate a formatted fleet status report for a GCP project. Shows VM overview, zone breakdown, and alerts.",
        "args": [
            {"name": "project_id", "description": "Full or partial project ID", "required": True},
            {"name": "zone", "description": "Optional zone or region prefix filter", "required": False}
        ]
    },
    "vm_health_report": {
        "fn": vm_health_report,
        "description": "Generate a health report identifying VMs that need attention based on CPU/memory thresholds and errors.",
        "args": [
            {"name": "project_id", "description": "Full or partial project ID", "required": True},
            {"name": "cpu_threshold", "description": "CPU percentage threshold (default: 80.0)", "required": False},
            {"name": "memory_threshold", "description": "Memory percentage threshold (default: 85.0)", "required": False}
        ]
    }
}
