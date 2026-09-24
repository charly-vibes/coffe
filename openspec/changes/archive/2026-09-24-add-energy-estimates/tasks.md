## 1. Config y loader
- [x] 1.1 Añadir bloque `energy_coefficients` a `config/fpa.json` (tiers
  flash/mid/frontier, mapping de los 29 modelos presentes — incluyendo variantes
  `google/…` vs `gemini-…`, `anthropic/…` vs `claude-…`, `:free` y
  `<synthetic>` —, default_tier, cache_read_energy_factor 0.10,
  versions.effective 2025-12-01 — primer día del primer bucket mensual, no de
  la primera interacción: la selección de versión es por bucket, coffe-7mj.2)
- [x] 1.2 Loader + validador fail-loud en `scripts/usage-tracker.py` (campos
  requeridos, tiers declarados, versión por fecha; test de abort con campo
  faltante)

## 2. Cómputo y reporte (TDD)
- [x] 2.1 Tests primero: energy por mes/modelo, ponderación de cache_read,
  cache_write a peso completo, null+razón para modelos sin telemetría, total
  mensual = suma de modelos con datos, selección de versión por primer día del
  mes, abort por mes sin cobertura, metadata energy_* completa
  (tests/test_energy.py)
- [x] 2.2 Implementar cómputo y emisión aditiva en el tracker
- [x] 2.3 Extender `specs/usage-report-v3.schema.json` (aditivo) y validar

## 3. Dataset y artefactos
- [x] 3.1 Regenerar `data/usage_report_v3.json` y verificar interacciones/
  costes sin cambio (solo campos nuevos)
- [x] 3.2 REGEN_GOLDEN=1 de goldens dataset-derived si el diff los toca
- [x] 3.3 README: campo nuevo en la descripción del reporte + método de
  energía con cita de fuentes de coeficientes (Luccioni et al. / AI Energy
  Score; ancla de contexto Google 0.24 Wh/prompt) (check-docs verde)

## 4. Cierre
- [x] 4.1 Suite completa verde + doble corrida determinista
- [x] 4.2 ro5u del diff
- [x] 4.3 Commit + bd close + push
