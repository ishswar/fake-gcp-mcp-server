# GCP Compute MCP Server

A fake GCP Compute Engine MCP server for AI agent testing. Provides a fully synthetic environment with projects, VMs, performance metrics, and event logs.

## Data Overview

- **5 projects** with 3-4 zones each
- **111 VMs** (12-32 per project) distributed across zones
- **24-hour performance data** (CPU, memory, disk) at 5-minute intervals
- **7 days of event logs** (START, STOP, RESTART, ERROR events)
- **All data is deterministic** (seed=42) - same on every restart

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

Server runs at: `http://localhost:8048/mcp`

## Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector http://localhost:8048/mcp
```

## Connect to AI Agent

Add to your MCP server configuration:

```json
{
  "name": "gcp-compute",
  "url": "http://localhost:8048/mcp",
  "transport": "streamable-http"
}
```

## Available Tools (13)

### Project Tools
- `tool_list_projects` - List all projects with summary info
- `tool_get_project` - Get project details (supports partial ID matching)
- `tool_list_users` - List IAM users for a project

### Zone Tools
- `tool_list_zones` - List zones with VM counts
- `tool_get_zone_summary` - Get zone details with VM list

### VM Tools
- `tool_list_vms` - List VMs with optional filters
- `tool_get_vm` - Get full VM details
- `tool_search_vms` - Free-text search across VMs

### Performance Tools
- `tool_get_vm_performance` - Get performance time series (chart-ready)

### Log Tools
- `tool_get_vm_logs` - Get VM event logs
- `tool_get_recent_events` - Cross-VM event query

### Aggregate Tools
- `tool_get_project_health` - Project health dashboard
- `tool_get_high_utilization_vms` - Find high-utilization VMs

## Resources (3)

- `gcp://projects` - List of all projects
- `gcp://regions` - Zone/region mappings
- `gcp://machine-types` - Machine type catalog

## Prompts (2)

- `vm_fleet_status` - Formatted fleet status report
- `vm_health_report` - Health report with thresholds

## Project Structure

```
gcp-mcp/
├── server.py           # FastMCP app entry point
├── data_generator.py   # Fake data generation (seed=42)
├── data_store.py       # Singleton in-memory store
├── tools/
│   ├── __init__.py
│   ├── projects.py     # Project tools
│   ├── zones.py        # Zone tools
│   ├── vms.py          # VM tools
│   ├── performance.py  # Performance metrics
│   ├── logs.py         # Event logs
│   └── aggregates.py   # Health/aggregate tools
├── resources.py        # MCP resources
├── prompts.py          # MCP prompts
├── requirements.txt
└── README.md
```

## Example Queries

```
"List all projects"
"Show me the health status of project alpha"
"Find VMs with high CPU usage in proj-gamma-5r8t"
"What errors happened in the last 24 hours?"
"Show performance data for vm-abc123"
"Search for VMs tagged with 'http-server'"
```
