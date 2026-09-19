## 0. Config y esquema (tickets bd de fase 0)

- [x] 0.1 Crear `config/fpa.json` con taxonomía de proyectos (FPA-018), calendario
      de suscripciones fechado con default Pro Mar-19 / Max Abr-19 / Pro Jun-19
      (FPA-015), pricing versionado por fecha efectiva (FPA-016)
- [x] 0.2 Añadir al config: presupuestos mensuales (cash, efectivo, objetivo por
      1k interacciones) con mes de inicio (FPA-050/051), umbrales de alertas con
      defaults de la spec (FPA-088), modelos premium (default: Opus, FPA-037),
      horarios laborales (FPA-111), días de dormancia/novedad (FPA-122),
      CTAs con targets (FPA-168), idioma (FPA-162), retro opcional (FPA-178)
- [x] 0.3 Extender `specs/usage-report-v3.schema.json` en sitio (versionar a v4
      solo si un campo cambia de significado, no si solo se añade) para las
      emisiones nuevas del tracker; mantener `--validate` verde
- [x] 0.4 Open questions 1–7 resueltas (2026-09-20, ver design.md): budget
      efectivo informativo, sin pay-per-token real (campo assumed/cero), taxonomía
      inferida de repos con overrides, horarios default Mon–Fri 9–18, retro
      conservado (FPA-178 completo), CTAs a rutas relativas publicadas, idioma es
      — reflejarlas en config/fpa.json

## 1. Base y resumen ejecutivo (FPA-001…009)

- [x] 1.1 Esqueleto `scripts/viz-fpa.py`: HTML autocontenido, inline SVG, header
      con fecha de generación y versión del tracker (FPA-001/005), tema claro/oscuro
      según sistema (FPA-093), formatos USD y tabular nums (FPA-095)
- [x] 1.2 Resumen ejecutivo de 3–5 cifras headline con interpretación de una línea
      (FPA-007); "n/a" con razón si no se puede computar, nunca vacío (FPA-008)
- [x] 1.3 Provenance tag *reported*/*assumed* en toda figura (FPA-003); separación
      estricta efectivo/cash, jamás sumados (FPA-002)
- [x] 1.4 Marca de mes parcial con días transcurridos/total (FPA-004); claims
      narrativos solo con métrica nombrada + threshold visibles (FPA-009)
- [x] 1.5 Validación de schema con exit non-zero y listado de campos fallidos
      (FPA-006); placeholder-check del smoke (FPA-108)
- [x] 1.6 Tests dorados fase 1 (agregaciones base) + smoke Playwright

## 2. Datos, jerarquías y KPIs (FPA-010…045, 140–142)

- [ ] 2.1 Emisiones tracker: breakdown por tool/model (FPA-011), project totals via
      `project_daily` (FPA-012), pay-per-token separado de suscripción con
      provenance assumed (no hay cargas reales, FPA-013), commits/releases con
      token GitHub (FPA-014), tokens in/out/cache por mes y modelo (FPA-019)
- [ ] 2.2 Emisiones tracker: interacciones por kind con share de tool-calls
      (FPA-140), proyectos filtrados por charly-filter con share (FPA-141),
      timezone registrada (FPA-142), concurrencia/paralelismo (FPA-120)
- [ ] 2.3 Árboles expandibles Time/Tool/Portfolio con columnas completas y
      recompute al cambiar el periodo (FPA-020…026); roll-up ≤ $0.01 y 1
      interacción (FPA-025); Portfolio limitado al periodo completo con la
      limitación visible mientras no haya project-by-month (FPA-027)
- [ ] 2.4 KPI strip: KPIs FPA-030…045 del periodo con sparkline y delta vs prior;
      outcome KPIs si hay datos (FPA-040); daily rates en meses parciales (FPA-041);
      "n/a" con denominador cero (FPA-042)
- [ ] 2.5 Token KPIs: cache-hit rate (FPA-043), ratio out/in (FPA-044), n/a por
      tool con share excluido (FPA-045)
- [ ] 2.6 Periodo sin datos → exclusión de trends y marker n/a (FPA-017)
- [ ] 2.7 Tests dorados de KPIs + roll-up (FPA-101) con fixture de meses parciales
      (FPA-102)

## 3. Presupuesto, bridge y forecast (FPA-050…077)

- [ ] 3.1 Presupuestos: pro-rating de mes parcial (FPA-052), varianza con signo y
      marcador favorable/desfavorable no-solo-color (FPA-053/054), tabla mensual
      con YTD (FPA-055), recompute sin reload (FPA-056)
- [ ] 3.2 Bridge precio-volumen-mix: fórmulas Volume/Mix/Rate (FPA-061…064),
      identidad ≤ $0.01 (FPA-065), FME en meses parciales (FPA-066), eje truncado
      etiquetado (FPA-067), 100% stacked mix por mes (FPA-068)
- [ ] 3.3 Forecast: run-rate base = media FME últimos 3 meses, "n/a" con razón si
      hay <3 meses de datos (FPA-070/008), inputs de escenario (FPA-071), fórmulas
      efectivo/cash (FPA-072/073), YTD+outlook vs presupuesto (FPA-074), resto del
      mes parcial como fila separada (FPA-075), distinción actual/forecast
      no-solo-color (FPA-076), update sin reload (FPA-077)
- [ ] 3.4 Tests dorados: bridge identity, pro-rating, FME, forecast (FPA-101/102);
      FPA-105 (economía de planes) se cubre en 4.3; test de paridad JS/Python:
      los valores recalculados en el cliente (varianza, forecast) igualan los
      golden precalculados sobre el fixture

## 4. Alertas y economía de suscripción (FPA-080…088, 130–133)

- [ ] 4.1 Motor de alertas con severity + rule name + evidencia (FPA-080); reglas:
      verify-plan (FPA-081), reconciliación $65.58 vs ~$220 (FPA-082), budget
      (FPA-083), unit-cost (FPA-084), mix (FPA-085), concentración (FPA-086),
      staleness (FPA-087); umbrales configurables (FPA-088)
- [ ] 4.2 Utilización por plan (FPA-130), break-even y headroom (FPA-131),
      comparación 4 casos (FPA-132), disclaimer de usage limits (FPA-133)
- [ ] 4.3 Tests dorados de utilización/break-even/comparación (FPA-105)

## 5. Patrones de uso, concurrencia y ciclo de vida (FPA-110…123)

- [ ] 5.1 Heatmap día×hora con timezone (FPA-110), after-hours/weekend share
      (FPA-111), weekly WoW y varianza (FPA-112)
- [ ] 5.2 Skills: top por usos (FPA-113), zero/once-uso + trend mensual si el
      tracker emite instaladas (FPA-114), slash commands con trend (FPA-115)
- [ ] 5.3 Sesiones: buckets de longitud (FPA-116), coste por bucket + mediana/p90
      (FPA-117), `/clear` por 100 sesiones (FPA-118)
- [ ] 5.4 Timeline por tool/model con gaps flag (FPA-119); concurrencia etiquetada
      paralelo vs contexto (FPA-120), share de sesiones con Agent (FPA-121)
- [ ] 5.5 Lifecycle: new/active/dormant (FPA-122), activos por mes y coste de
      dormantes (FPA-123); overlay de creación de repos (FPA-098)
- [ ] 5.6 Pareto de proyectos con cola agrupada (FPA-028), concentración top-3
      (FPA-036), drill Project→Model (FPA-021)

## 6. UX, CTA y export (FPA-090…098, 150–179)

- [ ] 6.1 Arquitectura de información: 5 vistas + Data & method (FPA-150/151),
      presets de periodo YTD/Q1–Q3 y custom range (FPA-090), navegación de vistas
      (FPA-091), mobile tabs /
      desktop secuencia (FPA-152), period selector fijo único (FPA-153), above the
      fold (FPA-154), top-5 + Show all (FPA-155), merges (FPA-156), Data & method
      colapsado (FPA-157), sin duplicación Pareto/árbol (FPA-158)
- [ ] 6.2 Títulos-hallazgo computados con fallback (FPA-160/161), idioma única
      (FPA-162), Data section con definición de interaction y gaps (FPA-096/140),
      numeración automática de figuras (FPA-144), sin placeholders vacíos (FPA-146),
      método de render documentado (FPA-145)
- [ ] 6.3 CTAs: 1 primario + ≤3 secundarios en Summary (FPA-165), máx 1 primario
      por vista (FPA-166), alerta→1 botón de acción (FPA-167), targets de config
      con fail si vacío — check activo desde que exista la clave `ctas`, obligatorio
      en F6 (FPA-168), labels verb-first ≤4 palabras (FPA-172)
- [ ] 6.4 Export/share: Export CSV en toda tabla + Download SVG en todo chart
      (FPA-169), Share view con URL que restaura estado (FPA-170), params inválidos
      ignorados (FPA-171)
- [ ] 6.5 Accesibilidad móvil: tap/focus/hover readout persistente (FPA-175),
      targets 44px (FPA-176), primera columna fija en tablas anchas (FPA-177),
      retro confinado+opcional+reduced-motion+4.5:1 (FPA-178), skip-link +
      lang (FPA-179), teclado y focus visible (FPA-094), scroll horizontal
      <600px (FPA-092), presets de periodo (FPA-090), navegación de vistas (FPA-091)
- [ ] 6.6 Tests: sin primario duplicado, sin target vacío, URL share restaura
      (FPA-149); numeración sin duplicados (FPA-106); doc-consistency de cifras del
      README (FPA-143) y CI (FPA-107); smoke 390×844 (FPA-109)

## 7. Cierre

- [ ] 7.1 Determinismo del output (FPA-104) verificado con doble corrida
- [ ] 7.2 `openspec validate add-fpa-dashboard --strict` verde y tareas al día
- [ ] 7.3 `openspec archive add-fpa-dashboard` al desplegar
