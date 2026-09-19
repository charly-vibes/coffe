## Context

Spec EARS v3 (~100 requisitos FPA-001…FPA-179, con sección de trazabilidad
hallazgo→requisito). Dashboard de análisis financiero sobre `data/usage_report_v3.json`.
El repo ya tiene: tracker con `aggregate()` pura, schema v3, dos viz scripts,
tests dorados y smoke Playwright. Change `add-usage-report-spec` casi cerrado (16/17).

## Goals / Non-Goals

- Goals: dashboard FP&A stdlib-only, un solo HTML, fases entregables, maths
  verificadas (FME, roll-up, identidad del bridge), UX accesible y exportable.
- Non-Goals: no reemplazar `viz-dashboard.py` (vive en paralelo); no backend ni
  servidor; no librerías de charts; no resolver el flip de Pages (`coffe-3yt`).

## Decisions

- **Un generador, un archivo**: `scripts/viz-fpa.py` stdlib-only, inline SVG
  (FPA-001, FPA-145). Alternativa (Chart.js) descartada: rompe la convención del
  repo y la propia spec la prohíbe en la práctica (FPA-145).
- **Config en un solo JSON**: `config/fpa.json` con taxonomía (FPA-018),
  suscripciones fechadas (FPA-015), pricing versionado por fecha (FPA-016),
  presupuestos y mes de inicio (FPA-050/051), umbrales de alertas (FPA-088),
  modelos premium (FPA-037), horarios laborales (FPA-111), CTAs (FPA-168),
  idioma (FPA-162), elementos retro opcionales (FPA-178). El generador falla si
  un CTA configurado está vacío (FPA-168).
- **Interactividad client-side**: datos embebidos como JSON + JS vanilla; el
  selector de periodo recompute sin reload (FPA-026/056/077), share-URL
  (FPA-170/171) y export CSV/SVG (FPA-169) sin dependencias.
- **Provenance como tipo**: cada figura lleva tag *reported*/*assumed* (FPA-003)
  via envoltorio de render, no a mano.
- **Maths puras en Python**: FME, varianza, bridge PVM, forecast y break-even se
  computan en el generador (no en JS) y se emiten pre-calculados para el golden
  test; JS solo re-escala/ordena. La identidad del bridge (FPA-065) y el roll-up
  (FPA-025) se verifican en Python (FPA-101).
- **Fases**: 8 fases (0–7, ver tasks.md) mapeadas a tickets bd; cada fase es
  cerrable y testable por separado.

## Risks / Trade-offs

- Alcance (~100 reqs) → fases cortas con tests dorados por fase; TDD por ticket.
- Meses parciales (FME, pro-rating, daily rates) → fixture dorado con meses
  parciales desde la fase 1 (FPA-102).
- Doble coste (efectivo vs cash) nunca se suma (FPA-002) → tests que fallen si
  algún total los suma.
- Timezone del tracker ausente → marcar vistas hora/día como unverified (FPA-142).
- Definición de "interaction" sin confirmar (FPA-140) → exigir emisión por kind
  antes de reportar totales sin desglose.

## Migration Plan

Por fases: cada fase añade vistas/secciones al HTML generado sin romper las
anteriores. `viz-fpa.py` es aditivo; no toca outputs existentes. Rollback =
borrar el script y los artefactos nuevos.

## Open Questions

Resueltas el 2026-09-20 con Sasha:

1. **¿Presupuesto de coste efectivo trackeado?** No — no se trackea de verdad.
   FPA-050 sigue exigiendo aceptarlo por config, pero se trata como informativo
   (soft): el presupuesto activo es el de cash cost; el de efectivo se muestra
   sin semántica de gestión.
2. **¿Cargas pay-per-token reales?** No — el tracker no registra cargas reales
   (Codex, OpenRouter). FPA-013: emitir el campo igualmente, con valor
   ausente/cero y provenance *assumed*; el cash cost efectivo = solo
   suscripciones. La alerta de reconciliación (FPA-082) sigue aplicando contra
   las cargas implícitas del calendario.
3. **¿Taxonomía?** Inferida de los nombres de repo. FPA-018: `config/fpa.json`
   provee reglas de inferencia (patrones nombre→categoría) + overrides a mano;
   lo no inferido cae en "Unclassified".
4. **¿Horarios laborales?** Cualquiera vale — se usa el default de la spec:
   Mon–Fri 09:00–18:00, configurable (FPA-111).
5. **¿Estilo retro?** Sí, se conserva → FPA-178 aplica con todo: confinado a
   header/footer, opcional por config (default on), sin animación bajo
   `prefers-reduced-motion`, contraste ≥ 4.5:1.
6. **¿URLs de CTAs?** Ok con los targets obvios: rutas relativas a los
   artefactos publicados (`data/gantt-multitasking.html`,
   `data/usage_report_v3.json`), URL del repo y URL de la serie. Valores
   finales se fijan en config al reclamar F6 — FPA-168 exige que ninguno esté
   vacío.
7. **¿Idioma?** Español → config `language: "es"` (FPA-162), única lengua de
   interfaz y texto generado.
