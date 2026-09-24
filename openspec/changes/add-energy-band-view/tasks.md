## 1. Tracker — banda de sensibilidad

- [x] 1.1 TDD `tests/test_energy.py`: banda low (cache factor 0.0) y high (1.0)
  por mes con synthetic rows — identidad `low ≤ nominal ≤ high`, null heredado,
  bucketing mensual igual que 7mj.1 (no por primera interacción)
- [x] 1.2 Implementar emisión `monthly[m].energy_kwh_band: {low, high}` en
  `usage-tracker.py` reusando `energy_for()`; misma `energy_version` por bucket
- [x] 1.3 Metadata: `energy_band_cache_factors: [0.0, 1.0]` + nota de método en
  `fpa_config.py` / `validate_config()` (bloque requerido, fail-loud igual que 7mj.1)
- [x] 1.4 Schema aditivo (`specs/usage-report-v3.schema.json`): `energy_kwh_band`
  y metadata de banda; `--validate` verde

## 2. Dashboard — vista Energía (F8)

- [x] 2.1 TDD `tests/test_fpa_f8.py` (estilo f2–f7, sin playwright): tab
  "Energía" en tablist, barras mensuales con banda low–high, total del periodo,
  meses null visibles con razón, tag *assumed* en toda cifra, readout accesible
- [x] 2.2 Implementar vista en `viz-fpa.py`: registro en `tabs`/`VIEWS`/
  `tab_labels`, chart con banda, KPI del total (banda 18/33/175 en dataset
  actual), cumpliendo accesibilidad/mobile y "loss visible, no silenciosa"
- [x] 2.3 Suite completa: `test_tracker.py`, `test_energy.py`, `test_viz.py`,
  `test_fpa_f6*.py`, `test_fpa_f8.py` — 0 pageerrors en smoke Chromium si
  playwright disponible

## 3. Datos y docs (pasada atómica final)

- [x] 3.1 Regen dataset congelado (`--until`), goldens dataset-derived y
  `data/fpa-dashboard.html` en una sola corrida; determinismo doble corrida
  (única diff permitida: timestamp — FPA-104)
- [x] 3.2 README: sección Energía referenciando la vista + check-docs verificado
- [ ] 3.3 Commits por fase y push; cerrar coffe-5ng; `openspec archive`
