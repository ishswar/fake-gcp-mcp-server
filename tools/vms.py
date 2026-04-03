"""
GCP Compute MCP Server - VM Tools

Tools for listing, querying, and searching VMs.
"""

from data_store import (
    VMS, VM_BY_ID, PERFORMANCE, LOGS,
    resolve_project_id
)
from datetime import datetime, timedelta


def list_vms(
    project_id: str,
    zone: str = None,
    status: str = None,
    owner_email: str = None
) -> dict:
    """
    List VMs in a project with optional filters.

    All filter arguments are optional. Supports partial zone matching
    (e.g., "us-west" matches all us-west zones).

    Args:
        project_id: Full or partial project ID or name
        zone: Optional zone filter (supports partial match like "us-west")
        status: Optional status filter ("RUNNING", "STOPPED", "TERMINATED")
        owner_email: Optional owner email filter
    """
    try:
        project = resolve_project_id(project_id)
    except ValueError as e:
        return {"error": "Ambiguous project ID", "message": str(e)}

    if not project:
        return {
            "error": "Project not found",
            "hint": f"No project matches '{project_id}'. Call tool_list_projects first to get valid project IDs, then retry with the correct project_id."
        }

    vms = VMS.get(project.project_id, [])

    # Apply filters
    filtered = vms
    if zone:
        zone_lower = zone.lower()
        filtered = [vm for vm in filtered if zone_lower in vm.zone.lower()]
    if status:
        status_upper = status.upper()
        filtered = [vm for vm in filtered if vm.status == status_upper]
    if owner_email:
        email_lower = owner_email.lower()
        filtered = [vm for vm in filtered if email_lower in vm.owner_email.lower()]

    # Build results
    results = []
    for vm in filtered:
        results.append({
            "vm_id": vm.vm_id,
            "name": vm.name,
            "zone": vm.zone,
            "machine_type": vm.machine_type,
            "status": vm.status,
            "internal_ip": vm.internal_ip,
            "external_ip": vm.external_ip,
            "tags": vm.tags,
            "owner_email": vm.owner_email
        })

    return {
        "project_id": project.project_id,
        "filters_applied": {
            "zone": zone,
            "status": status,
            "owner_email": owner_email
        },
        "total_count": len(results),
        "vms": results
    }


def get_vm(vm_id: str) -> dict:
    """
    Get full details of a specific VM by ID.

    Returns all static fields plus current metrics snapshot
    and recent log event count.

    Args:
        vm_id: The VM ID (e.g., "vm-a1b2c3d4")
    """
    vm = VM_BY_ID.get(vm_id)

    if not vm:
        return {
            "error": "VM not found",
            "hint": f"No VM with ID '{vm_id}'. Call tool_list_vms with a valid project_id to find VM IDs, or call tool_search_vms to search by name."
        }

    # Get current metrics (last data point)
    metrics_snapshot = {"cpu": None, "memory": None, "disk": None}
    perf = PERFORMANCE.get(vm_id)
    if perf:
        for metric in ["cpu", "memory", "disk"]:
            if perf[metric]:
                last_point = perf[metric][-1]
                metrics_snapshot[metric] = last_point.value

    # Count recent log events (last 24 hours)
    logs = LOGS.get(vm_id, [])
    cutoff = datetime(2026, 3, 10, 12, 0, 0) - timedelta(hours=24)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    recent_logs = [log for log in logs if log.timestamp >= cutoff_str]

    return {
        "vm_id": vm.vm_id,
        "instance_id": vm.instance_id,
        "name": vm.name,
        "project_id": vm.project_id,
        "zone": vm.zone,
        "machine_type": vm.machine_type,
        "vcpus": vm.vcpus,
        "memory_gb": vm.memory_gb,
        "status": vm.status,
        "internal_ip": vm.internal_ip,
        "external_ip": vm.external_ip,
        "tags": vm.tags,
        "labels": vm.labels,
        "boot_disk_gb": vm.boot_disk_gb,
        "os_image": vm.os_image,
        "owner_email": vm.owner_email,
        "created_at": vm.created_at,
        "last_start_timestamp": vm.last_start_timestamp,
        "self_link": vm.self_link,
        "current_metrics": metrics_snapshot,
        "recent_log_count": len(recent_logs)
    }


def search_vms(project_id: str, query: str) -> dict:
    """
    Free-text search across VMs.

    Searches name, tags, labels, machine_type, and owner_email.
    Case-insensitive matching. If project_id is invalid or empty,
    searches across ALL projects automatically.

    Args:
        project_id: Full or partial project ID or name (or empty to search all)
        query: Search query string
    """
    if not query or len(query.strip()) < 2:
        return {
            "error": "Invalid query",
            "hint": "Search query must be at least 2 characters."
        }

    # Try to resolve project, fall back to searching all projects
    project = None
    try:
        project = resolve_project_id(project_id)
    except ValueError:
        pass

    if project:
        vms = VMS.get(project.project_id, [])
    else:
        # Search across ALL projects when project_id is invalid/missing
        vms = [vm for vm_list in VMS.values() for vm in vm_list]
    query_lower = query.lower().strip()

    results = []
    for vm in vms:
        matched_on = None

        # Check name
        if query_lower in vm.name.lower():
            matched_on = f"name:{vm.name}"
        # Check tags
        elif any(query_lower in tag.lower() for tag in vm.tags):
            matching_tag = next(t for t in vm.tags if query_lower in t.lower())
            matched_on = f"tag:{matching_tag}"
        # Check labels
        elif any(query_lower in str(v).lower() for v in vm.labels.values()):
            matching_label = next(
                f"{k}:{v}" for k, v in vm.labels.items()
                if query_lower in str(v).lower()
            )
            matched_on = f"label:{matching_label}"
        # Check machine_type
        elif query_lower in vm.machine_type.lower():
            matched_on = f"machine_type:{vm.machine_type}"
        # Check owner_email
        elif query_lower in vm.owner_email.lower():
            matched_on = f"owner:{vm.owner_email}"

        if matched_on:
            results.append({
                "vm_id": vm.vm_id,
                "name": vm.name,
                "zone": vm.zone,
                "status": vm.status,
                "machine_type": vm.machine_type,
                "matched_on": matched_on
            })

    return {
        "project_id": project.project_id if project else "all",
        "query": query,
        "match_count": len(results),
        "results": results
    }
