# Verificación visual — F7 (coffe-8nx)

Screenshots de verificación del dashboard regenerado (2026-09-20, Chromium
headless vía Playwright): 6 vistas × 1280×900 y 390×844, más
`fpa-bridge-1280.png` (sección Bridge abierta, mes may 26 seleccionado).
Capturadas post-fix del autocierre de `<rect/>` en `_FpaRefMover`
(bug descubierto durante esta verificación: los waterfalls del bridge
renderizaban vacíos porque el post-proceso F4 convertía `<rect … />` en
`<rect …>`, y el parser HTML anidaba los rects SVG sin pintarlos).

## Veredicto por hallazgo del diagnóstico (proposal.md)

| # | Hallazgo | Veredicto | Evidencia |
|---|----------|-----------|-----------|
| 1 | Tabs no cambian de vista en desktop | **CERRADO** — una vista a la vez a 1280px; cada tab activa con `aria-current`, sin apilamiento de las 6 vistas | `fpa-{summary,cost,breakdown,habits,outlook,data}-1280.png` (cada una muestra solo su vista) |
| 2 | Grilla de Summary contaminada por hijos no-card | **CERRADO** — KPI cards en grilla 3×4 sana; marginalia, headings y CTAs fuera de la grilla | `fpa-summary-1280.png` |
| 3 | Cifras duplicadas (headline cards + KPI strip) | **CERRADO** — banda KPI única; "Coste efectivo $3,814.72" y "Coste cash $1,086.73" aparecen una sola vez | `fpa-summary-1280.png` (primer viewport sin duplicados) |
| 4 | CTAs como cajas verticales casi vacías | **CERRADO** — botones compactos en fila ("Exportar CSV", "Descargar SVG") | `fpa-cost-1280.png`, `fpa-bridge-1280.png` |
| 5 | Sin jerarquía tipográfica (FPA-xxx en el cuerpo) | **CERRADO** — IDs fuera del texto visible (van a `title`/caption); cifra primaria destacada, contexto muted (finding-meta, deltas) | `fpa-habits-1280.png` (título-hallazgo + meta muted), `fpa-breakdown-1280.png` |
| 6 | Marcador ▼ huérfano sobre títulos de sección | **CERRADO** — summaries como group-box con marcador integrado (▼/▶ inline antes del título); solo la sección primaria de cada vista abre expandida | `fpa-cost-1280.png` (Presupuesto abierto; Bridge/Alertas colapsados), `fpa-breakdown-1280.png` (Árbol Portfolio abierto; Time/Tool colapsados) |
| 7 | Bridge: un waterfall por mes con marcos $0.00 | **CERRADO** — selector de mes (abr–sep 26), exactamente un waterfall visible, meses sin mix fuera del selector ("Fuera del selector (sin datos de mix): feb 26, mar 26"), sin marcos vacíos | `fpa-bridge-1280.png` |
| 8 | Marginalia dispersa en columna huérfana | **CERRADO** — chips "¿Qué es esto? · N" en strip horizontal bajo el header de cada vista | todas las vistas a 1280 y 390 |

## Mobile (390×844)

Las 6 vistas en `fpa-{vista}-390.png`: tabs envueltas en 2 filas y
funcionales, grillas en 1 columna, sin overflow horizontal, marginalia en
strip, jerarquía conservada.

## Conclusión

Los 8 hallazgos del diagnóstico quedan cerrados visualmente a ambos
anchos. Bug adicional encontrado y corregido durante la evidencia:
autocierre de elementos SVG perdido en el post-proceso F4
(`scripts/viz-fpa.py`, `handle_startendtag`) que dejaba los waterfalls
del bridge sin barras.
