# Project Context

## Purpose

Reusable AI-usage tracker: extracts interaction, session, and cost data from local
CLI traces (Claude CLI, Pi, Amp, Gemini), filters to a configurable project set, and
produces JSON reports plus a self-contained Gantt visualization.

Extracted from the `microdancing` blog's `data/datos-uso-ia` branch (original tip
`09c063e`) so the tracker can be reused and extended independently of the blog series.

## Tech Stack

- Python 3, stdlib only (`json`, `collections`, `datetime`, `pathlib`) — no external dependencies
- Self-contained HTML visualization (no build step, no CDN)

## Project Conventions

### Code Style

- Single-file scripts in `scripts/`, stdlib only
- Config constants (source paths, subscriptions, model pricing) live at module top — keep them discoverable and easy to edit

### Architecture Patterns

- `scripts/usage-tracker.py` reads raw tool traces from `~/.claude`, `~/.pi/agent`, `~/.amp`, `~/.gemini` → writes `data/usage_report_v3.json` (hourly/daily/monthly/projects/sessions/skills/commands/multitasking/project_daily)
- `scripts/viz-gantt.py` reads the JSON report → writes `data/gantt-multitasking.html` (project × day Gantt with concurrency row)
- Generated artifacts are committed under `data/` alongside the code that produced them

### Testing Strategy

- No test suite yet; validate by spot-checking report totals against tool dashboards
- When changing token accounting, cross-check against a second source (e.g. `toolpath`/`path-cli`) as done for v4.1

## Reuse notes

- `CHARLY_FILTER`, `SUBSCRIPTIONS`, and `MODEL_PRICING` are project-specific constants — parametrize before reusing for another machine or project set
- Blog-series drafts stayed in `microdancing/drafts/`; this repo is data + code only
- `README.md` (originally `data/TRACKING.md`) documents the v3 data layout and known gaps
