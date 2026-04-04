"""
GCP Compute MCP Server

A fake GCP Compute Engine MCP server for AI agent testing.
Provides 5 projects, 125 VMs, 24-hour performance data, and event logs.
All data is synthetic and deterministic (seed=42).
"""

import logging
import base64
import io
from fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP(
    name="GCP Compute MCP Server",
    instructions=(
        "This server provides access to a GCP Compute Engine environment with "
        "5 projects, 111 VMs, 24-hour performance metrics, and 7-day event logs. "
        "IMPORTANT: Always call tool_list_projects FIRST to discover valid project IDs. "
        "Then call tool_list_vms or tool_search_vms to find VM IDs before calling "
        "tool_generate_chart or tool_get_vm_performance. VM IDs are opaque strings "
        "like 'vm-2a077021', not human names. Do NOT guess project or VM IDs. "
        "When generating charts, always use output_format='png+html' to get both an "
        "interactive Plotly chart and a PNG snapshot."
    )
)


# =============================================================================
# Register Tools
# =============================================================================

from tools.projects import list_projects, get_project, list_users
from tools.zones import list_zones, get_zone_summary
from tools.vms import list_vms, get_vm, search_vms
from tools.performance import get_vm_performance
from tools.logs import get_vm_logs, get_recent_events
from tools.aggregates import get_project_health, get_high_utilization_vms


@mcp.tool(description="List all GCP projects in this environment with summary info.")
async def tool_list_projects(ctx: Context) -> dict:
    """List all GCP projects with summary info including VM counts."""
    logger.info("Listing all projects")
    return {"projects": list_projects()}


@mcp.tool(description="Get detailed information about a specific GCP project. Supports partial matching on project_id or name.")
async def tool_get_project(project_id: str, ctx: Context) -> dict:
    """Get full project details including zones, users, and VM status breakdown."""
    logger.info(f"Getting project: {project_id}")
    return get_project(project_id)


@mcp.tool(description="List all IAM users for a GCP project with their roles and VM ownership counts.")
async def tool_list_users(project_id: str, ctx: Context) -> dict:
    """List users for a project including how many VMs each owns."""
    logger.info(f"Listing users for project: {project_id}")
    return list_users(project_id)


@mcp.tool(description="List all zones for a GCP project with VM counts per zone.")
async def tool_list_zones(project_id: str, ctx: Context) -> dict:
    """List zones with running/stopped/terminated VM counts."""
    logger.info(f"Listing zones for project: {project_id}")
    return list_zones(project_id)


@mcp.tool(description="Get detailed summary of a specific zone including all VMs and aggregate metrics.")
async def tool_get_zone_summary(project_id: str, zone: str, ctx: Context) -> dict:
    """Get zone details with VM list and CPU metrics."""
    logger.info(f"Getting zone summary: {project_id}/{zone}")
    return get_zone_summary(project_id, zone)


@mcp.tool(description="List VMs in a project with optional filters for zone, status, and owner.")
async def tool_list_vms(
    project_id: str,
    zone: str = None,
    status: str = None,
    owner_email: str = None,
    ctx: Context = None
) -> dict:
    """List VMs with optional filtering. Zone filter supports partial match (e.g., 'us-west')."""
    logger.info(f"Listing VMs: project={project_id}, zone={zone}, status={status}, owner={owner_email}")
    return list_vms(project_id, zone, status, owner_email)


@mcp.tool(description="Get full details of a specific VM including current metrics and recent log count.")
async def tool_get_vm(vm_id: str, ctx: Context) -> dict:
    """Get complete VM information with current CPU/memory/disk values."""
    logger.info(f"Getting VM: {vm_id}")
    return get_vm(vm_id)


@mcp.tool(description="Search VMs by name, tags, labels, machine type, or owner email. Requires a valid project_id — call tool_list_projects first if you don't know it.")
async def tool_search_vms(project_id: str, query: str, ctx: Context) -> dict:
    """Free-text search across VM attributes. Returns matching VMs with match reason."""
    logger.info(f"Searching VMs: project={project_id}, query={query}")
    return search_vms(project_id, query)


@mcp.tool(description="Get performance time series data (CPU/memory/disk) for a VM. Returns chart-ready data.")
async def tool_get_vm_performance(
    vm_id: str,
    metric: str = "all",
    hours: int = 24,
    ctx: Context = None
) -> dict:
    """Get 5-minute interval metrics with summary stats. Metric can be 'cpu', 'memory', 'disk', or 'all'."""
    logger.info(f"Getting performance: vm={vm_id}, metric={metric}, hours={hours}")
    return get_vm_performance(vm_id, metric, hours)


@mcp.tool(description="Get event logs for a specific VM (START/STOP/RESTART/ERROR events).")
async def tool_get_vm_logs(
    vm_id: str,
    hours: int = 24,
    event_type: str = None,
    ctx: Context = None
) -> dict:
    """Get VM logs sorted newest first. Max 168 hours (7 days)."""
    logger.info(f"Getting VM logs: vm={vm_id}, hours={hours}, event_type={event_type}")
    return get_vm_logs(vm_id, hours, event_type)


@mcp.tool(description="Get recent events across all VMs in a project. Useful for 'what happened today?' queries.")
async def tool_get_recent_events(
    project_id: str,
    hours: int = 24,
    event_type: str = None,
    severity: str = None,
    ctx: Context = None
) -> dict:
    """Cross-VM event query with optional event_type and severity filters."""
    logger.info(f"Getting recent events: project={project_id}, hours={hours}")
    return get_recent_events(project_id, hours, event_type, severity)


@mcp.tool(description="Get project health status at a glance: VM summary, alerts, zone breakdown, recent stops.")
async def tool_get_project_health(project_id: str, ctx: Context) -> dict:
    """Primary status dashboard tool. Shows high CPU VMs, errors, and recently stopped VMs."""
    logger.info(f"Getting project health: {project_id}")
    return get_project_health(project_id)


@mcp.tool(description="Get VMs exceeding a utilization threshold for CPU, memory, or disk.")
async def tool_get_high_utilization_vms(
    project_id: str,
    metric: str = "cpu",
    threshold: float = 80.0,
    ctx: Context = None
) -> dict:
    """Find VMs with high utilization, sorted by value descending."""
    logger.info(f"Getting high utilization VMs: project={project_id}, metric={metric}, threshold={threshold}")
    return get_high_utilization_vms(project_id, metric, threshold)


@mcp.tool(description="Generate a performance chart for a VM. Always use output_format='png+html' to get both an interactive HTML chart and a PNG snapshot. The vm_id must be the actual VM ID (e.g., 'vm-2a077021'), NOT the VM name — call tool_search_vms first if you only have the name.")
async def tool_generate_chart(
    vm_id: str,
    metric: str = "cpu",
    hours: int = 24,
    output_format: str = "png+html",
    width: int = 700,
    height: int = 400,
    title: str = "",
    ctx: Context = None
) -> dict:
    """Generate a Plotly chart of VM performance metrics."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    logger.info(f"Generating chart: vm={vm_id}, metric={metric}, hours={hours}, format={output_format}")

    try:
        perf_data = get_vm_performance(vm_id, metric, hours)
        if "error" in perf_data:
            return {"error": perf_data["error"]}

        metrics_data = perf_data.get("metrics", {})
        vm_name = perf_data.get("vm_name", vm_id)
        chart_title = title or f"Performance - {vm_name} (last {hours}h)"

        metric_names = list(metrics_data.keys())
        if len(metric_names) > 1:
            fig = make_subplots(rows=1, cols=len(metric_names),
                               subplot_titles=[m.upper() for m in metric_names],
                               shared_xaxes=True)
            for col, m in enumerate(metric_names, 1):
                data_points = metrics_data[m]
                timestamps = [p["timestamp"] for p in data_points]
                values = [p["value"] for p in data_points]
                fig.add_trace(go.Scatter(x=timestamps, y=values, mode='lines',
                                         name=m.upper(), legendgroup=m,
                                         showlegend=(col == len(metric_names))),
                              row=1, col=col)
                fig.update_yaxes(title_text="Usage %", row=1, col=col)
        else:
            fig = go.Figure()
            m = metric_names[0]
            data_points = metrics_data[m]
            timestamps = [p["timestamp"] for p in data_points]
            values = [p["value"] for p in data_points]
            fig.add_trace(go.Scatter(x=timestamps, y=values, mode='lines',
                                     name=vm_name, line=dict(width=2)))
            fig.update_yaxes(title_text="Usage %")

        fig.update_layout(title=chart_title, xaxis_title="Time", height=height,
                          autosize=True, showlegend=True, template="plotly_white")

        result = {
            "vm_name": vm_name, "metric": metric, "hours": hours,
            "title": chart_title, "series": len(metric_names),
            "data_points": len(next(iter(metrics_data.values()), [])),
        }

        if output_format in ("html", "png+html"):
            html_str = fig.to_html(include_plotlyjs="cdn", full_html=True,
                                    config={"responsive": True, "displayModeBar": True})
            result["html_data"] = base64.b64encode(html_str.encode()).decode()
            result["html_mime_type"] = "text/html"

        if output_format in ("png", "png+html"):
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            mpl_fig, mpl_ax = plt.subplots(figsize=(width/100, height/100))
            for mn, dp in metrics_data.items():
                vals = [(p["timestamp"], p["value"]) for p in dp if p["value"] is not None]
                if vals:
                    _, v = zip(*vals)
                    mpl_ax.plot(range(len(v)), v, label=mn.upper(), linewidth=1.5)
            mpl_ax.set_title(chart_title)
            mpl_ax.set_ylabel("Usage %")
            mpl_ax.set_xlabel("Time")
            mpl_ax.legend()
            mpl_ax.grid(True, alpha=0.3)
            buf = io.BytesIO()
            mpl_fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close(mpl_fig)
            buf.seek(0)
            result["png_data"] = base64.b64encode(buf.getvalue()).decode()
            result["mime_type"] = "image/png"

        logger.info(f"Chart result: html={'html_data' in result}, png={'png_data' in result}, series={result.get('series')}, points={result.get('data_points')}")
        return result

    except Exception as e:
        logger.error(f"Chart generation failed for vm={vm_id}: {e}")
        return {"error": f"Chart generation failed: {str(e)[:200]}"}


@mcp.tool(description="Generate a multi-panel dashboard comparing multiple metrics or VMs side-by-side. Supports output_format='png+html'.")
async def tool_generate_dashboard(
    vm_ids: str = "",
    metrics: str = "cpu,memory",
    hours: int = 24,
    output_format: str = "png+html",
    width: int = 900,
    height: int = 550,
    title: str = "",
    ctx: Context = None
) -> dict:
    """Generate a multi-panel Plotly dashboard. vm_ids is comma-separated VM IDs, metrics is comma-separated metric names."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as e:
        return {"error": f"Dashboard generation unavailable: {e}"}

    vm_id_list = [v.strip() for v in vm_ids.split(",") if v.strip()]
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]

    if not vm_id_list:
        return {"error": "No VM IDs provided. Pass comma-separated vm_ids."}

    logger.info(f"Generating dashboard: vms={len(vm_id_list)}, metrics={metric_list}, hours={hours}")

    try:
        fig = make_subplots(rows=1, cols=len(metric_list),
                            subplot_titles=[m.upper() for m in metric_list],
                            shared_xaxes=True)

        total_series = 0
        for col, metric in enumerate(metric_list, 1):
            for vm_id in vm_id_list:
                perf_data = get_vm_performance(vm_id, metric, hours)
                if "error" in perf_data:
                    continue
                vm_name = perf_data.get("vm_name", vm_id)
                data_points = perf_data.get("metrics", {}).get(metric, [])
                if not data_points:
                    continue
                timestamps = [p["timestamp"] for p in data_points]
                values = [p["value"] for p in data_points]
                fig.add_trace(go.Scatter(
                    x=timestamps, y=values, mode='lines',
                    name=vm_name, legendgroup=vm_name,
                    showlegend=(col == len(metric_list))
                ), row=1, col=col)
                total_series += 1
            fig.update_yaxes(title_text="Usage %", row=1, col=col)

        dashboard_title = title or f"Dashboard ({', '.join(metric_list)}) - last {hours}h"
        fig.update_layout(title=dashboard_title, height=height, autosize=True,
                          showlegend=True, template="plotly_white")

        result = {"title": dashboard_title, "metrics": metric_list,
                  "vm_count": len(vm_id_list), "series": total_series, "hours": hours}

        if output_format in ("html", "png+html"):
            html_str = fig.to_html(include_plotlyjs="cdn", full_html=True,
                                    config={"responsive": True, "displayModeBar": True})
            result["html_data"] = base64.b64encode(html_str.encode()).decode()
            result["html_mime_type"] = "text/html"

        if output_format in ("png", "png+html"):
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            n_metrics = len(metric_list)
            mpl_fig, axes = plt.subplots(1, n_metrics, figsize=(width/100, height/100))
            if n_metrics == 1:
                axes = [axes]
            for col, metric in enumerate(metric_list):
                ax = axes[col]
                for vm_id in vm_id_list:
                    perf_data = get_vm_performance(vm_id, metric, hours)
                    if "error" in perf_data:
                        continue
                    vm_name = perf_data.get("vm_name", vm_id)
                    dp = perf_data.get("metrics", {}).get(metric, [])
                    vals = [p["value"] for p in dp if p["value"] is not None]
                    if vals:
                        ax.plot(range(len(vals)), vals, label=vm_name, linewidth=1.5)
                ax.set_title(metric.upper())
                ax.set_ylabel("Usage %")
                ax.legend(fontsize=7)
                ax.grid(True, alpha=0.3)
            mpl_fig.suptitle(dashboard_title)
            mpl_fig.tight_layout()
            buf = io.BytesIO()
            mpl_fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close(mpl_fig)
            buf.seek(0)
            result["png_data"] = base64.b64encode(buf.getvalue()).decode()
            result["mime_type"] = "image/png"

        logger.info(f"Dashboard result: html={'html_data' in result}, png={'png_data' in result}, series={total_series}")
        return result

    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
        return {"error": f"Dashboard generation failed: {str(e)[:200]}"}


# =============================================================================
# Register Resources
# =============================================================================

from resources import RESOURCES, PROJECT_ZONES_TEMPLATE


@mcp.resource("gcp://projects")
def resource_projects() -> str:
    """Complete list of all GCP projects. Read this first to know available project IDs."""
    return RESOURCES["gcp://projects"]["fn"]()


@mcp.resource("gcp://regions")
def resource_regions() -> str:
    """All GCP zones with region groupings."""
    return RESOURCES["gcp://regions"]["fn"]()


@mcp.resource("gcp://machine-types")
def resource_machine_types() -> str:
    """GCP machine type catalog with vCPU and memory specs."""
    return RESOURCES["gcp://machine-types"]["fn"]()


# =============================================================================
# Register Prompts
# =============================================================================

from prompts import PROMPTS


@mcp.prompt(
    name="vm_fleet_status",
    description="Generate a formatted fleet status report for a GCP project."
)
def prompt_vm_fleet_status(project_id: str, zone: str = "") -> str:
    """Fleet status report with VM overview, zone breakdown, and alerts."""
    return PROMPTS["vm_fleet_status"]["fn"](project_id, zone)


@mcp.prompt(
    name="vm_health_report",
    description="Generate a health report identifying VMs that need attention."
)
def prompt_vm_health_report(
    project_id: str,
    cpu_threshold: float = 80.0,
    memory_threshold: float = 85.0
) -> str:
    """Health report showing VMs exceeding CPU/memory thresholds or with errors."""
    return PROMPTS["vm_health_report"]["fn"](project_id, cpu_threshold, memory_threshold)


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting GCP Compute MCP Server...")
    logger.info("Endpoint: http://0.0.0.0:8048/mcp")
    logger.info("Data: 5 projects, 111 VMs, 24h metrics, 7d logs")
    logger.info("All data is deterministic (seed=42)")

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8048
    )
