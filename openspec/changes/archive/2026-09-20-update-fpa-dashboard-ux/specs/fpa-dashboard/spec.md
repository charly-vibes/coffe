# fpa-dashboard — delta spec (update-fpa-dashboard-ux)

## ADDED Requirements

### Requirement: navegación de vistas efectiva a todo ancho

El Dashboard SHALL (debe) mostrar exactamente una vista a la vez a cualquier
ancho de viewport (no solo <600px). Las tabs SHALL (debe) cambiar la vista
visible sin recargar, actualizar `aria-current` y el parámetro `view` del
share-URL (query params — `?view=…` —, contrato vigente de share-URL; sin
hash). Con JS deshabilitado, las tabs SHALL (debe) seguir resolviendo la
vista por ancla (fallback degradado).

#### Scenario: tab switch en desktop

- **WHEN** se carga el dashboard a 1280×900 y se clickea la tab "Hábitos"
- **THEN** solo la vista Habits es visible, la altura de página es < 2× el
  viewport y la tab activa lleva `aria-current="true"`

#### Scenario: deep-link de vista

- **WHEN** se abre el dashboard con `?view=habits` (parámetro de share-URL)
- **THEN** la vista Habits está activa al cargar, sin scroll de llegada

### Requirement: layout de contenedor y jerarquía visual

El Dashboard SHALL (debe) renderizar dentro de un contenedor con `max-width`
centrado (sin columnas muertas a ningún ancho ≥ 600px). Los KPI cards SHALL
(debe) disponerse en una grilla responsive (≥2 columnas ≥600px, 3–4 columnas
≥1000px) con anatomía uniforme: label, cifra (tabular), delta chip y contexto
muted. Los CTAs SHALL (debe) renderizar como una fila compacta de botones
(altura ≤ 64px), no como cajas verticales. Los IDs FPA-xxx SHALL (debe) salir
del cuerpo visible del texto (pueden persistir en atributos `title` o
footnotes al final de la sección). El texto secundario (notas de método,
razones n/a) SHALL (debe) renderizar con el token muted, distinguible de la
cifra primaria.

#### Scenario: grilla de KPIs en desktop

- **WHEN** se muestra la banda de KPIs a 1280px
- **THEN** los cards se disponen en ≥3 columnas y ningún card excede la
  altura de la fila

#### Scenario: sin IDs FPA en el cuerpo

- **WHEN** se inspecciona el texto visible del HTML generado
- **THEN** ningún párrafo o celda contiene "FPA-\d\d\d" (los IDs solo
  aparecen en atributos o footnotes)

#### Scenario: CTAs compactos

- **WHEN** se renderiza la fila de CTAs del Summary
- **THEN** cada CTA mide ≤ 64px de alto y la fila ocupa una sola línea de
  layout a ≥600px

### Requirement: banda de KPI única sin duplicación

Cada cifra headline SHALL (debe) renderizar exactamente una vez en la vista
Summary: la banda de KPIs es la única superficie de cifras en cards; el
hallazgo narrativo correspondiente aparece como texto (claim con
métrica+threshold, según el requisito existente) y no como card repetida. Se
elimina el bloque de headline cards separado. Los claims conservan sus
cifras: la exclusión de duplicados aplica solo a cards, no al texto de
claims.

#### Scenario: cifra sin duplicar

- **WHEN** se renderiza la vista Summary
- **THEN** cada cifra KPI aparece en exactamente un card (verificado por
  test: ninguna cifra `fmt_usd` se repite entre cards visibles del primer
  viewport)

### Requirement: disclosure por defecto y summaries estilizados

Por vista, SHALL (debe) abrir expandida por defecto únicamente la sección
primaria (la que responde la pregunta de la vista); las demás secciones
SHALL (debe) renderizar colapsadas con su `summary` estilizado como group-box
del tema (marcador integrado al header, sin marcador nativo huérfano en línea
propia). El estado abierto/cerrado SHALL (debe) persistir en el share-URL
(sin cambio de contrato).

#### Scenario: disclosure inicial

- **WHEN** se carga la vista Cost sin parámetros
- **THEN** solo una de sus secciones está expandida y el resto renderiza
  colapsada con summary clickeable ≥44px de alto

#### Scenario: summary sin marcador huérfano

- **WHEN** se renderiza cualquier `<details>` de sección
- **THEN** el marcador de disclosure está integrado al summary y ningún
  marcador ocupa una línea propia fuera del header

### Requirement: bridge con selector de mes

El bridge precio-volumen-mix SHALL (debe) renderizar un único waterfall con
un selector de mes (default: el último mes con datos de mix), no una figura
por mes. Los meses sin datos de mix SHALL (debe) omitirse del selector, no
renderizar marcos vacíos. La tabla 100% stacked de mix por mes se conserva.
La identidad Volume+Mix+Rate = Δcoste SHALL (debe) seguir verificándose por
mes (sin cambio del requisito de datos).

#### Scenario: un waterfall, selector de mes

- **WHEN** se muestra la sección bridge en la vista Cost
- **THEN** hay exactamente un waterfall visible y un control para elegir el
  mes; cambiar el mes re-renderiza el waterfall sin recargar

#### Scenario: mes sin datos de mix

- **WHEN** un mes no tiene datos suficientes para el bridge
- **THEN** ese mes no aparece en el selector y no se renderiza marco vacío

#### Scenario: ningún mes con datos de mix

- **WHEN** el periodo seleccionado no tiene ningún mes con datos de mix
- **THEN** la sección muestra "n/a" con la razón y no renderiza selector ni
  waterfall (sin placeholders vacíos)

## MODIFIED Requirements

### Requirement: resumen ejecutivo con fallback n/a

La banda de KPIs SHALL (debe) ser el resumen ejecutivo: 3–5 cifras KPI, cada
una con su interpretación de una línea derivada de los datos como contexto
del card (anatomía label → cifra → delta → contexto). Si una cifra no puede
computarse SHALL (debe) mostrar "n/a" con la razón y no renderizar un resumen
vacío. Mientras un periodo no tenga datos (p.ej. el gap de Enero 1–10),
SHALL (debe) excluirse de trends y cálculos de coste unitario y marcarse
"n/a" (FPA-017). No SHALL (debe) renderizarse un bloque separado de headline
cards que duplique las cifras de la banda.

#### Scenario: headline sin datos

- **WHEN** una métrica headline carece de datos (p.ej. sin commits)
- **THEN** el card KPI muestra "n/a" con la razón en lugar de vacío o cero

#### Scenario: cifra en un solo card

- **WHEN** se renderiza la vista Summary
- **THEN** cada cifra KPI aparece en exactamente un card; los claims
  narrativos conservan sus cifras (no son cards)

### Requirement: vistas por pregunta con CTAs

El Dashboard SHALL (debe) organizarse en las vistas Summary, Cost, Breakdown,
Habits, Outlook (+ Data & method colapsado; nombres canónicos en inglés,
renderizados en el idioma configurado — es), cada una encabezada por la
pregunta que responde (también en el idioma configurado), con presets de
periodo (YTD, Q1–Q3, rango custom, FPA-090) y navegación de vistas efectiva a
todo ancho (ver "navegación de vistas efectiva a todo ancho"), titles de
charts computados como hallazgos (métrica+threshold, con fallback al label
descriptivo), un period selector único fijo, top-5 + "Show all" en listas, un
CTA primario máximo por vista (Summary: "Read the series" + ≤3 secundarios)
renderizado como fila compacta de botones (ver "layout de contenedor y
jerarquía visual"), targets de config con fail del generador si están vacíos
(check activo desde que exista la clave `ctas`; obligatorio cuando la clave
existe), labels verb-first ≤4 palabras, y un solo idioma configurado. La
marginalia de cada vista SHALL (debe) renderizar como un strip consistente
bajo el header de la vista (no dispersa en columnas huérfanas).

#### Scenario: generador falla con CTA vacío

- **WHEN** un CTA configurado tiene target vacío
- **THEN** `viz-fpa.py` termina con exit non-zero nombrando el CTA

#### Scenario: marginalia consistente

- **WHEN** se renderiza cualquier vista con chips de marginalia
- **THEN** los chips ocupan un único strip bajo el header de la vista y no
  quedan chips flotando fuera de él
