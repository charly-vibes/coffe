# Delta: fpa-dashboard

## ADDED Requirements

### Requirement: cash cost desde el ledger de cargos reales

El Dashboard SHALL (debe) computar el cash cost como la suma de los cargos
reales del ledger `data/charges.json` (provenance *reported*), contando solo
los kinds IA `subscription|credits|refund` dentro del periodo mostrado —
`api_cycle` aporta $0 y los cargos de storage quedan fuera del cash de IA.
Toda cifra de cash derivada del ledger SHALL (debe) llevar el tag
*reported*. Si un periodo no tiene facturas para un proveedor, el cash de
ese proveedor SHALL (debe) mostrarse "n/a" con la razón (FPA-008), nunca
vacío ni cero inventado. El cash cost (ledger) y el coste efectivo
(estimado API-equivalente del tracker) SHALL (debe) seguir siendo medidas
separadas y jamás sumarse (FPA-002). Los fees implícitos del calendario de
suscripciones NO son cash cost: solo alimentan la reconciliación (FPA-082)
y la economía de planes (FPA-130–133).

#### Scenario: cash mensual del ledger

- **WHEN** se muestra el cash cost de un mes con facturas (p.ej. mayo 2026:
  claude Pro $20 + codex Plus $20 + gemini $19.99)
- **THEN** la cifra es la suma de los cargos del ledger de ese mes y lleva
  el tag *reported*

#### Scenario: proveedor sin facturas en el periodo

- **WHEN** un proveedor no registra cargos en el periodo consultado
  (p.ej. openrouter entre mar y may 2026)
- **THEN** su cash se muestra "n/a" con la razón (sin facturas en el
  periodo), no cero ni ausencia silenciosa

#### Scenario: refund descuenta

- **WHEN** el ledger incluye un refund negativo en el periodo
  (p.ej. claude-cli −$28.22 el 2026-02-19)
- **THEN** el cash del periodo lo descuenta (es dinero devuelto, no gastado)

## MODIFIED Requirements

### Requirement: alertas con evidencia y umbrales configurables

El Dashboard SHALL (debe) listar alertas con severity, nombre de regla y valores de
evidencia, cubriendo: share efectivo/precio de plan > 25× (verify plan), discrepancia
entre el cash cost real (ledger `data/charges.json`, *reported*) y las cargas
implícitas del calendario de suscripciones (*assumed*) más allá de la tolerancia
(reconciliación, FPA-082), over-budget,
unit-cost +15% MoM, shift de mix premium > 5pts en 3 meses, concentración
top-3 > 50%, y staleness del reporte > 14 días. Todos los umbrales SHALL (debe) ser
configurables.

#### Scenario: reconciliación de suscripción

- **WHEN** el cash real del ledger difiere de las cargas implícitas del
  calendario más allá de la tolerancia
- **THEN** se emite una alerta de reconciliación mostrando ambas cifras
  (real *reported* vs implícito *assumed*), con la corrección del
  calendario de coffe-a31 el caso motivador queda resuelto: jun 2026 real
  $0 (sin factura) vs implícito $0

#### Scenario: calendario desalineado con facturas

- **WHEN** el calendario del config afirma una suscripción que las
  facturas no respaldan (o viceversa)
- **THEN** la alerta de reconciliación lo señala con los dos montos, que es
  la señal para corregir `config/fpa.json`

### Requirement: economía de suscripción

El Dashboard SHALL (debe) calcular utilización por plan (efectivo ÷ precio),
break-even mensual y headroom, comparar cash cost bajo 4 casos (actual,
todo pay-per-token, todo Pro, todo Max) y declarar que la equivalencia por coste
efectivo ignora usage limits del plan. La economía de planes SHALL (debe)
operar sobre el calendario de suscripciones del config — corregido a las
facturas (coffe-a31) — con provenance *assumed*: un panel por cada periodo
del calendario. Cuando ninguna suscripción esté activa al cierre del
reporte (Free/cancelado), el plan default del forecast SHALL (debe) ser
"sin suscripción" (fee $0; cash = p2p escalado, FPA-073) y los periodos del
calendario quedan como escenarios hipotéticos seleccionables.

#### Scenario: break-even visible

- **WHEN** se muestra el panel de un plan
- **THEN** aparecen utilización, break-even y headroom calculados del config

#### Scenario: sin suscripción activa al cierre

- **WHEN** el reporte termina después de la última factura de
  suscripción (p.ej. claude cancelado tras jun 2026)
- **THEN** el plan default del forecast es "sin suscripción" (fee $0) y
  los planes históricos del calendario siguen listables como escenarios

### Requirement: forecast con escenarios

El Dashboard SHALL (debe) proyectar el resto del año desde un run-rate base (media
FME de los últimos 3 meses; con menos de 3 meses de datos, la sección SHALL (debe)
mostrar "n/a" con la razón), aceptar escenarios (crecimiento %, cambio de rate %,
plan futuro), calcular efectivo y cash con las fórmulas FPA-072/073, mostrar
YTD+outlook vs presupuesto con varianza, fila separada para el resto del mes
parcial, y distinguir actual de forecast con patrón/label, no solo color, con
update sin reload. El plan futuro default SHALL (debe) ser la suscripción
activa al cierre del reporte; si no hay ninguna (Free/cancelado), el default
SHALL (debe) ser "sin suscripción" (fee $0) con los planes del calendario
como escenarios hipotéticos (FPA-071).

#### Scenario: cambio de escenario

- **WHEN** el usuario ajusta el growth % del escenario
- **THEN** el forecast se recalcula sin recarga y las cifras forecast quedan
  distinguidas de las actuales por patrón/label

#### Scenario: plan default sin suscripción activa

- **WHEN** ninguna suscripción del calendario cubre la fecha de fin del
  reporte
- **THEN** el forecast arranca con "sin suscripción" (cash = p2p escalado)
  y no inventa una suscripción que no existe
