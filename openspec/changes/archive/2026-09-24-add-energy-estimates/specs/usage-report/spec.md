## ADDED Requirements

### Requirement: estimación de energía por modelo (assumed)

El tracker SHALL (debe) emitir por mes `energy_kwh_by_model` (modelo → kWh
estimado como número de 3 decimales, o — solo para modelos sin telemetría de
tokens, ver requirement siguiente — `{"kwh": null, "reason": ...}`) y
`energy_kwh` (total mensual), calculados como
`(tokens_frescos + cache_read × cache_read_energy_factor) × J/token del tier /
3.6e6`. La metadata SHALL (debe) incluir `energy_provenance` (siempre
"assumed" — ningún proveedor reporta energía), `energy_config_source`,
`energy_cache_read_factor` y `energy_method` con la fórmula documentada. Los
campos son aditivos al reporte existente y jamás se mezclan con los costes USD
(FPA-002). Cada modelo SHALL (debe) registrar su `energy_tier` efectivo dentro
de `energy_kwh_by_model` para que la clasificación sea auditable.

#### Scenario: energía mensual por modelo presente

- **WHEN** el tracker genera `usage_report_v3.json` con el bloque
  `energy_coefficients` en config
- **THEN** cada mes incluye `energy_kwh_by_model` y `energy_kwh`, y la metadata
  incluye `energy_provenance` = "assumed", `energy_cache_read_factor` y
  `energy_method`, validables contra el schema extendido

#### Scenario: cache_read ponderado

- **WHEN** un modelo acumula cache_read (p.ej. claude-sonnet-4-6: 87% de sus
  tokens son cache) y `cache_read_energy_factor` = 0.10
- **THEN** solo el 10% de los tokens cache_read entra al cómputo con el coeficiente
  del tier, y el factor usado queda registrado en metadata

#### Scenario: energía nunca es coste

- **WHEN** se compara `energy_kwh` con `cost_effective` del mes
- **THEN** son campos independientes en el reporte (unidades distintas, jamás
  sumados ni convertidos entre sí)

### Requirement: coeficientes de energía versionados y fail-loud en config

`config/fpa.json` SHALL (debe) tener un bloque `energy_coefficients` con:
tiers de J/token entregado (mínimo `flash`, `mid`, `frontier`), mapping
modelo→tier (incluyendo todas las variantes de nombre presentes en el dataset:
`google/…`, `anthropic/…`, `:free`, `<synthetic>`), `default_tier`,
`cache_read_energy_factor` y versionado por `effective` (mismo patrón que
`model_pricing.versions`). Si el bloque falta o está malformado, el tracker
SHALL (debe) abortar con error no-cero listando el campo faltante (criterio
coffe-mbz). Un modelo sin mapping SHALL (debe) usar `default_tier` y su tier
efectivo SHALL (debe) quedar registrado como `energy_tier` en el reporte —
sin defaults silenciosos invisibles. La versión de coeficientes para un bucket
mensual SHALL (debe) seleccionarse por la fecha de inicio del mes (última
`effective` ≤ primer día del mes) — el agregado mensual de tokens no permite
partir un mes entre versiones (a diferencia de `estimate_cost(when)`, que es
por interacción). Un mes que arranque antes que toda versión declarada SHALL
(debe) abortar con error no-cero: el autor de config cubre el rango de datos.

#### Scenario: config válida

- **WHEN** el tracker corre con `energy_coefficients` completo
- **THEN** cada bucket mensual usa la versión con `effective` más reciente ≤
  primer día del mes y el reporte registra `energy_config_source`

#### Scenario: mes sin cobertura de versión

- **WHEN** el primer día de un bucket mensual es anterior a toda `effective`
  declarada
- **THEN** el tracker aborta con error no-cero nombrando el mes, sin escribir
  el reporte

#### Scenario: config malformada aborta

- **WHEN** falta `cache_read_energy_factor` o un tier declarado
- **THEN** el tracker aborta con error no-cero nombrando el campo, sin escribir
  el reporte

#### Scenario: modelo nuevo sin mapping

- **WHEN** aparece un modelo no mapeado (p.ej. un lanzamiento futuro)
- **THEN** se le aplica `default_tier` y su `energy_tier` en el reporte lo
  delata para auditar y mapear explícitamente

### Requirement: modelos sin telemetría de tokens emiten null con razón

Para modelos con interacciones pero tokens en cero, el tracker SHALL (debe) emitir `null` con razón en vez de 0: en `tokens_by_model` (p.ej.
`amp`, `<synthetic>`), `energy_kwh_by_model` SHALL (debe) emitir `null` con
`reason` "sin telemetría de tokens" — nunca 0, que sugeriría medición (FPA-008).

#### Scenario: modelo sin tokens

- **WHEN** el reporte incluye un modelo con interacciones > 0 y tokens = 0
- **THEN** su entrada en `energy_kwh_by_model` es `{"kwh": null, "reason":
  "sin telemetría de tokens"}` y el total mensual `energy_kwh` suma solo los
  modelos con datos
