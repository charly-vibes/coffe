# Tasks: add-usage-report-spec

## 1. Schema del contrato

- [x] 1.1 JSON Schema `specs/usage-report-v3.schema.json` (metadata, buckets, sessions, multitasking, project_daily)
- [x] 1.2 Validar el reporte real contra el schema (`check-jsonschema` ok)
- [x] 1.3 Flag `--validate` en `viz-gantt.py` y `viz-dashboard.py`

## 2. Tests

- [x] 2.1 `tests/test_tracker.py`: funciones puras (24 tests: estimate_cost, parse_ts, model_details, clean_proj_name, get_sub_cost, calc_subscription_fees, hour_key)
- [x] 2.2 Golden test de `aggregate()` con rows sintéticos (`tests/golden/aggregate-snapshot.json`, regen con `REGEN_GOLDEN=1`)
- [x] 2.3 `tests/test_viz.py`: smoke en Chromium real — 0 pageerrors, ≥7 SVGs en dashboard, >100 celdas en Gantt

## 3. Refactor de aggregate()

- [x] 3.1 Clases `Bucket`/`HourlyBucket` (elimina 4 copias del bloque de acumulación)
- [x] 3.2 Helpers puros: `_session_stats`, `_multitasking_block`, `_project_daily`, `_context_switches`, `collect_skills_and_commands`
- [x] 3.3 Skills/commands inyectados a `aggregate()` (pura, testeable)
- [x] 3.4 Snapshot pre/post refactor: equivalencia verificada (3 diffs, todos intencionales)

## 4. Robustez

- [x] 4.1 `except` tipados + contador `metadata.skipped_lines`
- [x] 4.2 `parse_ts` tolera strings inválidos (→ None)
- [x] 4.3 `clean_proj_name` sin ruta hardcodeada
- [x] 4.4 Remover `tools_summary`

## 5. Docs

- [x] 5.1 `openspec/project.md`: testing strategy actualizado
- [x] 5.2 README: sección de tests
- [x] 5.3 `openspec archive` del change (al cerrar)
