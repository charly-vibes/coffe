# Delta: usage-report

## MODIFIED Requirements

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
pay-per-token del reporte (`pay_per_token_charges`) SHALL (debe) emitirse como
campo separado con provenance *assumed*: el tracker no ve facturas, es un
estimado por tokens × pricing. Los cargos REALES (FPA-013) viven en el ledger
`data/charges.json` — transcripto de facturas, provenance *reported* — que el
dashboard consume para el cash cost (ver fpa-dashboard); el tracker no lo
emite ni lo duplica.

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

## ADDED Requirements

### Requirement: ledger de cargos reales

El repo SHALL (debe) mantener `data/charges.json` como única fuente de cargos
reales (facturas de proveedores, provenance *reported*): un objeto por
proveedor con entradas `{date, amount, kind, note}` en USD, donde kind es
`subscription | credits | refund | api_cycle` (factura de ciclo $0). Los
cargos de storage (p.ej. Google One) SHALL (debe) quedar fuera del ledger —
son gasto de storage, no de IA. Un `refund` SHALL (debe) ser el único kind
con amount negativo.

#### Scenario: kinds del vocabulario IA

- **WHEN** se valida el ledger
- **THEN** toda entrada tiene kind `subscription|credits|refund|api_cycle`,
  fecha ISO, amount numérico y note (FPA-008: nunca vacío sin razón)

#### Scenario: totales IA verificables

- **WHEN** se suman los amounts del ledger por proveedor
- **THEN** claude-cli $451.78, codex $40.00, amp $275.00, gemini-cli
  $119.94, openrouter $470.00 — IA $1,356.72 en total (transcripción
  2026-09-20, guardada en tests/test_charges.py)
