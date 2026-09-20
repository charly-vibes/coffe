# Design: Integrar el dashboard FP&A al sitio

## Context

- El sitio ya tiene una identidad visual estable: el tema "90s corporate" de
  `viz-dashboard.py` (líneas ~152–217): `--bg:#c0c0c0; --panel:#ffffff; --accent:#800000;
  --accent2/navy:#000080; --good:#008080; --yellow:#ffff00`, sombra dura
  `4px 4px 0 #404040`, `font-family: Arial`, terminales `Courier New` verde-sobre-negro.
- `viz-fpa.py` (4294 líneas) usa otro tema (crema `#f4f2ec` / carbón, system-ui,
  modo claro/oscuro) definido en el `<style>` que emite.
- El FPA está organizado en 5 vistas por pregunta (Summary, Cost, Breakdown,
  Habits, Outlook) + "Data & method" colapsado (FPA-090/091); cada figura ya lleva
  provenance (`reported/assumed`) y numeración automática.
- La guía a 4 niveles (19 análisis, 170 líneas) cubre los análisis que el dashboard
  renderiza; sus IDs FPA-xxx cruzan con la spec. Pero fue escrita contra la spec y
  un snapshot de README del 10 de junio: mezcla números hoy desactualizados
  (p.ej. $65.58 de cash cuando el ledger real dice $1,086.73; leverage ~48× cuando
  el real es ≈3.5×) y fórmulas que hay que verificar contra el código.
- Idioma del sitio: es; la guía está en inglés.
- El dashboard de insights (`dashboard.html`) no recibió visitas; su contenido
  (tendencia mensual, coste por herramienta, top proyectos, heatmap, skills,
  comandos, sesiones, timeline) está cubierto por las 5 vistas del FPA.

## Goals / Non-Goals

- Goals:
  - Que el FPA se vea como parte del mismo sitio (tema compartido, no "parecido").
  - Que los labels públicos hablen español llano (cero jerga corporativa).
  - Que un lector nuevo entienda cada análisis sin salir del dashboard, con
    progressive disclosure (tooltip → expandir).
  - Que la guía publicada diga la verdad del código, no la de un snapshot viejo.
- Non-Goals:
  - Reescribir la matemática del FPA ni el modelo de datos (usage-report intacto).
  - Portar el Gantt al FPA (queda como viz única, ahora con marginalia).
  - Renombrar artefactos/URLs (`fpa-dashboard.html`, IDs FPA-xxx, `fpa_*`) —
    internos, no públicos.
  - Dark mode en el tema 90s corporate (el resto del sitio no lo tiene).

## Decisions

### D1 — Fuente única del tema: `scripts/site-theme.py`

Los tokens del tema (`:root` palette, reglas de panel/sombra/tipografía/terminal)
viven en un módulo `scripts/site-theme.py` (dicts/strings) que los generadores
(`viz-fpa.py`, `viz-index.py`, `viz-gantt.py`) interpolan en su `<style>`.
Rationale: copiar el CSS a mano garantiza divergencia futura; un módulo stdlib es
el patrón que ya usa el repo (fpa_config.py). El `<style>` de `viz-dashboard.py`
es la fuente de verdad inicial: se extrae, no se rediseña. Se conservan los
nombres de variables existentes (`--navy`, `--yellow`) para minimizar el diff.

### D2 — El FPA pierde dark mode y gana el tema del sitio

El modo claro/oscuro del FPA se elimina; el tema compartido es de un solo modo.
Las reglas de accesibilidad existentes (targets 44px, no solo-color, tabular-nums
USD) se conservan: se adaptan al nuevo tema, no se descartan.

### D3 — Nombre canónico llano, definido una vez

El label público se define en `config/fpa.json` (clave nueva, p.ej.
`"site_name": "Uso y costos de IA"`) y la consumen índice, dashboard, guía
generada, Gantt y README. **Cero apariciones de "FP&A" en labels, headers, tabs,
titles o textos visibles.** Candidatos: "Uso y costos de IA" (recomendado),
"Panel de uso y costos", "Dashboard de uso de IA" — a confirmar con Sasha.
Los nombres de archivo, IDs FPA-xxx y variables `fpa_*` quedan intactos.

### D4 — Guía en español, versionada, con pase de grounding

- Se traduce la guía al español y se committea como `docs/fpa-analyses-guide.md`
  (fuente de verdad del contenido; el original en inglés queda en Downloads,
  fuera del repo).
- **Pase de grounding (obligatorio antes de publicar)**: cada afirmación
  practitioner/expert de la guía se verifica contra la implementación real
  (`viz-fpa.py`, `usage-tracker.py`, `config/fpa.json`):
  - Fórmulas (FME, bridge PVM, cache-hit rate, break-even) contra las funciones
    puras que las computan.
  - Umbrales y defaults (30 días dormancy, 25× utilization, mix premium 3 meses,
    tolerancia de reconciliación) contra `config/fpa.json` y sus validadores.
  - Cifras ilustrativas reemplazadas o re-etiquetadas: o se citan cifras actuales
    del JSON (derivadas en generación), o se elimina el número y se deja la idea.
    La guía ya no es "snapshot del 10 de junio".
- Regla de dirección: si la guía y el código discrepan, **se corrige el texto de
  la guía** (la guía documenta, no especifica). Nunca se cambia el código para
  hacer que un número de la guía sea verdad.
- El parser stdlib (`scripts/viz_fpa_guide.py`) parsea el markdown español
  (headings `##`/`###`, bloques por nivel) y emite `data/fpa-guide.html`
  (autocontenida, tema del sitio) + los fragmentos de marginalia.

### D5 — Marginalia con progressive disclosure: tooltip primero, expandir al seleccionar

- En cada una de las 5 vistas del FPA y en el Gantt, los análisis mapeados se
  anuncian con un **affordance compacto**: un chip/botón "¿Qué es esto?" (icono
  de información + texto corto), no un bloque de texto visible.
- **Tooltip nativo** (`title` + contenido en el chip) con el teaser del nivel 1
  (ELI5) — costo cero de espacio en la vista.
- **Al seleccionar** (click/tap/Enter — es un `<button>` real, no un div), la
  nota se expande in situ: nivel 2 completo, nivel 3 colapsado dentro, y enlace
  "Guía completa → análisis N" (`fpa-guide.html#analisis-N`).
- En touch (sin hover), el chip funciona igual: tap = expandir. El tooltip es
  enhancement, no requisito de lectura.
- Evaluación tooltip-vs-texto: el tooltip gana porque las vistas ya son densas
  (KPI strip de 12, árboles); un bloque visible por vista competiría con el
  contenido que explica. Si el chip resultara invisible en uso real (hallazgo
  del smoke/deploy), se escala a la variante "teaser de una línea visible" — se
  decide con el smoke Playwright a 390×844, no a priori.

### D6 — Mapeo análisis→vista, incluido el Gantt

Tabla de mapeo declarada en `viz_fpa_guide.py`, anclada a los IDs FPA-xxx del
propio texto de la guía (p.ej. análisis 8 multitasking → vista Habits **y** Gantt;
análisis 9 ritmo → Habits + Gantt). Cobertura verificada por test: cada análisis
en ≥1 superficie (vista o Gantt). El Gantt integra el mismo affordance de chip
expansible vía módulo compartido.

### D7 — Consolidación: eliminar el dashboard de insights

- Se **eliminan** `data/dashboard.html` y `scripts/viz-dashboard.py` del repo y
  del deploy (git history los preserva). Justificación: cero visitas y cobertura
  total por el FPA; congelarlo con banner solo aplaza la poda.
- `viz-index.py`: el FPA queda como "Dashboard principal" con el nombre llano;
  la entrada del dashboard de insights desaparece.
- README: filas del dashboard de insights eliminadas; jerarquía documentada.
- Gantt: se conserva (visualización única de su tipo) y pasa a usar
  `site-theme.py` para eliminar el último tema divergente del sitio.

### D8 — Checks

- Paridad de tema: test que corre los generadores y aserta que los tokens
  `:root` emitidos provienen de `site-theme.py` (idénticos entre HTMLs).
- Guía: test del parser (19 análisis × 4 niveles en el markdown español), test
  de cobertura del mapeo, test de enlaces a `fpa-guide.html`.
- Grounding: test de invariantes que cruzan guía↔código para los umbrales
  estables (dormancy 30, 25×, premium 3 meses): el valor en `config`/defaults ==
  el valor citado en la guía (los dos leídos de sus fuentes reales).
- Nomenclatura: test que falla si un label visible generado contiene "FP&A"
  (regex sobre los HTMLs salientes).
- Playwright smoke (`tests/test_viz.py`): `fpa-guide.html` sin pageerrors;
  computed styles del FPA y del Gantt (font-family/--bg del tema); interacción
  chip→expansión a 390×844.
- Goldens regenerados por el cambio de CSS + labels (diff esperado: style/labels).

## Risks / Trade-offs

- Tema 90s corporate sin modo oscuro → los usuarios de dark mode pierden la
  preferencia. Mitigación: contraste AA verificado sobre silver/granate/navy.
- Eliminar `dashboard.html` rompe cualquier enlace externo desconocido → riesgo
  aceptado explícitamente por Sasha (cero visitas); git history conserva el HTML.
- La traducción puede introducir errores propios → el pase de grounding se hace
  sobre la versión en español, verificando afirmación por afirmación.
- Chips con tooltip pueden pasar desapercibidos → decisión de escalar a teaser
  visible basada en evidencia del smoke (D5), no en gusto.
- `viz-fpa.py` ya pesa 4.3k líneas → el parser y el mapeo viven en módulo propio
  `viz_fpa_guide.py`.

## Migration Plan

1. Commit de la guía traducida + pase de grounding (afirmación por afirmación).
2. Extraer tema a `site-theme.py` y migrar generadores (FPA y Gantt últimos,
   juntos con los labels llanos).
3. Parser + `fpa-guide.html` + marginalia (FPA + Gantt).
4. Consolidación: eliminar dashboard de insights + índice + README.
5. Regen de HTMLs, goldens, suite completa + Playwright, deploy.

Rollback: revert de la serie de commits; ningún dato cambia.

## Open Questions

- Q3' — ¿Nombre canónico en `config/fpa.json`? Propuesta: **"Uso y costos de
  IA"** (label del dashboard: "Dashboard de uso y costos de IA"). Alternativas:
  "Panel de uso y costos de IA", "Uso y costo de IA" (solo título). Decisión de
  una palabra, no bloquea el resto.
