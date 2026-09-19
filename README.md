# coffe — Tracking de uso de IA

Extractado de `microdancing` (branch `data/datos-uso-ia`, tip `09c063e`) para poder
reutilizar y extender el tracker independientemente de la serie de posts.
Propósito: recolectar, procesar y documentar el uso de IA (Claude CLI, Pi, Amp, Gemini)
de los últimos meses.

## Archivos

### Scripts

| Archivo | Propósito |
|---------|-----------|
| `scripts/usage-tracker.py` | Extractor de uso de IA v4.1. Lee datos de Claude, Pi (incluye Gemini vía google-gemini-cli) y Amp. Filtra solo proyectos charly. Produce reporte JSON con hourly/daily/monthly/projects/sessions/skills/commands/multitasking/project_daily. Flags: `--output RUTA`, `--force` (ver "Uso"). |
| `scripts/viz-gantt.py` | Genera `data/gantt-multitasking.html`: Gantt de actividad proyecto × día con concurrencia diaria. Autocontenido, sin dependencias. |
| `scripts/viz-dashboard.py` | Genera `data/dashboard.html`: dashboard de insights (tendencia mensual, costo por herramienta, top proyectos, heatmap dow×hora, skills, comandos, sesiones, timeline de herramientas). Autocontenido, SVG puro. |

### Datos generados

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `data/usage_report_v3.json` | 716K | **Reporte principal.** Interacciones filtradas solo charly. Incluye hourly, daily, monthly, projects, sessions, skills, commands, multitasking, project_daily (matriz para el Gantt). Última regeneración: 2026-09-19 (139,609 interacciones). |
| `data/dashboard.html` | 25K | **Dashboard de insights.** Tendencias mensuales, uso por proyecto, skills, comandos, heatmap, sesiones, timeline de herramientas. En <https://charly-vibes.github.io/coffe/data/dashboard.html>. |
| `data/gantt-multitasking.html` | 41K | **Visualización Gantt.** Actividad por proyecto/día, fila de concurrencia diaria, toggle interacciones/presencia, tooltips. Abrir en navegador (o en <https://charly-vibes.github.io/coffe/data/gantt-multitasking.html>). |
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

> **Nota de vigencia (2026-09-19):** `usage_report_v3.json` fue regenerado el 2026-09-19 con el periodo extendido hasta septiembre (139,609 interacciones, 40 proyectos). Las cifras de `resumen-datos-v3.md` y de la sección "Estado de los datos" reflejan el snapshot de 2026-06-10 (81,887 interacciones); son históricas, no están actualizadas.

Los JSON en `data/` son **derivados**: la fuente son los logs locales de cada herramienta (`~/.claude`, `~/.pi/agent`, `~/.amp`), que no están versionados. En una máquina sin esos logs el tracker no produce datos reales (ver guard en `main()`).

## Uso / Reproducibilidad

Requisitos: Python ≥ 3.9 — solo stdlib, sin dependencias que instalar.

```bash
python3 scripts/usage-tracker.py   # regenera data/usage_report_v3.json (requiere los logs locales)
python3 scripts/viz-gantt.py       # regenera data/gantt-multitasking.html desde el JSON
python3 scripts/viz-dashboard.py   # regenera data/dashboard.html desde el JSON
python3 scripts/viz-gantt.py [reporte.json] [salida.html]  # rutas alternativas (viz-dashboard.py igual)
```

Notas de reproducibilidad entre máquinas:

- El tracker **no sobreescribe** el reporte si extrae < 1,000 interacciones (máquina sin logs); usa `--force` para forzar.
- Los buckets hourly/daily usan la **TZ local** de la máquina que extrae (`LOCAL_TZ` en el script): dos máquinas con TZ distinta producen agregaciones horarias distintas.
- Las cuotas de suscripción (`SUBSCRIPTIONS`) y precios por modelo (`MODEL_PRICING`) están hardcoded en el script y afectan los cálculos de costo.

### GitHub Pages

El deploy es vía **GitHub Actions** (no hay branch `gh-pages`): `.github/workflows/deploy-pages.yml` publica un índice (`index.html`), el Gantt (regenerado en CI) y los JSON de `data/` en cada push a `main`. Único requisito manual: Settings → Pages → Source: *GitHub Actions*.

## Estado de los datos

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
3. [ ] Generar dashboard HTML con Chart.js
4. [ ] Empezar a escribir post principal con datos reales
5. [ ] Interpretar el Gantt: los gaps sin actividad (vacaciones?) y los bloques densos de julio-agosto (¿migración masiva? ¿agentes paralelos?)