"""
GCP Compute MCP Server - Performance Tools

Tools for querying VM performance metrics (CPU, memory, disk).
Performance data is generated on-the-fly with current timestamps
so charts always show recent data without server restart.
"""

from data_store import VM_BY_ID
from data_generator import generate_performance_data as generate_vm_performance


def get_vm_performance(
    vm_id: str,
    metric: str = "all",
    hours: int = 24
) -> dict:
    """
    Get performance time series data for a VM.

    Returns data in a format suitable for plotting charts.
    Includes summary statistics (avg, min, max, current).
    Data timestamps are relative to current time (always fresh).

    Args:
        vm_id: The VM ID
        metric: "cpu", "memory", "disk", or "all" (default: "all")
        hours: Number of hours of data (1-24, default: 24)
    """
    vm = VM_BY_ID.get(vm_id)
    if not vm:
        return {
            "error": "VM not found",
            "hint": f"No VM with ID '{vm_id}'. Call tool_list_vms with a valid project_id to find VM IDs, or call tool_search_vms to search by name."
        }

    # Generate fresh performance data with current timestamps
    perf = generate_vm_performance(vm)
    if not perf:
        return {
            "error": "No performance data",
            "hint": f"No performance data available for VM '{vm_id}'."
        }

    # Validate and clamp hours
    hours = max(1, min(24, hours))

    # Calculate how many data points to include
    # 288 points = 24 hours at 5-min intervals
    # So N hours = N * 12 points
    points_to_include = hours * 12

    # Determine which metrics to include
    metric = metric.lower()
    if metric not in ["cpu", "memory", "disk", "all"]:
        return {
            "error": "Invalid metric",
            "hint": f"Metric must be 'cpu', 'memory', 'disk', or 'all'. Got '{metric}'."
        }

    metrics_to_fetch = ["cpu", "memory", "disk"] if metric == "all" else [metric]

    # Build response
    metrics_data = {}
    summary = {}

    for m in metrics_to_fetch:
        data_points = perf[m][-points_to_include:]

        # Convert to dict format
        series = [{"timestamp": dp.timestamp, "value": dp.value} for dp in data_points]
        metrics_data[m] = series

        # Calculate summary stats (ignoring None values)
        values = [dp.value for dp in data_points if dp.value is not None]
        if values:
            summary[m] = {
                "avg": round(sum(values) / len(values), 2),
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "current": round(values[-1], 2) if values else None,
                "data_points": len(values),
                "null_points": len(data_points) - len(values)
            }
        else:
            summary[m] = {
                "avg": None,
                "min": None,
                "max": None,
                "current": None,
                "data_points": 0,
                "null_points": len(data_points)
            }

    response = {
        "vm_id": vm.vm_id,
        "vm_name": vm.name,
        "zone": vm.zone,
        "status": vm.status,
        "hours_requested": hours,
        "interval_minutes": 5,
        "metrics": metrics_data,
        "summary": summary
    }

    # Add note for non-running VMs
    if vm.status != "RUNNING":
        response["note"] = f"VM is {vm.status}. Metrics may contain null values for periods when VM was not running."

    return response
