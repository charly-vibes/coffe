# Change: Añadir dashboard FP&A (`viz-fpa.py`) según spec EARS FPA

## Why

El review rule-of-5 del dashboard actual (`viz-dashboard.py`) destapó hallazgos
estructurales (resumen ejecutivo vacío, claims sin soporte, numeración de figuras
duplicada, captions solo-hover, idiomas mezclados, sin CTA ni export). La spec EARS
`fpa-dashboard-ears-spec.md` (v3, ~/Downloads) consolida esos hallazgos en ~100
requisitos (FPA-001…FPA-179) para un nuevo dashboard orientado a finanzas personales
del uso de IA. Copia canónica de la spec dentro del change:
`fpa-dashboard-ears-spec.md`. Cubre: coste efectivo vs cash, KPIs, árboles,
presupuesto/varianza, bridge precio-volumen-mix, forecast, alertas y economía
de suscripción.

## What Changes

- Nueva capacidad **`fpa-dashboard`**: generador stdlib-only `scripts/viz-fpa.py`
  que produce un HTML autocontenido (inline SVG, sin librerías externas) con vistas
  Summary / Cost / Breakdown / Habits / Outlook + sección Data & method.
- Extiende la capacidad **`usage-report`**: el tracker emite datos que el dashboard
  necesita (tokens por modelo, cargas pay-per-token, commits/releases, interacciones
  por kind, share del filtro charly, timezone, métricas de concurrencia).
- Nueva config `config/fpa.json`: taxonomía de proyectos, calendario de suscripciones,
  pricing versionado, presupuestos, umbrales de alertas, modelos premium, horarios,
  CTAs, idioma (complementa `coffe-mbz`).
- Entrega por fases (ver tasks.md); cada fase cierra con sus tests dorados.
- Sin cambios breaking: `viz-dashboard.py` y `viz-gantt.py` siguen existiendo.

## Impact

- Specs afectadas: `fpa-dashboard` (nueva), `usage-report` (emisiones nuevas del tracker)
- Tickets bd: epic `coffe-lat` con hijos `coffe-lat.1`…`coffe-lat.8` (fases 0–7, cadena de deps)
- Código afectado: `scripts/viz-fpa.py` (nuevo), `scripts/usage-tracker.py` (emisiones),
  `config/fpa.json` (nuevo), `specs/usage-report-v3.schema.json` (extensión),
  `tests/test_fpa.py` + fixture dorado (nuevo), `tests/test_viz_fpa.py` (smoke Playwright)
- Pipeline: TDD → ro5u → fix → commit → próximo ticket (por ticket bd)
