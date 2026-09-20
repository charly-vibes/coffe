# Delta: fpa-dashboard

## ADDED Requirements

### Requirement: identidad visual del sitio

El Dashboard SHALL (debe) usar el mismo tema visual que el resto del sitio: los
tokens del tema "90s corporate" (bg silver, acentos granate y navy, good teal,
sombra dura, Arial, terminales Courier) provistos por un módulo de tema compartido
(`scripts/site-theme.py`) del que también toman su estilo los demás generadores
(`viz-index.py`, `viz-gantt.py`). El tema compartido SHALL ser la única fuente de
definición de esos tokens: ningún generador duplica definiciones divergentes. Los
requisitos de accesibilidad previos (targets táctiles, no solo-color, cifras
tabulares) SHALL seguir cumpliéndose bajo el nuevo tema. El generador SHALL ser
determinista (mismo tema en cada corrida).

#### Scenario: paridad de tokens entre generadores

- **WHEN** se generan `fpa-dashboard.html`, `index.html` y `gantt-multitasking.html`
  en la misma corrida
- **THEN** los tokens `:root` y las reglas compartidas del `<style>` provienen del
  módulo de tema y son idénticos en los tres HTML

#### Scenario: smoke visual del tema

- **WHEN** el smoke de Playwright abre `data/fpa-dashboard.html`
- **THEN** el `font-family` computado y el `background` del body corresponden al
  tema compartido, sin pageerrors

### Requirement: nomenclatura pública en lenguaje llano

Los labels visibles del sitio (headers, tabs, titles, índice, guía, README) SHALL
usar un nombre canónico en español llano, definido en una única clave de
`config/fpa.json` y consumido por todos los generadores. Los labels SHALL NOT
contener el término "FP&A" ni otra jerga corporativa no explicada. Los nombres de
archivo, IDs de requisito (FPA-xxx) y variables internas SHALL NOT cambiar.

#### Scenario: label sin jerga

- **WHEN** se generan `fpa-dashboard.html`, `index.html` y `data/fpa-guide.html`
- **THEN** ningún label visible contiene "FP&A" y el nombre mostrado proviene de
  la clave de config canónica

#### Scenario: test de nomenclatura falla loud

- **WHEN** un generador emitiera un label visible con "FP&A"
- **THEN** el test de nomenclatura falla nombrando el archivo y el label

### Requirement: guía de análisis a cuatro niveles, en español y con grounding

El sistema SHALL (debe) versionar la guía de análisis en español
(`docs/fpa-analyses-guide.md`, 19 análisis × niveles ELI5/Everyday/Practitioner/
Expert) en el repo como fuente de contenido, con un pase de **grounding** previo a
la publicación: cada fórmula, umbral y default citado SHALL verificarse contra la
implementación real (`viz-fpa.py`, `usage-tracker.py`, `config/fpa.json`); las
cifras ilustrativas del snapshot original SHALL reemplazarse por cifras derivadas
en generación o eliminarse; y ante discrepancia guía↔código SHALL corregirse el
texto de la guía, nunca el código.

El generador SHALL ingerrir la guía (parse stdlib) y producir:

- `data/fpa-guide.html`: la guía completa, autocontenida y en el tema del sitio.
- **Marginalia con progressive disclosure**: en cada una de las 5 vistas del
  Dashboard y en el Gantt, cada análisis mapeado SHALL anunciarse con un
  affordance compacto (chip/botón de información, target táctil de 44px) cuyo
  tooltip muestre el teaser del nivel 1 (ELI5); al seleccionar el chip SHALL
  expandirse la nota in situ (nivel 2 completo, nivel 3 colapsado, enlace a la
  guía completa y a los IDs FPA-xxx). En touch, la expansión SHALL funcionar por
  tap sin depender de hover.

El mapeo análisis→superficie (vistas + Gantt) SHALL estar declarado en el
generador, anclado a los IDs FPA-xxx del texto de la guía, y cada análisis SHALL
aparecer en la marginalia de al menos una superficie. El `--check-docs` SHALL
extenderse para fallar loud si el mapeo referencia un análisis inexistente en la
guía o si un umbral citado por la guía difiere de su valor real en config/código.

#### Scenario: marginalia cubre todos los análisis incluido el Gantt

- **WHEN** se generan el dashboard y el Gantt con la guía presente
- **THEN** cada análisis de la guía aparece en la marginalia de ≥1 superficie
  (vista del dashboard o Gantt) y los enlaces a `fpa-guide.html` resuelven

#### Scenario: expansión desde el chip

- **WHEN** un lector selecciona el chip de información de un análisis (click o tap)
- **THEN** la nota se expande in situ mostrando el nivel 2 y el enlace al análisis
  de la guía completa, sin recargar la página

#### Scenario: check-docs detecta mapeo o umbral roto

- **WHEN** el mapeo referencia un análisis inexistente, o un umbral citado por la
  guía difiere del valor real en config/código
- **THEN** el generador termina con exit non-zero nombrando la discrepancia

#### Scenario: grounding corrige el texto, no el código

- **WHEN** una afirmación de la guía contradice el comportamiento real del código
- **THEN** se corrige el texto de la guía y el generador/código permanece sin
  cambios por esa discrepancia

### Requirement: consolidación de dashboards

El Dashboard SHALL (debe) ser el dashboard único del sitio con su nombre llano.
El dashboard de insights (`data/dashboard.html` y `scripts/viz-dashboard.py`)
SHALL eliminarse del repo y del deploy: el índice SHALL listarlo ya no, el README
SHALL documentar la eliminación y su cobertura por el Dashboard, y los URLs
externos que apunten al HTML eliminado SHALL romperse (riesgo aceptado, sin
visitas registradas). El Gantt (`gantt-multitasking.html`) SHALL conservarse como
visualización única de su tipo y SHALL adoptar el tema compartido.

#### Scenario: índice sin dashboard de insights

- **WHEN** se genera `index.html`
- **THEN** lista el Dashboard (nombre llano) como dashboard principal y el Gantt,
  sin entrada para el dashboard de insights

#### Scenario: artefactos eliminados

- **WHEN** se inspecciona el repo y el deploy tras el change
- **THEN** `data/dashboard.html` y `scripts/viz-dashboard.py` no existen y la
  suite verde no los referencia
