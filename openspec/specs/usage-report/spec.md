# usage-report Specification

## Purpose
TBD - created by archiving change add-fpa-dashboard. Update Purpose after archive.
## Requirements
### Requirement: emisiones para dashboard FP&A

El tracker SHALL (debe) emitir, además de lo existente: breakdown mensual por tool
y modelo (interacciones y coste efectivo), project totals por mes vía
`project_daily`, cargas pay-per-token separadas de las cargas de suscripción,
commits y releases por proyecto/mes donde haya token de GitHub configurado, tokens
input/output/cache-read/cache-write por mes y modelo, interacciones por kind
(user prompts, assistant turns, tool calls), interacciones y coste de los proyectos
excluidos por el charly-filter, timezone usada para el bucketing horario/diario, y
las métricas de concurrencia (proyectos distintos por hora, picos de sesiones
simultáneas, project switches por hora activa) para el dashboard FP&A. Las cargas
pay-per-token SHALL (debe) emitirse como campo separado con provenance *assumed*:
el tracker no registra cargas reales (decisión 2026-09-20), así que el cash cost
efectivo es solo suscripciones.

#### Scenario: tokens por modelo presentes

- **WHEN** el tracker genera `usage_report_v3.json`
- **THEN** el reporte incluye tokens input/output/cache-read/cache-write por mes
  y modelo, validables contra el schema extendido

#### Scenario: interacciones por kind presentes

- **WHEN** el tracker genera el reporte
- **THEN** cada mes incluye interacciones desglosadas por kind, permitiendo
  calcular el share de tool-calls (FPA-140)

#### Scenario: share del filtro visible

- **WHEN** el charly-filter excluye proyectos
- **THEN** el reporte incluye interacciones y coste de los excluidos para calcular
  el share filtrado (FPA-141)

