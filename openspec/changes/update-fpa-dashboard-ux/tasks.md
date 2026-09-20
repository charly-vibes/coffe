# Tasks — update-fpa-dashboard-ux

## Fase 1 — Navegación de vistas (D1)

- [ ] 1.1 Mover el toggle `body[data-view=…]` del media query <600px a la
      regla base en `viz-fpa.py` (CSS); verificar que el JS de tabs ya
      setea `data-view`, `aria-current` y el parámetro `view` (share-URL)
      a todo ancho; añadir `@media print { .fpa-view { display:block } }`
      para que la impresión incluya todas las vistas
- [ ] 1.2 Smoke Playwright: a 1280×900, click en "Hábitos" deja solo esa
      vista visible y la altura de página < 2 viewports; con `#habits` la
      vista activa al cargar es Habits

## Fase 2 — Grillas (D2)

- [ ] 2.1 Consolidar en `site_theme.py` tokens de estructura: contenedor
      existente (960px, sin widar), `.cards-grid` dedicada, fila de CTAs,
      anatomía de card
- [ ] 2.2 En `render_html()`: envolver los cards en `.cards-grid` (fuera
      quedan marginalia, headings y CTAs — hoy son grid items de `#summary`,
      root cause del layout roto); CTAs como fila compacta ≤64px;
      marginalia como strip bajo el header de cada vista
- [ ] 2.3 Smoke: a 1280px los KPI cards renderizan en ≥3 columnas y el grid
      no contiene items no-card

## Fase 3 — Banda KPI única (D3)

- [ ] 3.1 Eliminar `headline_card()` y su bloque en Summary; la
      interpretación de una línea pasa al contexto del KPI card
- [ ] 3.2 Test: cada cifra KPI aparece en exactamente un card del primer
      viewport de Summary (los claims quedan fuera del check — sus cifras
      pueden coincidir legítimamente con un KPI)

## Fase 4 — Jerarquía tipográfica (D4)

- [ ] 4.1 Mover "FPA-\d\d\d" del cuerpo visible a `title`/footnotes en los
      renderizadores de sección (parrafos `fig(...)`, captions, notas)
- [ ] 4.2 Verificar `viz_fpa_guide.py` y `--check-docs` siguen resolviendo
      los IDs (correr `python3 scripts/viz-fpa.py --check-docs` verde)
- [ ] 4.3 Test: regex sobre texto visible sin matches "FPA-\d\d\d"

## Fase 5 — Disclosure y summaries (D5)

- [ ] 5.1 Default open solo en la sección primaria por vista
      (Cost→Presupuesto, Breakdown→Árbol Portfolio, Habits→Heatmap,
      Outlook→Forecast, Data→Data y método); estilar summaries como
      group-box con marcador integrado (site_theme)
- [ ] 5.2 Añadir `data-tree` a las secciones que hoy no lo tienen (budget,
      bridge, forecast, alerts, reconciliation, plan-economy, weekly,
      pareto…): la serialización/restauración del share-URL es automática
      (shareUrl() ya serializa todo `details[data-tree]`), cero JS nuevo
- [ ] 5.3 Smoke: sin marcador huérfano (ningún nodo de texto "▼" fuera de
      un summary); summaries colapsados con target ≥44px

## Fase 6 — Bridge con selector (D6)

- [ ] 6.1 Emitir waterfalls como `<template data-bridge-month>` + `<select>`;
      meses sin mix fuera del selector; "Descargar SVG" sobre el visible
- [ ] 6.2 Test: exactamente un waterfall visible; identidad Volume+Mix+Rate
      sigue verde por mes (golden existente); con ningún mes con mix, la
      sección muestra n/a con la razón (sin selector vacío)

## Fase 7 — Regeneración y calidad

- [ ] 7.1 Regenerar `data/fpa-dashboard.html` y correr suite completa:
      `python3 tests/test_tracker.py`, `python3 tests/test_viz.py`,
      `--check-docs`, determinismo doble corrida
- [ ] 7.2 Screenshots de verificación (1280 y 390) de las 6 vistas dentro
      de la carpeta del change; revisar que los 8 hallazgos del diagnóstico
      quedan cerrados visiblemente
- [ ] 7.3 Actualizar README (sección del dashboard) si cambia algo documentado
