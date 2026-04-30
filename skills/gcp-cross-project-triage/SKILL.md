---
name: gcp-cross-project-triage
description: >
  Use when the user asks for a triage, health overview, or cross-project
  comparison across all GCP projects. Triggers on phrases like
  "triage my GCP projects," "which project needs attention,"
  "cross-project health," "GCP projects status overview." For a single
  project's deep dive, use tool_get_project_health directly instead.
langgraph-targets: [react_agent, synthesis]
langgraph-priority: 50
langgraph-requires-tools: [execute_python]
---

# gcp-cross-project-triage — multi-tool workflow skill

## Workflow

When this skill activates, run these steps in order:

1. **Discover GCP tools.** Call `tool_search` ONCE with the query
   "compare GCP projects health drill-down" to bind
   `tool_compare_projects` and `tool_get_project_health` into your
   toolbox. (In this agent, tools are dynamically discovered; the two
   tools above are not bound by default and must be discovered before
   they can be called.)

2. **Compare across projects.** Call `tool_compare_projects` (no args).
   Returns a `projects` list with VM counts, averages, and a
   `health` field per project.

3. **Identify projects needing drill-down.** A project needs drill-down
   if `health == "red"` OR `health == "yellow"` OR `error_count > 0`.

4. **Drill into each flagged project.** For EACH flagged project, call
   `tool_get_project_health(project_id)`. Run these in parallel — emit
   one `tool_get_project_health` tool call per flagged project ID, in a
   single turn. Do not call `tool_search` again.

5. **Synthesize.** Emit `SYNTHESIZE_RESPONSE_V1`. The synthesis turn
   will then call the `render_gcp_triage_report` function below
   (inline it into your `execute_python` code) with the comparison
   data and the per-project drilldown data.

**Do not call `tool_search` more than once for this workflow.** Steps
2-4 use tools that step 1 already bound. Calling `tool_search` again
wastes turns and does not help.

## Synthesis program (after tools return)

The synthesis program MUST inline the function below at the top of the
`code` argument, then call it. Tail of the program is **exactly** this
(no edits, no defensive checks added):

```python
comparison = []
drilldowns = []
for idx, name, data in iter_tool_results():
    if name == "tool_compare_projects":
        comparison = primary_records(data)
    elif name == "tool_get_project_health" and "error" not in data:
        drilldowns.append(data)
print(render_gcp_triage_report(comparison, drilldowns))
```

### Critical rules — do NOT modify the loop

**`data` is already parsed.** The interceptor has already unwrapped
the MCP `{'type':'text','text':'<json>'}` envelope and called
`json.loads()`. By the time you see `data`, it is a Python dict (for
single-result tools like `tool_compare_projects` and
`tool_get_project_health`). DO NOT add any of these:

  * `isinstance(data, list)` checks — `data` is a dict here, not a list
  * `data[0]['text']` accessors — there is no text envelope; you'd be
    reading into the dict's first key, which is wrong
  * `json.loads(data)` — `data` is not a string
  * `if data and isinstance(data[0], dict) and "projects" in data[0]:`
    style defensive walks — they all fail because `data` is the dict
    already.

Just call `primary_records(data)` and trust it. It returns the
records list (`tool_compare_projects.projects` here) for any
list-of-dict-shaped inner field.

**Find tool results by tool name, NOT by index.** Do NOT use
`tool_data(N)`. When many drilldowns are in scope (one per yellow
project), picking the right N by reading the `# tool_result_N` comments
is brittle and the model frequently picks N=0 (1-indexed sandbox →
KeyError) or the wrong index. `iter_tool_results()` + filter by `name`
is the canonical pattern — same for any tool count.

The function returns a complete report wrapped in a ` ```text ` fence —
that is the whole user-facing answer. Do NOT write markdown tables.
Do NOT use pandas. Do NOT add prose around the call. Every summary
statement is computed from the data; no string literals describe the
data.

## Function

```python
def render_gcp_triage_report(comparison, drilldowns):
    lines = ["```text"]

    total_projects = len(comparison)
    total_vms = sum(p.get("total_vms", 0) for p in comparison)
    total_running = sum(p.get("running", 0) for p in comparison)
    total_stopped = sum(p.get("stopped", 0) for p in comparison)
    total_errors = sum(p.get("error_count", 0) for p in comparison)
    total_high_cpu = sum(p.get("high_cpu_count", 0) for p in comparison)

    health_counts = {"green": 0, "yellow": 0, "red": 0}
    for p in comparison:
        h = p.get("health", "unknown")
        if h in health_counts:
            health_counts[h] += 1

    # ── Header ──────────────────────────────────────────────────
    lines.append("=" * 80)
    lines.append(f"  GCP TRIAGE REPORT  —  {total_projects} projects, {total_vms} VMs")
    lines.append("=" * 80)
    lines.append("")

    # Health distribution as bar
    bar_w = 40
    counts = [
        ("green ", health_counts["green"], "█"),
        ("yellow", health_counts["yellow"], "▒"),
        ("red   ", health_counts["red"], "█"),
    ]
    if total_projects:
        lines.append(f"  Health distribution ({total_projects} projects):")
        for label, cnt, ch in counts:
            fill = int(round(cnt / total_projects * bar_w))
            bar = ch * fill + " " * (bar_w - fill)
            lines.append(f"    {label}  {cnt:>3} [{bar}]")
        lines.append("")

    # VM summary line — every value computed
    lines.append(
        f"  VMs:  {total_running} running, {total_stopped} stopped, "
        f"{total_vms - total_running - total_stopped} other"
    )
    lines.append(
        f"  Signals:  {total_errors} error events, {total_high_cpu} high-CPU alerts"
    )
    lines.append("")

    # ── Cross-project table ────────────────────────────────────
    lines.append("PER-PROJECT COMPARISON")
    lines.append("-" * 80)
    lines.append(
        f"  {'Project':<25} {'VMs':>4} {'Run':>4} {'Stp':>4} "
        f"{'CPU%':>6} {'Mem%':>6} {'Err':>4} {'Health':<8} {'ID':<22}"
    )
    # Sort by health severity then by error count desc
    sev = {"red": 0, "yellow": 1, "green": 2, "unknown": 3}
    ordered = sorted(
        comparison,
        key=lambda p: (sev.get(p.get("health"), 9), -p.get("error_count", 0)),
    )
    for p in ordered:
        lines.append(
            f"  {p.get('name','?')[:24]:<25} "
            f"{p.get('total_vms',0):>4} {p.get('running',0):>4} "
            f"{p.get('stopped',0):>4} "
            f"{p.get('avg_cpu',0):>5.1f}% {p.get('avg_memory',0):>5.1f}% "
            f"{p.get('error_count',0):>4} "
            f"{p.get('health','?'):<8} {p.get('project_id','?'):<22}"
        )
    lines.append("")

    # ── Per-project drill-downs (only flagged ones) ────────────
    if drilldowns:
        lines.append("DRILL-DOWN — projects needing attention")
        lines.append("-" * 80)
        for d in drilldowns:
            name = d.get("project_name", d.get("project_id", "?"))
            vm_summary = d.get("vm_summary", {})
            alerts = d.get("alerts", [])
            recent_stops = d.get("recent_stops", [])
            zone_breakdown = d.get("zone_breakdown", [])
            lines.append(f"  >> {name}  ({d.get('project_id','')})")
            lines.append(
                f"     {vm_summary.get('total',0)} VMs "
                f"({vm_summary.get('running',0)} running, "
                f"{vm_summary.get('stopped',0)} stopped, "
                f"{vm_summary.get('terminated',0)} terminated)"
            )
            if zone_breakdown:
                zone_strs = [
                    f"{z.get('zone','?')}: {z.get('running',0)}r/{z.get('stopped',0)}s"
                    for z in zone_breakdown[:5]
                ]
                lines.append(f"     zones: {', '.join(zone_strs)}")
            if alerts:
                # Group alerts by type
                err_alerts = [a for a in alerts if a.get("type") == "ERROR_LOG"]
                cpu_alerts = [a for a in alerts if a.get("type") == "HIGH_CPU"]
                if cpu_alerts:
                    lines.append(f"     HIGH_CPU on {len(cpu_alerts)} VM(s):")
                    for a in cpu_alerts[:3]:
                        lines.append(
                            f"        {a.get('vm_name','?')} "
                            f"({a.get('zone','?')}) {a.get('value','?')}%"
                        )
                if err_alerts:
                    lines.append(f"     ERROR_LOG events: {len(err_alerts)}")
                    for a in err_alerts[:3]:
                        lines.append(
                            f"        {a.get('vm_name','?')} "
                            f"({a.get('zone','?')}): "
                            f"{a.get('message','')[:60]}"
                        )
            if recent_stops:
                lines.append(f"     {len(recent_stops)} VM(s) stopped in last 24h:")
                for s in recent_stops[:3]:
                    lines.append(
                        f"        {s.get('vm_name','?')} "
                        f"({s.get('zone','?')}) at {s.get('stopped_at','?')}"
                    )
            lines.append("")

    # ── Footer — computed verdict ──────────────────────────────
    lines.append("VERDICT")
    lines.append("-" * 80)
    if health_counts["red"] > 0:
        verdict = (
            f"  {health_counts['red']} project(s) RED — drill-down above. "
            f"Address high-CPU and error events first."
        )
    elif health_counts["yellow"] > 0:
        verdict = (
            f"  {health_counts['yellow']} project(s) YELLOW — review the "
            f"drill-down for early-warning signals."
        )
    else:
        verdict = "  All projects GREEN — no immediate action needed."
    lines.append(verdict)
    lines.append("")
    lines.append("=" * 80)
    lines.append("```")
    return "\n".join(lines)
```
