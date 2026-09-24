# Delta: usage-report

## ADDED Requirements

### Requirement: Report contract

El reporte `usage_report_v3.json` SHALL (debe) conformar al JSON Schema
`specs/usage-report-v3.schema.json`. Los viz scripts SHALL (debe)N poder validar
el reporte antes de renderizar (`--validate`).

#### Scenario: reporte válido pasa la validación

- **WHEN** se ejecuta `python3 scripts/viz-dashboard.py --validate`
- **THEN** el reporte satisface el schema y el script imprime `schema OK`

#### Scenario: clave requerida ausente falla la validación

- **WHEN** un reporte sin `project_daily.matrix` se valida
- **THEN** `jsonschema.validate` lanza `ValidationError`

### Requirement: agregación pura e inyectable

`aggregate()` NO SHALL (debe) leer archivos del disco; skills y comandos se
inyectan como parámetros (colección en `collect_skills_and_commands()`).

#### Scenario: aggregate con rows sintéticos es determinista

- **WHEN** `aggregate(rows_sintéticas, sessions_sintéticas)` corre dos veces
- **THEN** el output es idéntico byte a byte (golden test)

### Requirement: loss visible, no silenciosa

Las líneas de logs descartadas por errores de parseo SHALL (debe)N contarse en
`metadata.skipped_lines` (y detalle por archivo en `metadata.skipped`).

#### Scenario: archivo corrupto no desaparece sin rastro

- **WHEN** un JSONL tiene una línea corrupta
- **THEN** el extractor la salta y `metadata.skipped_lines` la refleja
