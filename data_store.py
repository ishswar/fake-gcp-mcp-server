"""
GCP Compute MCP Server - Data Store

Singleton in-memory store populated once at import time.
Provides lookup functions and indexes for O(1) access.
"""

from data_generator import generate_all_data, Project, Zone, VM, User, LogEntry

# Populate all data at import time
_data = generate_all_data()

# Export data collections
PROJECTS: list[Project] = _data["projects"]
ZONES: dict[str, list[Zone]] = _data["zones"]  # project_id -> list[Zone]
VMS: dict[str, list[VM]] = _data["vms"]  # project_id -> list[VM]
USERS: dict[str, list[User]] = _data["users"]  # project_id -> list[User]
PERFORMANCE: dict[str, dict] = _data["performance"]  # vm_id -> {"cpu": [...], "memory": [...], "disk": [...]}
LOGS: dict[str, list[LogEntry]] = _data["logs"]  # vm_id -> list[LogEntry]

# Build lookup indexes for O(1) access
PROJECT_BY_ID: dict[str, Project] = {p.project_id: p for p in PROJECTS}
VM_BY_ID: dict[str, VM] = {vm.vm_id: vm for vms in VMS.values() for vm in vms}

# Also index VMs by name for search
VM_BY_NAME: dict[str, VM] = {vm.name: vm for vms in VMS.values() for vm in vms}


def resolve_project_id(partial: str) -> Project | None:
    """
    Case-insensitive partial match on project_id or project name.

    Returns:
        Project if exactly one match found

    Raises:
        ValueError if multiple matches (ambiguous)

    Returns None if no matches.
    """
    if not partial:
        return None

    partial = partial.lower().strip()

    # First try exact match
    for p in PROJECTS:
        if p.project_id.lower() == partial:
            return p

    # Then try partial match
    matches = [p for p in PROJECTS
               if partial in p.project_id.lower() or partial in p.name.lower()]

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous project '{partial}'. Matches: {[p.project_id for p in matches]}")
    return None


def get_vm_by_id(vm_id: str) -> VM | None:
    """Get VM by exact ID."""
    return VM_BY_ID.get(vm_id)


def get_vms_for_project(project_id: str) -> list[VM]:
    """Get all VMs for a project."""
    return VMS.get(project_id, [])


def get_zones_for_project(project_id: str) -> list[Zone]:
    """Get all zones for a project."""
    return ZONES.get(project_id, [])


def get_users_for_project(project_id: str) -> list[User]:
    """Get all users for a project."""
    return USERS.get(project_id, [])


def get_performance_for_vm(vm_id: str) -> dict | None:
    """Get performance data for a VM."""
    return PERFORMANCE.get(vm_id)


def get_logs_for_vm(vm_id: str) -> list[LogEntry]:
    """Get logs for a VM."""
    return LOGS.get(vm_id, [])


def get_all_project_ids() -> list[str]:
    """Get list of all project IDs."""
    return [p.project_id for p in PROJECTS]


def count_vms_by_status(project_id: str) -> dict[str, int]:
    """Count VMs by status for a project."""
    vms = get_vms_for_project(project_id)
    counts = {"RUNNING": 0, "STOPPED": 0, "TERMINATED": 0}
    for vm in vms:
        counts[vm.status] = counts.get(vm.status, 0) + 1
    return counts


def get_all_vms() -> list[VM]:
    """Get all VMs across all projects."""
    all_vms = []
    for vms in VMS.values():
        all_vms.extend(vms)
    return all_vms


if __name__ == "__main__":
    # Test data store
    print(f"Loaded {len(PROJECTS)} projects")
    print(f"Loaded {len(VM_BY_ID)} VMs total")

    # Test resolve_project_id
    p = resolve_project_id("alpha")
    print(f"\nResolved 'alpha' to: {p.project_id if p else None}")

    p = resolve_project_id("proj-beta-3m9p")
    print(f"Resolved exact ID to: {p.project_id if p else None}")

    # Test ambiguous
    try:
        resolve_project_id("proj")
    except ValueError as e:
        print(f"Ambiguous match error: {e}")

    # Test counts
    counts = count_vms_by_status("proj-alpha-7x2k")
    print(f"\nVM counts for proj-alpha-7x2k: {counts}")
