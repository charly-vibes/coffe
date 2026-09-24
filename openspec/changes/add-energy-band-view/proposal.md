# Change: Vista de energía estimada con banda de sensibilidad de caché en el dashboard

## Why

El epic coffe-7mj emitió `energy_kwh` por mes (33.4 kWh / 9 meses) al reporte y lo
documentó en el README, pero el dashboard FP&A no lo muestra: la estimación es
invisible para el lector del dashboard y la banda de sensibilidad 18/33/175 kWh
(el cache_read factor es el parámetro dominante) solo vive en prosa. coffe-5ng.

## What Changes

- Tracker: emisión aditiva de `energy_kwh_band: {low, high}` por mes — recomputo
  del mismo `energy_for()` con cache_read factor 0.0 y 1.0 (mismos buckets,
  mismos coeficientes versionados, misma `energy_version` por bucket); meses sin
  telemetría quedan `null` en banda también.
- Metadata: `energy_band_cache_factors: [0.0, 1.0]` para que el lector del JSON
  (y el viz) sepan qué representan los extremos sin duplicar config.
- Schema `specs/usage-report-v3.schema.json`: propiedades aditivas (+ band).
- viz-fpa.py: nueva vista/tab **"Energía"** con barras mensuales de kWh
  estimados, banda low–high por mes y total del periodo (~18/33/175 kWh en el
  dataset actual), meses null visibles con razón, tag *assumed* en toda cifra
  (provenance), readout por hover/focus/tap, mobile single-column.
- Regeneración de dataset + goldens + README (check-docs) en pasada atómica.

No breaking: todo aditivo en schema y reporte; las 6 vistas existentes no cambian.

## Impact

- Affected specs: `usage-report` (ADDED banda), `fpa-dashboard` (ADDED vista energía)
- Affected code: `scripts/usage-tracker.py` (band), `scripts/fpa_config.py`
  (factor metadata), `specs/usage-report-v3.schema.json`, `scripts/viz-fpa.py`
  (vista/tab F8), `tests/test_energy.py`, `tests/test_fpa_f8.py` (nuevo),
  `data/usage_report_v3.json`, `data/fpa-dashboard.html`, goldens, README
