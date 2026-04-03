"""
GCP Compute MCP Server - Zone Tools

Tools for listing and querying GCP zones.
"""

from data_store import (
    ZONES, VMS, PERFORMANCE,
    resolve_project_id
)


def list_zones(project_id: str) -> dict:
    """
    List all zones for a GCP project with VM counts.

    Returns zone details including region, total VMs, and breakdown by status.

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

    zones = ZONES.get(project.project_id, [])
    vms = VMS.get(project.project_id, [])

    # Count VMs by zone and status
    zone_stats = {}
    for vm in vms:
        if vm.zone not in zone_stats:
            zone_stats[vm.zone] = {"running": 0, "stopped": 0, "terminated": 0}
        if vm.status == "RUNNING":
            zone_stats[vm.zone]["running"] += 1
        elif vm.status == "STOPPED":
            zone_stats[vm.zone]["stopped"] += 1
        else:
            zone_stats[vm.zone]["terminated"] += 1

    results = []
    for zone in zones:
        stats = zone_stats.get(zone.zone_id, {"running": 0, "stopped": 0, "terminated": 0})
        total = stats["running"] + stats["stopped"] + stats["terminated"]
        results.append({
            "zone_id": zone.zone_id,
            "region": zone.region,
            "vm_count": total,
            "running_count": stats["running"],
            "stopped_count": stats["stopped"],
            "terminated_count": stats["terminated"]
        })

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "zone_count": len(results),
        "zones": results
    }


def get_zone_summary(project_id: str, zone: str) -> dict:
    """
    Get detailed summary of a specific zone including all VMs.

    Returns zone info with list of VMs and aggregate metrics.

    Args:
        project_id: Full or partial project ID or name
        zone: Zone ID (e.g., "us-west1-a")
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

    zones = ZONES.get(project.project_id, [])
    zone_obj = None
    for z in zones:
        if z.zone_id == zone:
            zone_obj = z
            break

    if not zone_obj:
        available_zones = [z.zone_id for z in zones]
        return {
            "error": "Zone not found",
            "hint": f"Zone '{zone}' not in project. Available zones: {available_zones}"
        }

    # Get VMs in this zone
    all_vms = VMS.get(project.project_id, [])
    zone_vms = [vm for vm in all_vms if vm.zone == zone]

    # Calculate aggregate metrics (last data point for each running VM)
    cpu_values = []
    high_cpu_vms = []

    for vm in zone_vms:
        if vm.status == "RUNNING":
            perf = PERFORMANCE.get(vm.vm_id)
            if perf and perf["cpu"]:
                last_cpu = perf["cpu"][-1]
                if last_cpu.value is not None:
                    cpu_values.append(last_cpu.value)
                    if last_cpu.value > 80:
                        high_cpu_vms.append({
                            "vm_id": vm.vm_id,
                            "name": vm.name,
                            "cpu": last_cpu.value
                        })

    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0

    # Build VM list (summary only)
    vm_list = []
    for vm in zone_vms:
        vm_list.append({
            "vm_id": vm.vm_id,
            "name": vm.name,
            "status": vm.status,
            "machine_type": vm.machine_type,
            "owner_email": vm.owner_email
        })

    return {
        "project_id": project.project_id,
        "zone_id": zone_obj.zone_id,
        "region": zone_obj.region,
        "vm_count": len(zone_vms),
        "running_count": sum(1 for vm in zone_vms if vm.status == "RUNNING"),
        "stopped_count": sum(1 for vm in zone_vms if vm.status == "STOPPED"),
        "terminated_count": sum(1 for vm in zone_vms if vm.status == "TERMINATED"),
        "average_cpu_percent": round(avg_cpu, 2),
        "high_cpu_count": len(high_cpu_vms),
        "high_cpu_vms": high_cpu_vms,
        "vms": vm_list
    }
