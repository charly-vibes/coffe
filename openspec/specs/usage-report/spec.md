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
simultáneas, project switches por hora activa) para el dashboard FP&A.

Desde coffe-a31.2 (CRG-F1) el tracker SHALL (debe) consumir el ledger de cargos
reales `data/charges.json` y emitirlo de forma aditiva: `charges_real_by_month`
(proveedor → mes → USD, solo kinds IA, provenance *reported*),
`charges_reconciliation_by_month` (por mes y tool: cash real del ledger vs fee
implícito del calendario vs efectivo estimado — insumo de la reconciliación
FPA-082) y metadata `charges_source`/`charges_total_real`/`charges_provenance`.
El campo `pay_per_token_charges` mensual SHALL (debe) ser *reported* cuando el
ledger tiene cargas pay-per-token reales del mes (créditos/reembolsos — FPA-013
deja de ser assumed) y *assumed* (estimado tokens × pricing) si no; los fees
implícitos del calendario NUNCA se mezclan en ese campo. Los cargos del ledger
son cash cost: medida separada del coste efectivo, jamás sumadas (FPA-002).

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

#### Scenario: cargas pay-per-token reales del ledger

- **WHEN** el tracker genera el reporte y el ledger tiene cargas p2p del mes
  (p.ej. enero 2026: claude $20 en créditos + amp $80)
- **THEN** `pay_per_token_charges` del mes es la suma real del ledger con
  `pay_per_token_provenance` = "reported" (FPA-013 deja de ser assumed)

#### Scenario: mes sin cargas p2p en el ledger

- **WHEN** un mes no registra cargas p2p en el ledger (p.ej. abril 2026)
- **THEN** `pay_per_token_charges` es el estimado del tracker con provenance
  "assumed" — cifra presente, nunca vacío sin razón (FPA-008)

#### Scenario: insumo de reconciliación FPA-082

- **WHEN** el tracker genera `charges_reconciliation_by_month`
- **THEN** cada mes incluye cada tool con `charges_real` (ledger, *reported*),
  `subscription_fee_implicit` (calendario, *assumed*, no es cash) y
  `cost_effective` (tracker, *assumed*); los meses con facturas pero sin
  interacciones también aparecen (p.ej. recargas openrouter de jul-2026)

#### Scenario: total real unificado

- **WHEN** se compara `metadata.cost_total_real` con la suma mensual de
  `cost_real`
- **THEN** coinciden (una sola cuenta); la parte tracker queda separada en
  `cost_real_total_tracker` y los fees implícitos en
  `subscription_fees_by_month`, sin doble conteo (coffe-a31.2: resuelve la
  divergencia 381.62 vs 611.62 del dataset previo)

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

