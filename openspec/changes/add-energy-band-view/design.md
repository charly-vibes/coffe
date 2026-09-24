## Context

coffe-7mj dejó `energy_kwh` mensual en el reporte (nominal, cache factor 0.10)
pero el dashboard no lo muestra. La banda 18/33/175 kWh del README es el rango
al variar el multiplicador de cache_read (0% / 10% / 100%): es el parámetro
dominante y el dashboard debería mostrar la incertidumbre, no solo el punto.

## Goals / Non-Goals

- Goals: banda visible en el dashboard (por mes y total), sin perder las
  garantías 7mj (provenance assumed, loss visible, bucketing mensual)
- Non-Goals: no recalibrar coeficientes, no cambiar el método de 7mj, no medir
  energía real, no tocar las 6 vistas existentes

## Decisions

- **Banda computada en el tracker, no en el viz.** El viz no conoce tiers ni
  coeficientes; duplicar la aritmética en JS rompería la fuente única de verdad
  (y el patrón de paridad JS/Python de F3). El tracker ya tiene `energy_for()`
  y emite por bucket — la banda es el mismo cálculo con factor 0.0/1.0.
  Alternativa descartada: pasar `energy_coefficients` al HTML (expone config y
  duplica lógica).
- **Emisión aditiva con misma energy_version.** `energy_kwh_band` comparte
  bucket y versión con `energy_kwh`; si el config cambia, ambos cambian juntos.
- **Vista nueva (tab) en vez de mezclar en Costo.** La energía no es dinero;
  mezclar unidades en la vista de costo confundiría el bridge precio-volumen.
  Tab separado = reusa el patrón F6 (tabs/VIEWS/readout) y mantiene scope chico.

## Risks / Trade-offs

- Crecimiento de viz-fpa.py (ya 4.7k líneas) → vista F8 aislada, sin refactor
  de vistas existentes; si crece más, extracción futura.
- Banda high (factor 1.0) puede alarmar → caption explícito: los extremos son
  0% y 100% de acierto de caché, el 10% nominal es el escenario base.
- Regen persigue blanco móvil (gotcha 7mj.2) → pasada atómica final (tarea 3.1).

## Open Questions

- Ninguno bloqueante; el etiquetado de la banda (low/high vs p0/p100) se
  resuelve en implementación siguiendo el tono del dashboard.
