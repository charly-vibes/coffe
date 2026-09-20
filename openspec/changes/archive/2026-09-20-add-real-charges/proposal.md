# Add: cargos reales (ledger de facturas) + corrección del calendario de planes

## Why

El epic coffe-a31 transcriptó las facturas reales de 5 proveedores a
`data/charges.json` (IA $1,356.72 en el ledger). El spec vigente asume que
"el tracker no registra cargas reales" y que el calendario de suscripciones
es Pro Mar-19 → Max Abr-19 → Pro Jun-19: las facturas prueban que eso está
mal (claude fue Max $100 el 19-mar y el 19-abr, Pro $20 el 19-may, sin
factura jun; codex fue ChatGPT Plus $20 el 02-abr y el 02-may, Free después;
gemini-cli pagó Google AI Pro $19.99/mes desde dic-2025). FPA-082 existe
precisamente para reconciliar el calendario asumido contra lo real — y para
eso necesita que el cash cost real venga del ledger, no de una estimación.

## What Changes

- **ADDED** (fpa-dashboard): cash cost = cargos reales del ledger
  (`data/charges.json`), provenance *reported*, solo kinds IA
  `subscription|credits|refund` (api_cycle aporta $0; storage queda fuera
  del cash de IA por decisión de Sasha 2026-09-20). FPA-013 pasa a real
  (créditos claude ene-feb, amp, openrouter).
- **MODIFIED** (fpa-dashboard): la reconciliación (FPA-082) compara cash
  real del ledger vs cargas implícitas del calendario; los fees implícitos
  quedan SOLO para reconciliación y plan economy (FPA-130–133), nunca como
  cash cost. Efectivo + cash jamás se suman (FPA-002, sin cambios).
- **MODIFIED** (fpa-dashboard): economía de suscripción y forecast operan
  sobre el calendario corregido; sin suscripción activa al cierre el plan
  default es "sin suscripción" (fee $0, cash = p2p escalado).
- **MODIFIED** (usage-report): el campo `pay_per_token_charges` del reporte
  sigue siendo *assumed* (el tracker no ve facturas); la fuente de cargos
  reales pasa a ser el ledger `data/charges.json` con contrato propio.
- **Corregido** `config/fpa.json` + fallback del tracker a las facturas:
  claude-cli Max 03-19→04-19 $100, Max 04-19→05-19 $100, Pro 05-19→06-19
  $20 (cancelado); codex Plus 04-02→05-02 $20 y 05-02→06-02 $20; gemini-cli
  Google AI Pro 2025-12-03→2026-06-03 $19.99/mes.

## Impact

- Affected specs: `fpa-dashboard`, `usage-report`
- Affected code: `config/fpa.json`, `scripts/usage-tracker.py` (fallback),
  `scripts/viz-fpa.py` (consumo del ledger — ticket posterior), tests de
  guards del ledger (`tests/test_charges.py`), goldens regenerados
- Compat: el calendario corregido cambia las cargas implícitas (jun = $0
  real vs implícito — exactamente el caso FPA-082); datos de `charges.json`
  ya transcriptos y versionados (5 proveedores, kinds IA)

## Decisions (Sasha 2026-09-20)

- cash cost = cargos reales pagados (provenance *reported*, del ledger)
- fees implícitos del calendario = solo para reconciliación FPA-082 y plan
  economy; jamás sumar efectivo+cash (FPA-002)
- "n/a" con razón, nunca vacío (FPA-008); toda cifra del ledger en el
  dashboard lleva *reported*
