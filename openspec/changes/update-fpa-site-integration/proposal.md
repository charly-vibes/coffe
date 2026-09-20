# Change: Integrar el dashboard FP&A al sitio (tema visual, nombre llano, guía a 4 niveles, consolidación)

## Why

El dashboard FP&A (`data/fpa-dashboard.html`, generado por `scripts/viz-fpa.py`) quedó
publicado pero desalineado del resto del sitio en cuatro sentidos:

1. **Look & feel**: usa un tema propio cálido (`--bg:#f4f2ec`, system-ui, modo
   claro/oscuro) mientras el resto del sitio (`viz-dashboard.py`, `viz-index.py`)
   usa el tema "90s corporate" (silver `#c0c0c0`, acentos granate `#800000` /
   navy `#000080`, sombras duras `4px 4px 0`, Arial, terminales Courier).
2. **Nombre con jerga**: el label público "FP&A" presuntuiza conocimiento que la
   mayoría de los lectores no tiene (finance-speak corporativo). El sitio es en
   español y los labels públicos deben usar lenguaje llano.
3. **Superposición con dashboards anteriores**: conviven `dashboard.html`
   (insights: tendencia mensual, coste por herramienta, top proyectos, heatmap,
   skills, comandos, sesiones, timeline) y `fpa-dashboard.html` (que cubre todo eso
   con más profundidad). Nadie visitó el de insights: se elimina en vez de
   mantener el par sin jerarquía.
4. **Falta de documentación explicativa**: los 19 análisis del dashboard solo se
   entienden leyendo la spec; existe una guía a 4 niveles
   (`~/Downloads/fpa-analyses-guide-4-levels.md`: ELI5 → Everyday → Practitioner →
   Expert) que no está en el repo ni en el sitio. Además, la guía fue escrita
   contra la spec y un snapshot de README: sus afirmaciones necesitan **grounding
   contra la implementación real** antes de publicarse como verdad.

## What Changes

- **Tema visual unificado**: `viz-fpa.py` adopta los tokens del tema 90s corporate
  del sitio (misma paleta, tipografía, sombras duras, estilo de paneles/terminales),
  manteniendo los requisitos de accesibilidad existentes (FPA-150…179). Los tokens
  se comparten con `viz-dashboard.py`/`viz-index.py` desde un módulo común
  (`scripts/site-theme.py`).
- **Nombre público llano**: ningún label visible del sitio menciona "FP&A"; el
  dashboard usa un nombre canónico en español llano (propuesta: "Uso y costos de
  IA"), definido en un único lugar de config y consumido por índice, dashboard,
  guía y README. Los IDs internos (`fpa_*`, FPA-xxx, `fpa-dashboard.html`) no
  cambian.
- **Guía de análisis a 4 niveles, en español y con grounding**: la guía se
  traduce al español, se committea como fuente en el repo
  (`docs/fpa-analyses-guide.md`), se hace un pase de verificación de cada
  afirmación contra el código real (formulas, umbrales, defaults — corregir el
  texto de la guía, nunca el código, para hacerlo decir lo que el código hace),
  y el generador la expone en dos formas:
  - **Marginalia por análisis con progressive disclosure**: en cada vista (y en el
    Gantt), un affordance compacto (chip/botón de información) con tooltip del
    teaser ELI5; al seleccionarlo se expande la nota in situ (niveles 2–3 +
    enlaces a la guía completa y a los IDs FPA-xxx).
  - **Guía completa** en `data/fpa-guide.html` (autocontenida, mismo tema), enlazada
    desde el dashboard, el Gantt y el índice.
- **Consolidación de dashboards**: el FPA pasa a ser el dashboard único. El
  dashboard de insights (`dashboard.html` + `viz-dashboard.py`) se **elimina** del
  repo y del deploy (nadie lo visitó; todo su contenido está cubierto por el FPA).
  El Gantt se conserva y recibe marginalia para los análisis que le corresponden
  (multitasking, ritmo).
- **README y check-docs** actualizados a la nueva jerarquía y al nombre llano.

## Impact

- Affected specs: `fpa-dashboard` (4 requirements nuevos: identidad visual,
  nomenclatura pública llana, guía con marginalia y grounding, consolidación)
- Affected code: `scripts/viz-fpa.py` (tema + nombre + marginalia), nuevo
  `scripts/site-theme.py` + `scripts/viz_fpa_guide.py`, `scripts/viz-gantt.py`
  (marginalia), `scripts/viz-index.py` (labels), `viz-dashboard.py` +
  `data/dashboard.html` **eliminados**, `docs/fpa-analyses-guide.md` (nuevo, es),
  `data/fpa-guide.html` + regeneración de los HTML restantes, `README.md`,
  `config/fpa.json` (nombre canónico), `tests/` + goldens.
- **BREAKING**: se elimina `data/dashboard.html` del sitio (sin visitas registradas;
  los enlaces externos no se conocen — riesgo aceptado por decisión de Sasha).
