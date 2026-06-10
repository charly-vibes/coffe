# Serie de aprendizaje — Tracking de datos

Branch: `data/datos-uso-ia`
Propósito: recolectar, procesar y documentar los datos de uso de IA de los últimos 6 meses para la serie de posts.

## Archivos en esta branch

### Scripts

| Archivo | Propósito |
|---------|-----------|
| `scripts/usage-tracker.py` | Extractor de uso de IA v3. Lee datos de Claude, Pi, Amp, Gemini. Filtra solo proyectos charly. Produce reporte JSON con hourly/daily/monthly/projects/sessions/skills/commands. |

### Datos generados

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `data/usage_report_v3.json` | 283K | **Reporte principal.** 81,887 interacciones filtradas solo charly. Incluye hourly (479 horas), daily (96 días), monthly (6 meses), projects (48), sessions (1,884), skills (29), commands (49). |
| `data/usage_report_v2.json` | 285K | Reporte v2 sin filtrar. 94,115 interacciones (incluye proyectos no-charly). |
| `data/usage_hourly.json` | 399K | Datos hora a hora de v2 (sin filtrar). |
| `data/daily_summary.json` | 33K | Resumen diario v2. |
| `data/tool_timeline.json` | 1.6K | Timeline de herramientas (primera/última vez). |

### Documentos

| Archivo | Contenido |
|---------|-----------|
| `data/resumen-datos-v3.md` | **Resumen final.** Datos filtrados solo charly, con tablas mensuales, sesiones, skills, comandos, proyectos top. |
| `data/resumen-datos-2026-06-10.md` | Resumen preliminar v2 (sin filtrar). |
| `drafts/serie-aprendizaje-6-meses-boceto.md` | **Boceto de la serie.** Evolución v1→v2→v3 con todos los temas y datos reales. |

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
- **48 proyectos charly:** miblioteca ($870), atril ($471), dont ($403) top 3

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