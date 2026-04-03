"""
GCP Compute MCP Server - Project Tools

Tools for listing and querying GCP projects.
"""

from data_store import (
    PROJECTS, PROJECT_BY_ID, VMS, USERS, ZONES,
    resolve_project_id, count_vms_by_status
)


def list_projects() -> list[dict]:
    """
    List all GCP projects in this environment.

    Returns summary info for each project: project_id, project_number, name,
    labels, zone_count, vm_count, running_count, owner_email.
    """
    results = []

    for project in PROJECTS:
        vms = VMS.get(project.project_id, [])
        running_count = sum(1 for vm in vms if vm.status == "RUNNING")

        results.append({
            "project_id": project.project_id,
            "project_number": project.project_number,
            "name": project.name,
            "labels": project.labels,
            "zone_count": len(project.zones),
            "vm_count": len(vms),
            "running_count": running_count,
            "owner_email": project.owner_email
        })

    return results


def get_project(project_id: str) -> dict:
    """
    Get detailed information about a specific GCP project.

    Supports partial matching on project_id or project name.
    Returns full project details including zones, user summary, and VM status breakdown.

    Args:
        project_id: Full or partial project ID or name (e.g., "alpha" matches "proj-alpha-7x2k")
    """
    try:
        project = resolve_project_id(project_id)
    except ValueError as e:
        # Ambiguous match
        return {"error": "Ambiguous project ID", "message": str(e)}

    if not project:
        # No match - provide suggestions
        suggestions = [p.project_id for p in PROJECTS]
        return {
            "error": "Project not found",
            "hint": f"No project matches '{project_id}'. Available projects: {suggestions}"
        }

    # Get related data
    vms = VMS.get(project.project_id, [])
    users = USERS.get(project.project_id, [])
    zones = ZONES.get(project.project_id, [])

    # Count VMs by status
    status_counts = count_vms_by_status(project.project_id)

    # Count users by role
    role_counts = {}
    for user in users:
        role_counts[user.role] = role_counts.get(user.role, 0) + 1

    return {
        "project_id": project.project_id,
        "project_number": project.project_number,
        "name": project.name,
        "billing_account": project.billing_account,
        "owner_email": project.owner_email,
        "created_at": project.created_at,
        "labels": project.labels,
        "zones": [z.zone_id for z in zones],
        "zone_count": len(zones),
        "users_summary": {
            "total": len(users),
            "by_role": role_counts
        },
        "vm_summary": {
            "total": len(vms),
            "running": status_counts.get("RUNNING", 0),
            "stopped": status_counts.get("STOPPED", 0),
            "terminated": status_counts.get("TERMINATED", 0)
        }
    }


def list_users(project_id: str) -> dict:
    """
    List all IAM users for a GCP project.

    Returns user details including email, role, and count of VMs they own.

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

    users = USERS.get(project.project_id, [])
    vms = VMS.get(project.project_id, [])

    # Count VMs per owner
    vm_counts = {}
    for vm in vms:
        vm_counts[vm.owner_email] = vm_counts.get(vm.owner_email, 0) + 1

    results = []
    for user in users:
        results.append({
            "user_id": user.user_id,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "joined_at": user.joined_at,
            "vms_owned": vm_counts.get(user.email, 0)
        })

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "user_count": len(results),
        "users": results
    }
