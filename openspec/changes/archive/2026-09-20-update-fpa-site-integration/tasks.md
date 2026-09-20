# Tasks: update-fpa-site-integration

Pipeline por fase: TDD → ro5u (review rule-of-5) → fix → commit. Tickets bd se
crean al aprobar el change (epic + hijos por fase, con `metadata.files`).

## 0. Preparación

- [x] 0.1 Confirmar el nombre canónico (propuesta: "Uso y costos de IA") y
      definir la clave en `config/fpa.json` (p.ej. `site_name`)
- [x] 0.2 Traducir la guía al español y committearla como
      `docs/fpa-analyses-guide.md` (fuente de contenido; IDs FPA-xxx intactos)
- [x] 0.3 **Pase de grounding** afirmación por afirmación contra la
      implementación: fórmulas (FME, bridge PVM, cache-hit, break-even) contra
      las funciones puras; umbrales/defaults (dormancy 30, 25×, premium 3 meses,
      tolerancia de reconciliación) contra `config/fpa.json`; cifras
      ilustrativas del snapshot reemplazadas por cifras derivadas en generación
      o eliminadas. Corregir el texto de la guía, nunca el código
- [x] 0.4 Crear tickets bd del epic (fases 1–5)

## 1. Tema compartido + nombre llano (identidad visual)

- [x] 1.1 TDD: test de paridad de tokens (los generadores emiten el mismo
      `:root`/reglas desde `scripts/site-theme.py`)
- [x] 1.2 Extraer el `<style>` compartido de `viz-dashboard.py` a
      `scripts/site-theme.py` (mismos nombres de variables) e interpolarlo en
      `viz-index.py`
- [x] 1.3 Migrar `viz-fpa.py` al tema compartido: reemplazar paleta crema/carbón,
      quitar dark mode, adaptar clases del FPA (cards→paneles con sombra dura,
      sparklines, badges de provenance, KPI strip) a los tokens
- [x] 1.4 Nombre canónico: label llano del dashboard en headers/tabs/titles
      (desde config), sin "FP&A" en ningún label visible; TDD: test de
      nomenclatura que falla si un HTML generado contiene "FP&A"
- [x] 1.5 Verificar accesibilidad bajo el nuevo tema (contraste AA, targets 44px,
      no solo-color) y extender el smoke de Playwright con asserts de
      `font-family`/`background` computados
- [x] 1.6 Regen `data/fpa-dashboard.html` + goldens (diff esperado: CSS/labels);
      suite completa verde; ro5u; commit

## 2. Guía generada (parser + fpa-guide.html)

- [x] 2.1 TDD: parser stdlib del markdown español (`scripts/viz_fpa_guide.py`):
      19 análisis, 4 niveles por análisis, extracción de IDs FPA-xxx
- [x] 2.2 Emitir `data/fpa-guide.html` autocontenida en el tema del sitio, con
      nombre llano y sin cifras de snapshot (las que queden se derivan en
      generación del JSON actual)
- [x] 2.3 TDD: extensión de `--check-docs` que falla si el mapeo referencia un
      análisis inexistente o un umbral citado difiere del valor real en
      config/código
- [x] 2.4 Suite + ro5u + commit

## 3. Marginalia con progressive disclosure (FPA + Gantt)

- [x] 3.1 Declarar el mapeo análisis→superficie (5 vistas + Gantt; multitasking y
      ritmo también en el Gantt) anclado a IDs FPA-xxx; test de cobertura: todo
      análisis en ≥1 superficie
- [x] 3.2 TDD: affordance compacta por análisis (chip/botón "¿Qué es esto?",
      target 44px, `<button>` accesible) con tooltip nativo del teaser ELI5
- [x] 3.3 TDD: expansión in situ al seleccionar (nivel 2 completo, nivel 3
      colapsado, enlace a `fpa-guide.html#analisis-N`), funcional por tap en
      touch sin depender de hover
- [x] 3.4 Marginalia en `viz-gantt.py` para sus análisis mapeados (mismo módulo
      compartido de chips/notes) + Gantt migrado a `site-theme.py`
- [x] 3.5 Smoke Playwright a 390×844: chip→expansión interactiva sin pageerrors;
      evaluar visibilidad del chip; si pasa desapercibido, escalar a teaser de
      una línea visible (decisión basada en evidencia, documentada)
- [x] 3.6 Regen HTMLs + goldens; suite verde; ro5u; commit

## 4. Consolidación (eliminar insights)

- [x] 4.1 Eliminar `data/dashboard.html` y `scripts/viz-dashboard.py` del repo
      (git history los preserva); sin referencias restantes en tests/CI/justfile
- [x] 4.2 `viz-index.py`: Dashboard (nombre llano) como principal + Gantt; sin
      entrada para insights
- [x] 4.3 README: filas del insights eliminadas, jerarquía documentada,
      `--check-docs` alineado
- [x] 4.4 Regen `index.html`; suite + ro5u + commit

## 5. Cierre

- [x] 5.1 Doble corrida de todos los generadores: byte-idénticos salvo timestamp
      (determinismo)
- [x] 5.2 Suite completa + Playwright verde; `openspec validate --strict`
- [x] 5.3 Deploy Pages verificado en producción (tema, nombre llano, guía,
      marginalia, índice sin insights)
- [x] 5.4 Cerrar tickets bd, archivar change, push
