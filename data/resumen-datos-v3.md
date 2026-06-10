---
title: "Resumen de datos — v3 final (charly-only)"
date: 2026-06-10
---

# Resumen de datos extraídos (v3, solo charly)

Extraído con `scripts/usage-tracker.py` el 2026-06-10.

## Resumen general

| Métrica | Valor |
|---------|-------|
| Interacciones únicas | **81,887** (deduplicado de 82,166 crudas) |
| Rango de fechas | **2026-01-11 → 2026-06-10** |
| Horas con actividad | **479** |
| Días activos | **96** |
| Proyectos (charly) | **48** |
| Costo efectivo | **$3,160.94** (pay-per-token estimado) |
| Costo real | **$65.70** (Pro $20/mes → Max $100/mes → Pro $20/mes) |
| Tokens input consumidos | ~73.4M |
| Tokens output generados | ~61.1M |

**Nota sobre costos:** fechas reales de suscripción: Pro $20/mes (Mar 19 → Abr 19), Max $100/mes (Abr 19 → Jun 19), Pro $20/mes (Jun 19 → presente). El costo real de $65.70 corresponde a Codex pay-per-token post-mayo 15 y OpenRouter.

**Amp es @ampcode/cli** (agente autónomo). Sus 2,281 interacciones son escrituras de archivos sin costo directo (ya cubierto por suscripción o plan gratuito). Amp dominó enero-febrero (1,648 cambios) y fue reemplazado por Claude CLI a partir de marzo.

## Mensual (solo charly)

| Mes | Reqs | Costo efectivo | Costo real | Herramientas | Modelos dominantes |
|:---|:---:|:---:|:---:|:---|:---|
| **Enero** | 929 | $0 | $0 | Amp | — (solo Amp) |
| **Febrero** | 719 | $0 | $0 | Amp | — |
| **Marzo** | 263 | $0 | $0 | Amp | — |
| **Abril** | 20,671 | $1,109.93 | $0 | Claude CLI (13,855), Codex (5,738), Gemini (823), Amp (253) | Sonnet 4.6 (10,733), GPT-5.4 (5,594), Opus 4.6 (3,120) |
| **Mayo** | 57,647 | $2,047.18 | $61.76 | Claude CLI (51,494), Codex (6,074), Amp (43) | Sonnet 4.6 (42,969), Opus 4.7 (4,358), Opus 4.6 (4,094), GPT-5.4 (3,240) |
| **Junio** | 1,658 | $3.83 | $3.83 | Claude CLI (1,359), OpenRouter (204), Codex (95) | Sonnet 4.6 (1,355), DeepSeek V4 (202) |

## Sesiones (Claude, charly)

| Métrica | Valor |
|:--------|:-----:|
| Sesiones totales | **1,884** |
| Con herramienta Agent (autónomas) | **346 (18%)** |
| Turnos promedio | 27 |
| Herramientas distintas promedio | 2.4 |
| Errores de API | 2 |
| Compactaciones | 9 |

### Distribución de largos de sesión

| Turnos | Sesiones |
|:------:|:--------:|
| 1–10 | 914 (48%) |
| 11–50 | 700 (37%) |
| 51–100 | 167 (9%) |
| 101–300 | 94 (5%) |
| 301–500 | 8 (0.4%) |
| 500+ | 1 (0.05%) |

### Sesiones más largas

| Turnos | Msgs | Fecha | Proyecto |
|:-----:|:----:|:-----:|:---------|
| **1,001** | 723 | 2026-05-12 | miblioteca |
| 480 | 322 | 2026-04-22 | atril |
| 398 | 245 | 2026-05-05 | sk-XAct-jl |
| 393 | 248 | 2026-04-30 | sk-REPLy-jl |
| 360 | 248 | 2026-05-12 | miblioteca |
| 354 | 262 | 2026-05-15 | miblioteca |
| 336 | 230 | 2026-04-23 | atril (6h de duración) |
| 316 | 214 | 2026-05-11 | dont |
| 266 | 188 | 2026-05-15 | dont |
| 265 | 182 | 2026-04-28 | atril |

## Skills más usados

| Skill | Usos | Proyecto principal |
|:------|:----:|:-----------------|
| rule-of-5-universal | 115 | miblioteca |
| commit | 75 | miblioteca / atril |
| issue-review | 38 | miblioteca |
| rule-of-5 | 22 | wai |
| openspec-proposal | 8 | — |
| grill-me | 5 | — |
| openspec-archive | 5 | — |
| openspec:proposal | 4 | — |
| tdd | 4 | espectacular |
| resume-handoff | 3 | ruta |

## Comandos slash más usados

| Comando | Usos |
|:--------|:----:|
| /clear | 307 |
| /rule-of-5-universal | 62 |
| /rate-limit-options | 54 |
| /close | 19 |
| /resume | 15 |
| /commit | 12 |
| /add-dir | 10 |
| /model | 9 |
| /skills | 7 |
| /issue-review | 7 |

## Proyectos top

| Proyecto | Costo efectivo | Interacciones | Herramientas top | Skills top |
|:---------|:------------:|:------------:|:----------------|:----------|
| miblioteca | $869.97 | 22,876 | Claude CLI | rule-of-5, commit |
| atril | $471.21 | 5,527 | Claude CLI | commit, rule-of-5 |
| dont | $403.29 | 15,523 | Claude CLI | rule-of-5, commit |
| sk-REPLy-jl | $201.39 | 4,758 | Claude CLI | commit |
| wai | $146.70 | 4,437 | Claude CLI | rule-of-5 |
| pretender | $77.62 | 4,466 | Claude CLI | rule-of-5 |
| superficies | $70.51 | 1,898 | Claude CLI | commit, rule-of-5 |
| tRAGar | $66.28 | 1,640 | Claude CLI | rule-of-5, commit |
| espectacular | $51.79 | 1,153 | Claude CLI | rule-of-5, tdd, grill-me |
| fotos | $35.87 | 1,113 | Claude CLI | rule-of-5 |
| paranoid | $29.96 | 858 | Claude CLI | issue-review, rule-of-5 |
| incitaciones | $3.96 | 127 | Claude CLI | rule-of-5 |

## Comentarios sobre los datos

1. **Enero-marzo sin Claude.** Los datos de Claude arrancan el 16 de marzo. Antes de eso solo hay Amp (cambios de archivos autónomos) y no hay registro de qué herramienta se usó. Los posts de enero (Resonant Coding, el blog) y los primeros repos (jams, incitaciones, nayra) aparecen en los commits pero no en los logs de sesiones.

2. **Posible explicación:** el user usaba Claude web o Cursor antes de adoptar Claude CLI. No hay logs locales de esas herramientas. Los commits de jams (6 de enero) tienen el autor "Charly Vibes" que es el que usa Claude, así que probablemente era Claude Code (que sí guarda historial, pero las sesiones muy viejas se limpiaron).

3. **Amp data.** 2,281 interacciones de Amp, distribuidas: enero (929), febrero (719), marzo (263), abril (253), mayo (43). Muestra un claro decline: Amp se usaba mucho al principio, después fue reemplazado por Claude CLI y Codex.

4. **Costos.** Con la configuración actual de suscripciones, el costo real es solo $65.58 de los $3,160.94 efectivos. La mayor parte del uso cayó dentro del período de suscripción. Los $65.58 reales corresponden a junio y parte de mayo (cuando ya estaba en pay-per-token o Max).

## Archivos generados

- `data/usage_report_v3.json` (~12MB) — reporte completo con hourly, daily, monthly, projects, sessions, skills, commands
- `scripts/usage-tracker.py` — script que genera el reporte