---
title: "Boceto v3 — Datos reales extraídos"
date: 2026-06-10
status: boceto-v3
---

# Datos reales extraídos (2026-06-10)

Ejecución de `scripts/usage-tracker.py v2` sobre datos locales.

## Resumen

| Métrica | Valor |
|---------|-------|
| Interacciones únicas | **94,115** |
| Horas con actividad | **332** |
| Días activos | **47** |
| Proyectos detectados | **68** |
| Herramientas | claude-cli, codex, copilot, gemini-cli, openrouter |
| Skills usados | 29 |
| Comandos slash | 49 |
| Costo efectivo (pay-per-token) | **$3,483** |
| Costo real estimado | **$3,008** |
| Tokens input | 81.6M |
| Tokens output | 63.2M |

## Línea de tiempo de herramientas

### Marzo 2026 — Comienza Claude CLI
- **547 interacciones**, $66.91 costo efectivo, **$0 real** (suscripción)
- Solo Claude Opus 4.6
- Uso esporádico

### Abril 2026 — Explosión
- **21,823 interacciones**, $1,260.24 efectivo, **$1,074.22 real**
- Entra Codex (GPT-5.4): 5,989 interacciones
- Claude se diversifica: Sonnet 4.6 domina (11,299), Opus 4.6 cae a 3,510
- Gemini CLI aparece (862 interacciones)
- Copilot: 2 interacciones (prueba)
- ~36.5M tokens input, ~13.6M output

### Mayo 2026 — Pico absoluto
- **69,363 interacciones**, $2,150.97 efectivo, **$1,929.20 real**
- Claude CLI domina: 62,453 interacciones (90%)
- Opus 4.7 entra (5,768), Opus 4.6 se mantiene (5,592), Sonnet 4.6 explota (50,481)
- Codex cae a 6,854, Gemini desaparece casi
- ~38.3M tokens input, **~48.6M output** (más output que input = sesiones largas de edición)

### Junio 2026 — La pausa (parcial, 10 días)
- **2,860 interacciones**, $4.95 real
- Claude CLI aún domina (2,304), OpenRouter entra (448, DeepSeek)
- Caída del 96% respecto a mayo

## Skills más usados

| Skill | Usos | Proyecto top |
|-------|:----:|-------------|
| rule-of-5-universal | 119 | miblioteca |
| commit | 76 | miblioteca / atril |
| issue-review | 38 | miblioteca |
| rule-of-5 | 22 | wai |
| openspec-proposal | 8 | — |
| grill-me | 5 | — |
| openspec-archive | 5 | — |
| tdd | 4 | espectacular |
| resume-handoff | 3 | ruta |
| close | 2 | — |
| ui-align | 2 | — |
| narrative-article | 1 | — |
| anti-slop-prose | 1 | — |
| implement-plan | 1 | — |

## Herramientas más usadas

| Herramienta | Usos |
|:-----------|:----:|
| Bash | 27,086 |
| Read | 12,625 |
| Edit | 9,589 |
| Write | 1,827 |
| Agent | 748 |
| Grep | 709 |
| Glob | 478 |
| Skill | 307 |
| Playwright (total) | ~1,019 |
| ToolSearch | 106 |
| TodoWrite | 60 |

## Proyectos top por costo

| Proyecto | Costo efectivo | Interacciones | Skills principales |
|:---------|:------------:|:------------:|:------------------|
| miblioteca | $869.97 | 22,876 | rule-of-5, commit, issue-review |
| atril | $471.21 | 5,527 | commit, rule-of-5, issue-review |
| dont | $403.29 | 15,523 | rule-of-5, commit, issue-review |
| sk-REPLy-jl | $201.39 | 4,758 | commit, rule-of-5, issue-review |
| wai | $146.70 | 4,437 | rule-of-5, commit |
| ak | $132.53 | 739 | commit |
| pretender | $77.62 | 4,466 | rule-of-5, issue-review |
| superficies | $70.51 | 1,898 | commit, rule-of-5 |
| tRAGar | $66.28 | 1,640 | rule-of-5, commit |
| espectacular | $51.79 | 1,153 | rule-of-5, tdd, grill-me |
| paranoid | $29.96 | 858 | issue-review, rule-of-5, commit |
| incitaciones | $3.96 | 127 | rule-of-5 |

## Modelos (desagregado fine)

| Modelo | Interacciones | Tool principal |
|:------|:------------:|:--------------|
| Claude Sonnet 4.6 | ~63,855 | Claude CLI |
| GPT-5.4 (Codex) | ~9,787 | Pi/Codex |
| Claude Opus 4.6 | ~9,336 | Claude CLI |
| Claude Opus 4.7 | ~5,768 | Claude CLI |
| GPT-5.5 (Codex) | ~3,014 | Pi/Codex |
| Gemini 3 Pro | ~553 | Pi/Gemini |
| DeepSeek V4 Flash | ~408 | Pi/OpenRouter |
| Gemini 3 Flash | ~259 | Pi/Gemini |
| GPT-5.3 (Codex) | ~146 | Pi/Codex |
| Gemini 2.5 Pro | ~86 | Pi/Gemini |
| Kimi K2 | ~6 | Pi/OpenRouter |
| Gemini 3.1 Pro | ~43 | Pi/Gemini |

## Costo real vs efectivo

El reporte actual usa estas suposiciones de suscripción (configurables en `SUBSCRIPTIONS`):

| Herramienta | Período suscripción | Fee mensual |
|:-----------|:-------------------|:-----------:|
| Claude CLI | Mar 1 → Abr 15 | $20/mes |
| Claude CLI | Abr 16 → presente | pay-per-token |
| Codex | Abr 1 → May 15 | $10/mes |
| Codex | May 16 → presente | pay-per-token |

**Necesito que revises estas fechas y montos.** ¿Cuándo pasaste exactamente de suscripción a pay-per-token en cada herramienta? ¿Era Claude Pro ($20) o Max ($200)?

## Lo que FALTA / se puede mejorar

1. **Data de enero-febrero 2026.** No hay sesiones de Claude anteriores a marzo 16 en los datos locales. ¿Usabas Claude web antes? ¿Cursor? ¿Los primeros posts (enero) se escribieron con qué herramientas?
2. **Código generado por repo.** Podemos correr `git log --stat` y `tokei` en cada repo para tener líneas de código y commits por período.
3. **Dashboard HTML.** El JSON ya tiene toda la data hora a hora. Podemos generar un HTML con Chart.js similar a `llm-dashboard.py` pero con las nuevas métricas (herramientas, skills, proyectos, costo real vs efectivo).
4. **Línea de tiempo visual repos + uso.** Superponer creación de repos sobre las series de uso.

---

*Archivos generados: `data/usage_report_v2.json` (~6MB). Script: `scripts/usage-tracker.py`*