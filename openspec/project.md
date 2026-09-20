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

- `scripts/usage-tracker.py` reads raw tool traces from `~/.claude`, `~/.pi/agent`, `~/.amp` (Gemini arrives via Pi) → writes `data/usage_report_v3.json` (schema: `specs/usage-report-v3.schema.json`)
- Inside the tracker: extractors (`extract_*`) → `collect_skills_and_commands()` → pure `aggregate()` built on `Bucket`/`HourlyBucket` classes with injected skills/commands
- `scripts/viz-gantt.py` reads the JSON report → writes `data/gantt-multitasking.html` (project × day Gantt with concurrency row)
- `scripts/viz-fpa.py` reads the JSON report → writes `data/fpa-dashboard.html` (the main dashboard; the old insights dashboard was removed in coffe-gen.5, see git history for `viz-dashboard.py`)
- Both viz scripts accept `--validate` (validates against the JSON Schema; needs `jsonschema`)
- Generated artifacts are committed under `data/` alongside the code that produced them

### Testing Strategy

- `tests/test_tracker.py`: pure functions + `aggregate()` with synthetic rows; golden snapshot in `tests/golden/` (regen with `REGEN_GOLDEN=1`, review the diff)
- `tests/test_viz.py`: smoke test in real Chromium (playwright, optional) — 0 pageerrors, charts actually render; exists because DOM-stub smoke tests let 4 JS bugs reach production
- Run: `python3 tests/test_tracker.py && python3 tests/test_viz.py`
- When changing token accounting, cross-check against a second source (e.g. `toolpath`/`path-cli`) as done for v4.1, and update the golden snapshot

## Reuse notes

- `CHARLY_FILTER`, `SUBSCRIPTIONS`, and `MODEL_PRICING` are project-specific constants — parametrize before reusing for another machine or project set
- `aggregate()` is pure (no disk I/O): skills/commands are injected — test it with synthetic rows, not by pointing at real logs
- Blog-series drafts stayed in `microdancing/drafts/`; this repo is data + code only
- `README.md` (originally `data/TRACKING.md`) documents the v3 data layout and known gaps
