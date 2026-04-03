"""
GCP Compute MCP Server - Resources

MCP resources for static/slow-changing data that LLMs can load into context.
"""

import json
from data_store import PROJECTS, ZONES, resolve_project_id
from data_generator import MACHINE_TYPES, ZONE_POOL


def get_all_projects_resource() -> str:
    """
    Complete list of all GCP projects in this environment.

    Read this first to know available project IDs before querying VMs.
    """
    projects = []
    for p in PROJECTS:
        projects.append({
            "project_id": p.project_id,
            "name": p.name,
            "zone_count": len(p.zones),
            "labels": p.labels
        })
    return json.dumps(projects, indent=2)


def get_regions_resource() -> str:
    """
    All GCP zones used in this environment with region groupings.
    """
    regions = {}
    for zone in ZONE_POOL:
        region = "-".join(zone.split("-")[:-1])
        if region not in regions:
            regions[region] = []
        regions[region].append(zone)
    return json.dumps(regions, indent=2)


def get_machine_types_resource() -> str:
    """
    GCP machine type catalog with vCPU and memory specs.
    """
    return json.dumps(MACHINE_TYPES, indent=2)


def get_project_zones_resource(project_id: str) -> str:
    """
    Zone assignments for a specific project.

    Args:
        project_id: Exact project ID (no partial matching for resources)
    """
    try:
        project = resolve_project_id(project_id)
    except ValueError:
        return json.dumps({"error": f"Ambiguous project ID: {project_id}"})

    if not project:
        return json.dumps({"error": f"Project not found: {project_id}"})

    zones = ZONES.get(project.project_id, [])
    return json.dumps({
        "project_id": project.project_id,
        "zones": [z.zone_id for z in zones]
    }, indent=2)


# Resource registry for registration in server.py
RESOURCES = {
    "gcp://projects": {
        "fn": get_all_projects_resource,
        "description": "Complete list of all GCP projects in this environment. Read this first to know available project IDs before querying VMs."
    },
    "gcp://regions": {
        "fn": get_regions_resource,
        "description": "All GCP zones used in this environment with region groupings."
    },
    "gcp://machine-types": {
        "fn": get_machine_types_resource,
        "description": "GCP machine type catalog with vCPU and memory specs."
    }
}

# Template resource with parameter
PROJECT_ZONES_TEMPLATE = {
    "uri_template": "gcp://projects/{project_id}/zones",
    "fn": get_project_zones_resource,
    "description": "Zone assignments for a specific project. Use exact project_id."
}
