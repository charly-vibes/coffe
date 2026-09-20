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

- [x] `usage-tracker.py` (coffe-a31.2, CRG-F1): cargar `data/charges.json`
      (guardas loud); emitir `charges_real_by_month` por provider (solo kinds
      IA), `charges_reconciliation_by_month` (real vs fee implícito vs
      efectivo — insumo FPA-082) y metadata
      `charges_source`/`charges_total_real`/`charges_provenance`/`charges_reason`
- [x] FPA-013 deja de ser assumed: `pay_per_token_charges` mensual es
      *reported* cuando hay cargas p2p del ledger (créditos/reembolsos);
      *assumed* solo si no; fees implícitos nunca mezclados
- [x] Divergencia 611.62 vs 381.62 explicada y unificada:
      `metadata.cost_total_real` = suma mensual; parte tracker separada
      (`cost_real_total_tracker`, `cost_real_tracker` mensual) de los fees
      implícitos (`subscription_fees_by_month`) — sin doble conteo
- [x] Schema aditivo (`specs/usage-report-v3.schema.json`) + golden
      regenerado (solo emisiones nuevas y las 4 líneas del p2p/cost_total_real)
- [x] `viz-fpa.py`: cash mensual/por proveedor del ledger, tag *reported* en
      toda cifra del ledger (coffe-a31.3, CRG-F2): cost_cash mensual =
      cargos del ledger (refund descuenta); fallback tracker *assumed* con
      razón si el reporte no trae el ledger; KPIs/árboles/budget/forecast/
      plan-economy usan el mismo cash (FPA-031 cambia de semántica)
- [x] Proveedor sin facturas en el periodo → "n/a" con razón (FPA-008)
      en el dashboard (la serie ya emite 0.0 + razón en charges_reason)
- [x] Reconciliación FPA-082 en el dashboard: sección cash real por
      proveedor + matriz por tool y mes (real pagado vs fee implícito vs
      efectivo estimado); alerta compara cash real del ledger vs fees del
      calendario + p2p reportado (fallback al chequeo previo sin ledger)
- [x] FPA-081 sobre el calendario corregido: mes con uso de Claude sin
      plan que lo cubra → alerta high (jun-sep 2026)
- [x] Actualizar `data/fpa-dashboard.html` regenerado con el calendario
      corregido y el cash del ledger
- [x] README/docs: cifra nueva `Cash real (ledger)` en check-docs (n/a
      mientras el reporte commiteado no traiga el ledger — CRG-F3/
      coffe-a31.4); `Costo real` queda acoplado a la suma mensual

## 4. Validación

- [x] `openspec validate add-real-charges --strict`
- [x] Suite completa en verde (`pytest tests/ --ignore=tests/test_viz.py`
      + `test_viz.py`)
