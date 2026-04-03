"""
GCP Compute MCP Server - Tools Module

All MCP tools for querying fake GCP Compute Engine data.
"""

from tools.projects import list_projects, get_project, list_users
from tools.zones import list_zones, get_zone_summary
from tools.vms import list_vms, get_vm, search_vms
from tools.performance import get_vm_performance
from tools.logs import get_vm_logs, get_recent_events
from tools.aggregates import get_project_health, get_high_utilization_vms

__all__ = [
    "list_projects",
    "get_project",
    "list_users",
    "list_zones",
    "get_zone_summary",
    "list_vms",
    "get_vm",
    "search_vms",
    "get_vm_performance",
    "get_vm_logs",
    "get_recent_events",
    "get_project_health",
    "get_high_utilization_vms",
]
