# Tasks: add-real-charges

## 1. Contrato del ledger (FPA-013 real)

- [x] Guardar `data/charges.json` transcripto (5 proveedores, kinds IA
      `subscription|credits|refund|api_cycle`, sin storage) — hecho en el
      epic coffe-a31 antes de este change
- [x] Tests de guards del ledger (`tests/test_charges.py`): estructura,
      vocabulario de kinds, refund negativo único, totales por proveedor
      (claude $451.78, codex $40, amp $275, gemini $119.94, openrouter
      $470; IA $1,356.72)

## 2. Calendario de planes corregido a facturas (FPA-082/015)

- [x] `config/fpa.json`: claude-cli Max 03-19→04-19 $100, Max 04-19→05-19
      $100, Pro 05-19→06-19 $20 (cancelado, sin factura jun); codex Plus
      04-02→05-02 $20 y 05-02→06-02 $20 (Free después); gemini-cli Google
      AI Pro 2025-12-03→2026-06-03 $19.99/mes; ninguna entrada con `end`
      null (Free/cancelado = ausencia de suscripción)
- [x] `scripts/usage-tracker.py`: `_FALLBACK_SUBSCRIPTIONS` alineado al
      config (TestConsistenciaConTracker)
- [x] Tests de calendario actualizados (`test_fpa_config.py`,
      `test_tracker.py`, `test_fpa_f4.py`) y goldens regenerados
      (REGEN_GOLDEN=1, diffs revisados: solo cargas del calendario)
- [x] Forecast: sin suscripción activa al cierre → plan default "sin
      suscripción" (fee $0) + planes del calendario como escenarios
      (`viz-fpa.py build_forecast`); paridad JS/Python aislada (reload en
      tests de paridad que mutan la página)

## 3. Dashboard consume el ledger (cash cost *reported*)

- [ ] `viz-fpa.py`: cargar `data/charges.json`; cash mensual/por proveedor
      del ledger (kinds subscription|credits|refund), tag *reported* en
      toda cifra del ledger
- [ ] Proveedor sin facturas en el periodo → "n/a" con razón (FPA-008)
- [ ] Reconciliación FPA-082: comparar cash real (ledger) vs cargas
      implícitas del calendario; evidencia con ambos montos
- [ ] Actualizar `data/fpa-dashboard.html` regenerado con el calendario
      corregido y el cash del ledger
- [ ] README/docs: cifras de cash citadas pasan a venir del ledger
      (`--check-docs`)

## 4. Validación

- [x] `openspec validate add-real-charges --strict`
- [x] Suite completa en verde (`pytest tests/ --ignore=tests/test_viz.py`
      + `test_viz.py`)
