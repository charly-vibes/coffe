# Change: estimación de energía (kWh) por modelo en el reporte de uso

## Why
El reporte no tiene ninguna dimensión energética: solo costes en USD y tokens.
La investigación de 2026-09-23 (ver whisper branch notes, topic `energia`) muestra
que los tokens por modelo ya medidos permiten estimar kWh con coeficientes
públicos (Luccioni et al. / AI Energy Score), pero que ningún proveedor reporta
energía — toda cifra es `assumed` y necesita provenance explícito para no
contaminar la honestidad del reporte.

## What Changes
- `config/fpa.json` gana un bloque `energy_coefficients` (J/token entregado por
  tier de modelo + multiplicador de energía del cache_read + versión por fecha,
  mismo patrón que `model_pricing.versions`)
- El tracker emite, de forma aditiva: `energy_kwh_by_model` mensual,
  `energy_kwh` mensual y metadata `energy_provenance`/`energy_config_source`/
  `energy_cache_read_factor`
- Modelos con interacciones pero sin telemetría de tokens (p.ej. `amp`,
  `<synthetic>`) emiten `null` con razón — no 0 (FPA-008)
- Schema `specs/usage-report-v3.schema.json` extendido (aditivo)
- Dashboard: fuera de alcance en este change (follow-up si se quiere banda
  min/max visual con el multiplicador de cache como eje)

## Impact
- Affected specs: usage-report
- Affected code: scripts/usage-tracker.py (loader + cómputo), config/fpa.json,
  specs/usage-report-v3.schema.json, tests/, data/usage_report_v3.json (regen),
  README (check-docs), goldens F2/summary si el dataset cambia
