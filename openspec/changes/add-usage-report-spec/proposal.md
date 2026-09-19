# Add: Usage Report Contract (spec + tests)

## Why

El producto principal del repo — `data/usage_report_v3.json` — no tenía
contrato formal: el schema vivía implícito en `aggregate()` (tracker) y en
`prepare()` (dashboard). Los viz scripts consumen claves con defaults
silenciosos (`or 0`), así que un renombre en el tracker rompería los viz
*sin error*. Además el repo no tenía tests y eso ya costó 4 bugs de JS
llegando a producción.

## What Changes

- **ADDED**: capability `usage-report` con el contrato del JSON
  (schema en `specs/usage-report-v3.schema.json`)
- **ADDED**: suite de tests (`tests/test_tracker.py`, `tests/test_viz.py`)
- **ADDED**: flag `--validate` en los viz scripts (opcional, requiere `jsonschema`)
- **MODIFIED**: `aggregate()` refactorizada a clases `Bucket`/`HourlyBucket`
  + helpers puros (`_session_stats`, `_multitasking_block`, `_project_daily`,
  `_context_switches`, `collect_skills_and_commands`) — mismo output,
  verificado con snapshot pre/post
- **REMOVED**: clave muerta `tools_summary` (siempre `{}`)
- **MODIFIED**: daily `cost_real` ahora redondeado a 2 decimales (antes
  filtraba floats crudos, inconsistente con el resto de buckets)
- **MODIFIED**: `parse_ts` devuelve `None` ante strings inválidos (antes
  lanzaba `ValueError` y el `except: pass` descartaba la fila sin rastro)
- **MODIFIED**: extractores tipan sus `except` y cuentan descartes en
  `metadata.skipped` / `metadata.skipped_lines`
- **MODIFIED**: `clean_proj_name` deriva el prefijo de ruta de `Path.home()`
  (antes hardcodeaba `-var-home-sasha-para-areas-dev-gh-`)

## Impact

- Affected specs: `usage-report` (nueva)
- Affected code: `scripts/usage-tracker.py` (refactor), `scripts/viz-*.py`
  (`--validate`), `tests/` (nuevo), `specs/usage-report-v3.schema.json` (nuevo)
- Compat: output del tracker equivalente salvo lo listado arriba; golden
  snapshot regenerado
