# fpa-dashboard Specification

## Purpose
TBD - created by archiving change add-fpa-dashboard. Update Purpose after archive.
## Requirements
### Requirement: Generador stdlib-only autocontenido

El Dashboard SHALL (debe) generarse con un script Python stdlib-only
(`scripts/viz-fpa.py`) como un único archivo HTML autocontenido con SVG inline.

#### Scenario: HTML sin dependencias externas

- **WHEN** se genera el dashboard y se inspecciona el HTML
- **THEN** no hay `<script src>` ni `<link href>` externos y los charts son SVG inline

### Requirement: separación de coste efectivo y cash

El Dashboard SHALL (debe) mostrar coste efectivo y cash cost como medidas separadas
y nunca sumarlas.

#### Scenario: totales por separado

- **WHEN** se muestra cualquier total agregado de coste
- **THEN** efectivo y cash aparecen como cifras distintas, sin suma combinada

### Requirement: provenance en toda figura

Toda figura SHALL (debe) llevar un tag de procedencia: *reported* (del JSON) o
*assumed* (de la configuración).

#### Scenario: cifra asumida marcada

- **WHEN** se renderiza una cifra derivada de config (p.ej. precio de plan)
- **THEN** lleva el tag *assumed* junto al valor

### Requirement: meses parciales marcados

Cuando la última fecha del reporte cae antes del fin de su mes, el Dashboard SHALL
(debe) marcar ese mes como parcial y mostrar los días transcurridos sobre el total.

#### Scenario: reporte a medio mes

- **WHEN** el reporte termina el 10 de junio
- **THEN** junio aparece como parcial con `10/30` días y sus comparaciones usan
  daily rates (FPA-041)

### Requirement: resumen ejecutivo con fallback n/a

El Dashboard SHALL (debe) abrir con 3–5 cifras headline, cada una con interpretación
de una línea derivada de los datos. Si una cifra no puede computarse SHALL (debe)
mostrar "n/a" con la razón y no renderizar un resumen vacío. Mientras un periodo no
tenga datos (p.ej. el gap de Enero 1–10), SHALL (debe) excluirse de trends y
cálculos de coste unitario y marcarse "n/a" (FPA-017).

#### Scenario: headline sin datos

- **WHEN** una métrica headline carece de datos (p.ej. sin commits)
- **THEN** la card muestra "n/a" con la razón en lugar de vacío o cero

### Requirement: claims con métrica y threshold visibles

El Dashboard SHALL (debe) mostrar un claim narrativo solo si se computa de una
métrica nombrada y un threshold, ambos visibles junto al claim.

#### Scenario: claim sin soporte se rechaza

- **WHEN** el generador evalúa un claim sin métrica+threshold asociados
- **THEN** el claim no se renderiza

### Requirement: árboles con roll-up verificado

El Dashboard SHALL (debe) proveer árboles expandibles Time (Año→Trimestre→Mes),
Tool (Tool→Model) y Portfolio (Categoría→Proyecto, con drill a Model cuando haya
datos), mostrar en cada nodo las columnas coste, % del total, interacciones, coste
por 1k y delta vs prior (budget/varianza en Time), garantizar que todo padre
iguale la suma de sus hijos dentro de $0.01 y 1 interacción, recomputar los
árboles y los KPIs al seleccionar un periodo (FPA-026), y — mientras no haya
datos project-by-month — limitar el árbol Portfolio al periodo completo del
reporte mostrando esa limitación (FPA-027).

#### Scenario: roll-up consistente

- **WHEN** se expande un nodo padre
- **THEN** la suma de sus hijos difiere del padre en ≤ $0.01 y ≤ 1 interacción
  (verificado por test dorado FPA-101)

### Requirement: KPI strip con sparkline y delta

El Dashboard SHALL (debe) calcular los KPIs del periodo seleccionado —costes
efectivo/cash con daily-rate delta, leverage, coste por 1k, coste por sesión,
concentración top-3, share premium, autonomous share, multitasking, outcome KPIs
donde haya datos, cache-hit rate y ratio out/in— cada uno con sparkline mensual y
delta vs prior. Con denominador cero SHALL (debe) mostrar "n/a", nunca cero o
infinito. Con mes parcial SHALL (debe) comparar como daily rates. Si faltan datos
de tokens para una tool, los KPIs de tokens SHALL (debe) marcarse "n/a" para esa
tool, excluirse del cálculo y mostrarse el share excluido (FPA-045).

#### Scenario: denominador cero

- **WHEN** un KPI tiene denominador 0 (p.ej. 0 interacciones)
- **THEN** la card muestra "n/a" con la razón

### Requirement: presupuesto y varianza interactivos

El Dashboard SHALL (debe) aceptar presupuestos mensuales (cash, efectivo, objetivo
por 1k) aplicados desde un mes de inicio configurable, pro-ratear meses parciales,
calcular varianza con signo (positivo = over budget), marcar favorable/desfavorable
con color Y texto/símbolo, mostrar tabla mensual con YTD, y recalcular al editar un
input sin recargar la página. El presupuesto de coste efectivo SHALL (debe)
tratarse como informativo (soft): el presupuesto gestionado es el de cash cost.

#### Scenario: edición de presupuesto

- **WHEN** el usuario edita el input de presupuesto mensual
- **THEN** todas las varianzas se recalculan sin recarga de página

### Requirement: bridge precio-volumen-mix con identidad

El Dashboard SHALL (debe) mostrar un waterfall del coste efectivo del mes prior al
seleccionado, descompuesto en Volume = (Q1−Q0)×rate₀, Mix = Σ(q1ᵢ·p0ᵢ) − Q1·rate₀ y
Rate = Σ q1ᵢ·(p1ᵢ−p0ᵢ), usando rate actual como prior para modelos nuevos (solo Mix),
con identidad Volume+Mix+Rate = Δcoste dentro de $0.01, FME y etiqueta cuando haya
meses parciales, eje truncado etiquetado, y un chart 100% stacked de mix por mes.

#### Scenario: identidad del bridge

- **WHEN** se computa el bridge para dos meses cualesquiera
- **THEN** Volume + Mix + Rate = Δcoste dentro de $0.01 (test dorado FPA-101)

### Requirement: forecast con escenarios

El Dashboard SHALL (debe) proyectar el resto del año desde un run-rate base (media
FME de los últimos 3 meses; con menos de 3 meses de datos, la sección SHALL (debe)
mostrar "n/a" con la razón), aceptar escenarios (crecimiento %, cambio de rate %,
plan futuro), calcular efectivo y cash con las fórmulas FPA-072/073, mostrar
YTD+outlook vs presupuesto con varianza, fila separada para el resto del mes
parcial, y distinguir actual de forecast con patrón/label, no solo color, con
update sin reload. El plan futuro default SHALL (debe) ser la suscripción
activa al cierre del reporte; si no hay ninguna (Free/cancelado), el default
SHALL (debe) ser "sin suscripción" (fee $0) con los planes del calendario
como escenarios hipotéticos (FPA-071).

#### Scenario: cambio de escenario

- **WHEN** el usuario ajusta el growth % del escenario
- **THEN** el forecast se recalcula sin recarga y las cifras forecast quedan
  distinguidas de las actuales por patrón/label

#### Scenario: plan default sin suscripción activa

- **WHEN** ninguna suscripción del calendario cubre la fecha de fin del
  reporte
- **THEN** el forecast arranca con "sin suscripción" (cash = p2p escalado)
  y no inventa una suscripción que no existe

### Requirement: alertas con evidencia y umbrales configurables

El Dashboard SHALL (debe) listar alertas con severity, nombre de regla y valores de
evidencia, cubriendo: share efectivo/precio de plan > 25× (verify plan), discrepancia
entre el cash cost real (ledger `data/charges.json`, *reported*) y las cargas
implícitas del calendario de suscripciones (*assumed*) más allá de la tolerancia
(reconciliación, FPA-082), over-budget,
unit-cost +15% MoM, shift de mix premium > 5pts en 3 meses, concentración
top-3 > 50%, y staleness del reporte > 14 días. Todos los umbrales SHALL (debe) ser
configurables.

#### Scenario: reconciliación de suscripción

- **WHEN** el cash real del ledger difiere de las cargas implícitas del
  calendario más allá de la tolerancia
- **THEN** se emite una alerta de reconciliación mostrando ambas cifras
  (real *reported* vs implícito *assumed*), con la corrección del
  calendario de coffe-a31 el caso motivador queda resuelto: jun 2026 real
  $0 (sin factura) vs implícito $0

#### Scenario: calendario desalineado con facturas

- **WHEN** el calendario del config afirma una suscripción que las
  facturas no respaldan (o viceversa)
- **THEN** la alerta de reconciliación lo señala con los dos montos, que es
  la señal para corregir `config/fpa.json`

### Requirement: vistas por pregunta con CTAs

El Dashboard SHALL (debe) organizarse en las vistas Summary, Cost, Breakdown,
Habits, Outlook (+ Data & method colapsado; nombres canónicos en inglés, renderizados
en el idioma configurado — es), cada una encabezada por la pregunta que responde
(también en el idioma configurado), con presets de periodo (YTD, Q1–Q3, rango
custom, FPA-090) y navegación de vistas (FPA-091), titles de charts computados como
hallazgos (métrica+threshold, con fallback al label descriptivo), un period selector
único fijo, top-5 + "Show all" en listas, un CTA primario máximo por vista (Summary:
"Read the series" + ≤3 secundarios), targets de config con fail del generador si
están vacíos (check activo desde que exista la clave `ctas`; obligatorio cuando la
clave existe), labels verb-first ≤4 palabras, y un solo idioma configurado.

#### Scenario: generador falla con CTA vacío

- **WHEN** un CTA configurado tiene target vacío
- **THEN** `viz-fpa.py` termina con exit non-zero nombrando el CTA

### Requirement: export y share de vista

El Dashboard SHALL (debe) ofrecer "Export CSV" en toda tabla y "Download SVG" en
todo chart — ambos generados client-side sin librerías externas — y un control
"Share view" que copia una URL codificando periodo, vista y expansión de árbol; al
cargar con esos parámetros SHALL (debe) restaurar el estado, e ignorar parámetros
inválidos cargando defaults.

#### Scenario: export de tabla

- **WHEN** el usuario activa "Export CSV" en una tabla
- **THEN** se descarga un CSV con las filas visibles

#### Scenario: URL compartida restaura estado

- **WHEN** se abre la URL con parámetros de periodo/vista/expansión válidos
- **THEN** el dashboard restaura exactamente ese estado

#### Scenario: parámetros inválidos ignorados

- **WHEN** la URL contiene parámetros inválidos
- **THEN** se ignoran y se cargan los defaults

### Requirement: patrones de uso y ciclo de vida

El Dashboard SHALL (debe) mostrar: heatmap día×hora con timezone etiquetada, shares
after-hours/weekend con horarios configurables, WoW y varianza semanal, skills y
comandos con trends, buckets de longitud de sesión con coste/mediana/p90, `/clear`
por 100 sesiones, timeline por tool/model con gaps flag > N días, métricas de
concurrencia etiquetadas (paralelo vs context switching), share de sesiones con
Agent, clasificación de proyectos new/active/dormant con coste dormante, y — donde
haya fechas de creación de repos — su overlay como marcadores en el trend mensual
(FPA-098).

#### Scenario: timezone ausente marca vistas

- **WHEN** el tracker no registró timezone
- **THEN** las vistas hora/día se marcan "unverified" (FPA-142)

### Requirement: economía de suscripción

El Dashboard SHALL (debe) calcular utilización por plan (efectivo ÷ precio),
break-even mensual y headroom, comparar cash cost bajo 4 casos (actual,
todo pay-per-token, todo Pro, todo Max) y declarar que la equivalencia por coste
efectivo ignora usage limits del plan. La economía de planes SHALL (debe)
operar sobre el calendario de suscripciones del config — corregido a las
facturas (coffe-a31) — con provenance *assumed*: un panel por cada periodo
del calendario. Cuando ninguna suscripción esté activa al cierre del
reporte (Free/cancelado), el plan default del forecast SHALL (debe) ser
"sin suscripción" (fee $0; cash = p2p escalado, FPA-073) y los periodos del
calendario quedan como escenarios hipotéticos seleccionables.

#### Scenario: break-even visible

- **WHEN** se muestra el panel de un plan
- **THEN** aparecen utilización, break-even y headroom calculados del config

#### Scenario: sin suscripción activa al cierre

- **WHEN** el reporte termina después de la última factura de
  suscripción (p.ej. claude cancelado tras jun 2026)
- **THEN** el plan default del forecast es "sin suscripción" (fee $0) y
  los planes históricos del calendario siguen listables como escenarios

### Requirement: calidad de datos y documentación

El Dashboard SHALL (debe): definir "interaction" en la sección Data y mostrar el
share de tool-calls; mostrar el share filtrado por el charly-filter; mostrar la
timezone registrada o marcar vistas hora/día como unverified; renderizar las cifras
citadas en README/docs desde el JSON o fallar en modo `--check-docs`; numerar
figuras y tablas automáticamente sin duplicados; documentar el método de render;
no renderizar placeholders vacíos; y derivar cualquier label de periodo decorativo
del periodo real de los datos.

#### Scenario: check-docs detecta cifra obsoleta

- **WHEN** una cifra citada en el README difiere del JSON y se corre `--check-docs`
- **THEN** el generador falla listando la cifra en desacuerdo

### Requirement: accesibilidad y mobile

El Dashboard SHALL (debe): operar todo control por teclado con focus visible;
inspeccionar todo chart por tap/focus/hover con readout persistente (captions sin
hover); touch targets ≥ 44×44 px; primera columna fija en tablas anchas con scroll
horizontal < 600px; single-column < 600px; tema claro/oscuro según sistema;
formato USD y miles con tabular nums; skip-to-content y `lang` del documento;
retro decorativo confinado a header/footer, opcional por config, sin animación bajo
`prefers-reduced-motion`, contraste ≥ 4.5:1; y funcionar sin storage con defaults.

#### Scenario: smoke mobile 390×844

- **WHEN** el smoke test carga la página a 390×844
- **THEN** el primer viewport contiene título, period selector y primera headline,
  sin scroll horizontal ni errores de consola

### Requirement: verificación del dashboard

La suite SHALL (debe) incluir: golden tests de agregaciones contra fixture fijo;
verificación de roll-up de árboles y identidad del bridge; tests de mes parcial
(FME, pro-rating, daily rates); golden tests de utilización/break-even/comparación
de planes; smoke Playwright que falle en cualquier error de consola, resumen vacío,
placeholder sin valor o viewport mobile incompleto; test de unicidad de numeración
de figuras; test de CTAs (≤1 primario por vista, sin target vacío) y restauración
de URL share; determinismo byte-a-byte salvo timestamp; y check de consistencia de
docs en CI.

#### Scenario: doble corrida determinista

- **WHEN** el generador corre dos veces con el mismo input
- **THEN** el output es idéntico salvo la fecha de generación (FPA-104)

### Requirement: cash cost desde el ledger de cargos reales

El Dashboard SHALL (debe) computar el cash cost como la suma de los cargos
reales del ledger `data/charges.json` (provenance *reported*), contando solo
los kinds IA `subscription|credits|refund` dentro del periodo mostrado —
`api_cycle` aporta $0 y los cargos de storage quedan fuera del cash de IA.
Toda cifra de cash derivada del ledger SHALL (debe) llevar el tag
*reported*. Si un periodo no tiene facturas para un proveedor, el cash de
ese proveedor SHALL (debe) mostrarse "n/a" con la razón (FPA-008), nunca
vacío ni cero inventado. El cash cost (ledger) y el coste efectivo
(estimado API-equivalente del tracker) SHALL (debe) seguir siendo medidas
separadas y jamás sumarse (FPA-002). Los fees implícitos del calendario de
suscripciones NO son cash cost: solo alimentan la reconciliación (FPA-082)
y la economía de planes (FPA-130–133).

#### Scenario: cash mensual del ledger

- **WHEN** se muestra el cash cost de un mes con facturas (p.ej. mayo 2026:
  claude Pro $20 + codex Plus $20 + gemini $19.99)
- **THEN** la cifra es la suma de los cargos del ledger de ese mes y lleva
  el tag *reported*

#### Scenario: proveedor sin facturas en el periodo

- **WHEN** un proveedor no registra cargos en el periodo consultado
  (p.ej. openrouter entre mar y may 2026)
- **THEN** su cash se muestra "n/a" con la razón (sin facturas en el
  periodo), no cero ni ausencia silenciosa

#### Scenario: refund descuenta

- **WHEN** el ledger incluye un refund negativo en el periodo
  (p.ej. claude-cli −$28.22 el 2026-02-19)
- **THEN** el cash del periodo lo descuenta (es dinero devuelto, no gastado)

