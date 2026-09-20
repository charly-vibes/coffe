# Design — update-fpa-dashboard-ux

## Decisiones

### D1: una vista a la vez a todo ancho (no solo mobile)

Hoy el toggle de vistas vive en un `@media (max-width:599px)`. Se mueve a la
regla base: `body[data-view=…] #…` muestra la activa, las demás `display:none`.
Esto revierte deliberadamente la parte desktop de FPA-152 (comentario en
viz-fpa.py ~4044: "en desktop las vistas van en secuencia y el ancla navega
in-page"). El deep-link usa el contrato vigente de share-URL por query
params (`?view=…`, viz-fpa.py ~4122); no hay ni habrá hash. Con JS
deshabilitado, los anchors `href="#…"` de las tabs siguen scrolleando a la
vista (fallback degradado). Para impresión: `@media print` re-muestra todas
las vistas. Coste: cero datos nuevos; solo CSS + el JS de tabs ya existente.

### D2: grillas como tokens de estructura en site_theme.py

El contenedor ya existe (`main { max-width: 960px; margin: 0 auto; }`):
se conserva (sin widar; decisión explícita, no side effect) y se consolida
en `site_theme.py` junto con reglas compartidas de estructura (no color):
grilla de KPI cards dedicada (`.cards-grid`, `repeat(auto-fit,
minmax(240px, 1fr))`, en un div propio — no como hijos de la sección), fila
de CTAs (`flex; gap`), y la anatomía de card (`.kpi-card { … }`). Root cause
del layout roto: la marginalia, los headings y el div de CTAs son hijos
directos de `#summary` (que es `display:grid`), así que se vuelven grid
items; la corrección es envolver los cards en `.cards-grid` y sacar
marginalia/CTAs de la grilla. Ningún token de color/tipografía cambia.

### D3: banda KPI única — desaparecen las headline cards

Las headline cards (resumen ejecutivo, requisito "3–5 cifras headline") se
fusionan con el KPI strip: el KPI strip ES el resumen ejecutivo. La
interpretación de una línea por cifra (requisito vigente con fallback n/a)
pasa a ser la línea de contexto del card. Los claims narrativos se mantienen
como texto sobre la banda y conservan sus cifras: el test anti-duplicados
aplica solo a cards, no al texto de claims (la métrica de un claim puede
coincidir legítimamente con un KPI). La spec delta MODIFICA también el
requisito "resumen ejecutivo con fallback n/a" (si no, el spec archivado
se auto-contradice). El bloque de Summary en `render_html()` cambia y se
elimina `headline_card()`.

### D4: IDs FPA-xxx fuera del cuerpo visible

Patrón: el párrafo visible pierde "(FPA-xxx)"; el ID viaja a `title` del
elemento contenedor o a una lista de footnotes al pie de la sección
(`<ol class="fn">`). Los IDs siguen presentes en el DOM, solo dejan de ser
ruido visual. Riesgo bajo verificado: ningún test ni check assertion los
FPA-ids del texto visible del dashboard (test_viz.py solo los menciona en
comentarios; el grounding de la guía parsea el markdown de la guía, no el
HTML); los chips de marginalia (que sí llevan ids) no se tocan. Se corre
`--check-docs` como verificación.

### D5: disclosure por defecto por vista

Sección primaria por vista (la que responde la pregunta):
Summary→KPI band (no es details), Cost→Presupuesto y varianza,
Breakdown→Árbol Portfolio, Habits→Heatmap, Outlook→Forecast,
Data→Data y método. El resto colapsado. El estado abierto/cerrado ya se
serializa: `shareUrl()` serializa TODO `details[data-tree]` (open/closed,
viz-fpa.py ~4124) y lo restaura al cargar (~4145). La tarea 5.2 es añadir
`data-tree` a las secciones que hoy no lo tienen (budget, bridge, forecast,
alerts, reconciliation, plan-economy, weekly, pareto…); cero JS nuevo.

### D6: bridge con selector de mes

Python pre-calcula los waterfalls de todos los meses (igual que hoy) pero los
emite como `<template data-bridge-month="YYYY-MM">`; un `<select>` elige cuál
se monta. Meses sin datos de mix no emiten template ni opción. El
`Descargar SVG` opera sobre el waterfall visible. Determinismo intacto.

## Riesgos

- **Golden tests**: los cambios de estructura tocan el HTML golden de smoke;
  se regeneran y revisan a mano.
- **`--check-docs` y grounding de la guía**: los FPA-ids dejan el cuerpo
  visible; el parser de la guía y los checks que grepan texto visible deben
  apuntar a atributos/footnotes (verificado en `viz_fpa_guide.py`).
- **A11y**: tabs ya son `role=tab`; se mantiene focus-visible y targets ≥44px
  en los summaries colapsados (regla compartida en site_theme).
