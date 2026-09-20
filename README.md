# coffee — Tracking de uso de IA

> *Do you feel like a chain store /
> Practically floored /
> One of many zeroes /
> Kicked around bored*
>
> — Blur, "Coffee & TV"

Extractado de `microdancing` (branch `data/datos-uso-ia`, tip `09c063e`) para poder
reutilizar y extender el tracker independientemente de la serie de posts.
Propósito: recolectar, procesar y documentar el uso de IA (Claude CLI, Pi, Amp, Gemini)
de los últimos meses.

## Archivos

### Scripts

| Archivo | Propósito |
|---------|-----------|
| `scripts/usage-tracker.py` | Extractor de uso de IA v4.3. Lee datos de Claude, Pi (incluye Gemini vía google-gemini-cli) y Amp. Filtra solo proyectos charly. Produce reporte JSON con hourly/daily/monthly/projects/sessions/skills/commands/multitasking/project_daily. Flags: `--output RUTA`, `--force`, `--filter {charly,all}` (default charly), `--since/--until YYYY-MM-DD` (ventana inclusive, coffe-snj), `--config RUTA` (ver "Uso"). SUBSCRIPTIONS/MODEL_PRICING se cargan de `config/fpa.json` (coffe-mbz). |
| `scripts/viz-gantt.py` | Genera `data/gantt-multitasking.html`: Gantt de actividad proyecto × día con concurrencia diaria. Autocontenido, sin dependencias. |
| `scripts/viz-dashboard.py` | Genera `data/dashboard.html`: dashboard de insights (tendencia mensual, costo por herramienta, top proyectos, heatmap dow×hora, skills, comandos, sesiones, timeline de herramientas). Autocontenido, SVG puro. |
| `scripts/viz-fpa.py` | Genera `data/fpa-dashboard.html`: dashboard FP&A (presupuestos, bridge PVM, forecast, alertas, economía de suscripción). Un solo HTML autocontenido, **SVG inline, sin librería de charts externa** (FPA-145); las matemáticas se pre-calculan en Python y el JS solo re-escala. Config en `config/fpa.json`. Flags: `--check-docs` (consistencia README↔JSON, FPA-143). |

### Datos generados

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `data/usage_report_v3.json` | 766K | **Reporte principal.** Interacciones filtradas solo charly. Incluye hourly, daily, monthly, projects, sessions, skills, commands, multitasking, project_daily (matriz para el Gantt). Última regeneración: 2026-09-20 (140,564 interacciones). |
| `data/dashboard.html` | 25K | **Dashboard de insights.** Tendencias mensuales, uso por proyecto, skills, comandos, heatmap, sesiones, timeline de herramientas. En <https://charly-vibes.github.io/coffee/data/dashboard.html>. |
| `data/gantt-multitasking.html` | 41K | **Visualización Gantt.** Actividad por proyecto/día, fila de concurrencia diaria, toggle interacciones/presencia, tooltips. Abrir en navegador (o en <https://charly-vibes.github.io/coffee/data/gantt-multitasking.html>). |
| `data/fpa-dashboard.html` | 1.7M | **Dashboard FP&A.** Resumen ejecutivo, KPIs, presupuestos, bridge precio-volumen-mix, forecast, alertas, economía de suscripción, patrones de uso. 5 vistas + selector de periodo; export CSV/SVG; share-URL. En <https://charly-vibes.github.io/coffee/data/fpa-dashboard.html>. |
| `data/usage_report_v2.json` | 285K | Reporte v2 sin filtrar. 94,115 interacciones (incluye proyectos no-charly). |
| `data/usage_hourly.json` | 399K | Datos hora a hora de v2 (sin filtrar). |
| `data/daily_summary.json` | 33K | Resumen diario v2. |
| `data/tool_timeline.json` | 1.6K | Timeline de herramientas (primera/última vez). |

### Documentos

| Archivo | Contenido |
|---------|-----------|
| `data/resumen-datos-v3.md` | **Resumen final.** Datos filtrados solo charly, con tablas mensuales, sesiones, skills, comandos, proyectos top. Refleja el snapshot de 2026-06-10; el JSON actual ya lo supera (ver nota abajo). |
| `data/resumen-datos-2026-06-10.md` | Resumen preliminar v2 (sin filtrar). |

> **Nota:** el boceto de la serie vive en `microdancing/drafts/serie-aprendizaje-6-meses-boceto.md`, no en este repo.

> **Nota de vigencia (2026-09-20):** `usage_report_v3.json` fue regenerado el 2026-09-20 con el periodo hasta septiembre (140,564 interacciones, 40 proyectos; coffe-6i8 arregló el schema: `tokens_by_model` a 2 niveles y `concurrency.reason` nullable). Las cifras de `resumen-datos-v3.md` y de la sección "Estado de los datos" reflejan el snapshot de 2026-06-10 (81,887 interacciones); son históricas, no están actualizadas.

Los JSON en `data/` son **derivados**: la fuente son los logs locales de cada herramienta (`~/.claude`, `~/.pi/agent`, `~/.amp`), que no están versionados. En una máquina sin esos logs el tracker no produce datos reales (ver guard en `main()`).

## Uso / Reproducibilidad

Requisitos: Python ≥ 3.9 — solo stdlib, sin dependencias que instalar.

### Tests

```bash
python3 tests/test_tracker.py   # funciones puras + golden de aggregate() (24 tests)
python3 tests/test_viz.py       # smoke de los HTML en Chromium real (opcional: playwright)
REGEN_GOLDEN=1 python3 tests/test_tracker.py  # regenerar golden (revisar diff antes de aceptar)
```

El contrato del reporte está spec'd en `specs/usage-report-v3.schema.json`;
los viz scripts lo validan con `--validate` (requiere `jsonschema`, opcional).

```bash
python3 scripts/usage-tracker.py   # regenera data/usage_report_v3.json (requiere los logs locales)
python3 scripts/usage-tracker.py --since 2026-01-01 --until 2026-06-30 --output data/usage_report_v2.json
                                   # subconjunto reproducible: ventana temporal (extremos inclusive, fechas UTC; coffe-snj)
python3 scripts/viz-gantt.py       # regenera data/gantt-multitasking.html desde el JSON
python3 scripts/viz-dashboard.py   # regenera data/dashboard.html desde el JSON
python3 scripts/viz-fpa.py         # regenera data/fpa-dashboard.html desde el JSON
python3 scripts/viz-fpa.py --check-docs  # verificar cifras del README (FPA-143)
python3 scripts/viz-gantt.py [reporte.json] [salida.html]  # rutas alternativas (viz-dashboard.py igual)
```

Notas de reproducibilidad entre máquinas:

- El tracker **no sobreescribe** el reporte si extrae < 1,000 interacciones (máquina sin logs); usa `--force` para forzar.
- Con `--since/--until` (ventana temporal, extremos inclusive) la extracción es un subconjunto: el umbral de 1,000 no aplica (una ventana angosta legítimamente extrae poco), se registra la ventana pedida en `metadata.window`, y **es obligatorio `--output`** (o `--force`) para no pisar el dataset principal de `data/` con un subconjunto.
- Los buckets hourly/daily usan la **TZ local** de la máquina que extrae (`LOCAL_TZ` en el script): dos máquinas con TZ distinta producen agregaciones horarias distintas.
- Las cuotas de suscripción y los precios por modelo ya NO están hardcoded: el tracker los carga de **`config/fpa.json`** (`subscriptions` y `model_pricing` versionado por fecha efectiva, coffe-mbz). Para cambiar precios/planes editá el config. Si no hay config disponible, usa constantes hardcodeadas como fallback con un warning; `--config RUTA` (o env `TRACKER_CONFIG`) apunta a otro config — una ruta explícita inexistente aborta con error. El reporte lo documenta: `metadata.config_source` y `model_pricing_config` reflejan lo cargado.

### GitHub Pages

El deploy es vía **GitHub Actions** (no hay branch `gh-pages`): `.github/workflows/deploy-pages.yml` publica un índice (`index.html`), el Gantt (regenerado en CI) y los JSON de `data/` en cada push a `main`. Único requisito manual: Settings → Pages → Source: *GitHub Actions*.

## Estado de los datos

<!-- CHECK-DOCS:BEGIN -->
Cifras actuales del reporte, verificadas por
`python3 scripts/viz-fpa.py --check-docs` contra `data/usage_report_v3.json`
(FPA-143; corre en CI y falla el build ante cualquier desvío, FPA-107):

- Interacciones: 141,549
- Proyectos: 42
- Costo efectivo: $3,814.20
- Costo real: $564.86
- Cash real (ledger): $1,086.73
- Sesiones: 1,884
- Periodo: 2026-01-11 → 2026-09-20
<!-- CHECK-DOCS:END -->

Nota: `Costo real` es la suma mensual del tracker (fees implícitos del
calendario + p2p tracker, *assumed*); `Cash real (ledger)` es el cash
real pagado según el ledger `data/charges.json` (*reported*, FPA-003;
coffe-a31.2/3). Ambos números no se suman entre sí (FPA-002): efectivo
es la estimación del tracker, cash es la factura real de los proveedores
y difieren porque las cuotas implícitas son un calendario, no un gasto.

### ✅ Extraído y documentado

- **81,887 interacciones** de enero 11 a junio 10 (solo charly)
- **3 fuentes:** Claude CLI, Pi (Codex + Gemini CLI + OpenRouter), Amp
- **Filtro charly:** excluye proyectos ak, sk-, phorma, ~/Downloads, etc.
- **Mensual:** enero (929 Amp), febrero (719), marzo (263), abril (20,671), mayo (57,647), junio (1,658)
- **Modelos:** Sonnet 4.6 (~55K), Opus 4.6/4.7 (~12K), GPT-5.4 (~9K), GPT-5.5 (~3K), Gemini 3 Pro (~500), DeepSeek V4 (~400)
- **Herramientas:** claude-cli, codex, gemini-cli, openrouter, amp, copilot
- **Costo efectivo:** $3,160.94
- **Costo real (estimado):** $65.58 (con suscripciones)
- **1,884 sesiones:** 48% cortas (1-10 turns), 18% autónomas (con Agent)
- **Skills:** 29, lidera rule-of-5-universal (115 usos)
- **Comandos:** 49, /clear domina (307), /rule-of-5-universal (62)
- **Multitasking (nuevo):** 54.6% de horas activas con ≥2 proyectos simultáneos, promedio 2.31 proyectos/hora, máximo 10 proyectos en una misma hora (2026-07-27 22:00). 51% de días con ≥2 proyectos.
- **38 proyectos charly** (tras normalizar nombres duplicados entre fuentes; antes contaban 59)
- **38 proyectos:** miblioteca ($870), atril ($471), dont ($403) top 3

## Lo único que sigue sin resolver

- **Enero 1-10.** Información no disponible. Los primeros commits (jams, fabbro) son del 6-7 de enero pero no hay logs de qué herramienta se usó. Amp arranca recién el 11. Posiblemente Claude Code sin persistencia de sesiones en ese entonces.
- **Fechas exactas de suscripción.** En el script uso estimaciones (Pro $20 → Max $100 → Pro $20). Pendiente confirmar fechas exactas.

### 📊 Posibles visualizaciones

Con los datos actuales podemos generar:

1. **Gráfica mensual:** interacciones + costo, con línea de creación de repos superpuesta
2. **Timeline de herramientas:** cuándo entró y salió cada herramienta/modelo
3. **Distribución de sesiones:** histograma de largos de sesión (1-10, 11-50, 51-100, 100+)
4. **Autonomía en el tiempo:** % de sesiones con Agent por mes
5. **Costo real vs efectivo:** barras apiladas mostrando suscripción vs pay-per-token
6. **Heatmap hora a día:** qué horas del día se usaba más la IA (los datos ya están en usage_report_v3.json)

## Próximos pasos

1. [x] ~~Confirmar fechas exactas de suscripción Claude (Pro→Max→Pro)~~ ✅ **Mar 19 Pro → Abr 19 Max → Jun 19 Pro**
2. [ ] Investigar gap de enero 1-10 (¿Claude web? ¿Cursor?)
3. [x] ~~Generar dashboard HTML con Chart.js~~ ✅ **Descartado: `scripts/viz-fpa.py` genera `data/fpa-dashboard.html` con SVG inline, stdlib-only (FPA-145)**
4. [ ] Empezar a escribir post principal con datos reales
5. [ ] Interpretar el Gantt: los gaps sin actividad (vacaciones?) y los bloques densos de julio-agosto (¿migración masiva? ¿agentes paralelos?)