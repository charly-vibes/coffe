# Proposal: update-fpa-dashboard-ux

## Why

El Dashboard principal (`data/fpa-dashboard.html`) es funcional pero la
presentación de la información no es clara. Un pase de diagnóstico con
screenshots reales (1280×900, Chromium) sobre el HTML generado encontró
8 problemas de estructura de información, ninguno de ellos del tema
visual "Corporate Infographics™ 1996" (que funciona y se conserva):

1. **Las tabs no cambian de vista en desktop**: el CSS de una-vista-a-la-vez
   solo aplica bajo `max-width:599px` (`viz-fpa.py` ~2942). En 1280px las 6
   vistas se apilan en una página de ~20,600px de alto; las tabs solo
   scrollean. El usuario no tiene navegación real.
2. **La grilla de Summary está contaminada por hijos no-card**: `#summary`
   es `display:grid` (auto-fit, viz-fpa.py ~2844) y la marginalia, los
   headings y el div de CTAs son hijos directos de la sección, así que se
   convierten en grid items y fragmentan el layout (chips en una columna
   izquierda, CTAs como cajas verticales, cards aplastados). El contenedor
   `main { max-width: 960px }` ya existe; el problema es la grilla, no el
   contenedor.
3. **Cifras duplicadas en la primera pantalla**: "Coste efectivo $3,814.72"
   y "Coste cash $1,086.73" aparecen como headline cards Y otra vez como
   KPI cards.
4. **CTAs renderizan como cajas verticales casi vacías** ("Leer la serie",
   "Explorar el Gantt"…): parecen roturas, no botones.
5. **Sin jerarquía tipográfica**: los IDs FPA-xxx intercalados en el cuerpo
   del texto, deltas, tags de provenance y notas de método compiten al mismo
   peso visual; no se distingue cifra primaria de contexto.
6. **Marcador ▼ huérfano**: el marker nativo de `<details>` flota solo en su
   propia línea encima de cada título de sección.
7. **El bridge renderiza un waterfall por mes** con marcos casi vacíos
   ($0.00) para meses sin datos de mix: cientos de px desperdiciados.
8. **Marginalia dispersa**: los chips "¿Qué es esto? · N" flotan en una
   columna izquierda huérfana en vez de un strip consistente por vista.

## What Changes

- **Navegación de vistas real en todo viewport**: una vista a la vez a
  cualquier ancho (no solo mobile), tabs persistentes, deep-link por hash y
  share-URL sin cambios de contrato.
- **Grillas sanas**: contenedor existente (960px) conservado; los KPI
  cards pasan a un div `.cards-grid` propio (≥2 columnas en tablet, 3–4 en
  desktop), fila de CTAs compacta, marginalia como strip consistente bajo
  el header de cada vista (fuera de las grillas de cards).
- **Una sola banda de KPIs**: se elimina la duplicación headline-cards ↔
  KPI strip; los hallazgos headline pasan a texto narrativo + la banda KPI
  única.
- **Jerarquía tipográfica estandarizada**: anatomía de card (label → cifra
  → delta → contexto), IDs FPA-xxx fuera del cuerpo visible (van a
  `title`/footnotes), texto secundario muted.
- **Disclosure por defecto**: por vista, solo la sección primaria abre
  expandida; el resto colapsado. Los `<summary>` se estilizan como
  group-box 90s con el marcador integrado (no ▼ huérfano).
- **Bridge con selector de mes** (small multiples → un waterfall a la vez)
  en vez de una figura por mes; meses sin datos no renderizan marcos vacíos.
- **Tokens del tema intactos**: la paleta/tipografía de
  `scripts/site_theme.py` no cambia; se añaden reglas de layout compartidas
  (contenedor, grilla de cards) como tokens de estructura del mismo módulo.

## Capabilities

### Modified
- `fpa-dashboard`: los requisitos de vistas/CTAs/layout se actualizan;
  se añaden requisitos de jerarquía, disclosure y bridge; los requisitos
  de datos (provenance, roll-up, ledger, etc.) NO cambian.

## Impact

- `scripts/viz-fpa.py`: CSS + estructura del body de `render_html()` y de
  los renderizadores de sección; JS de tabs pasa a funcionar a todo ancho.
- `scripts/site_theme.py`: se consolidan tokens de estructura (contenedor
  existente, grilla de cards, anatomía de card); ningún token de
  color/tipografía cambia.
- `tests/test_viz.py`: smoke Playwright extendido (tab switching a 1280px,
  sin cifras duplicadas en el primer viewport, sin ▼ huérfanos).
- `data/fpa-dashboard.html` y `data/fpa-guide.html` (marginalia compartida)
  se regeneran; sin cambios de datos ni del reporte JSON.
