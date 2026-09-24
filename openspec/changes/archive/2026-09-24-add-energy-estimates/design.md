## Context
- La investigación (whisper branch notes topic `energia`, 2026-09-23) estableció:
  banda 17.7/33.4/174.7 kWh en 9 meses según el multiplicador de cache; el
  multiplicador de cache es la decisión dominante (no los coeficientes J/token).
- Anclas públicas: Google 0.24 Wh/prompt mediano Gemini Apps NO calibra CLI
  agéntico (diverge ×3–10 de los coeficientes per-token) — queda como cita de
  contexto, no como método.
- Convenciones de casa: provenance reported/assumed (FPA-013), config única
  fail-loud (coffe-mbz), campos n/a con razón (FPA-008), config versionada por
  fecha (model_pricing.versions, coffe-mbz).

## Goals / Non-Goals
- Goals: kWh estimado por modelo/mes en el reporte, con provenance y método
  reproducibles desde config; schema válido; TDD.
- Non-Goals: dashboard visual (follow-up); mediciones de hardware (imposible
  desde API); energía de entrenamiento amortizada; banda min/max en el reporte
  (el multiplicador central queda documentado, la banda es del viz futuro).

## Decisions
- **Mapping por tier, no por modelo exacto.** flash ≈ 0.03 J/token
  (MoE-cheap: deepseek-v4-flash, glm-5.3-flash, gemini flash, codex), mid ≈ 0.1
  (sonnet, gpt-5.4, glm-5.2), frontier ≈ 0.2 J/token (opus, gpt-5.5, gemini pro,
  deepseek pro). Mapping exacto en config con `default_tier` para modelos nuevos
  y el nombre del tier efectivo registrado por modelo (`energy_tier`) — nada de
  defaults silenciosos. El mapping lista TODAS las variantes de nombre presentes
  en el dataset (29 modelos: duplicados `google/…` vs `gemini-…`,
  `anthropic/…` vs `claude-…`, sufijos `:free`, `<synthetic>`).
- **Multiplicador de cache_read = 0.10**, explícito en config
  (`cache_read_energy_factor`), decisión central documentada en Data & method.
  Es el parámetro más sensible (banda ×10) y por eso vive en config, no en código.
- **Versionado por fecha** (`versions[].effective`), mismo patrón que
  model_pricing: los coeficientes caducan (Google reportó ×33 reducción per-query
  en 12 meses; EU AI Act Art. 53 forzará más disclosures).
- **Fail-loud si falta el bloque.** `energy_coefficients` es requerido en config
  (mismo criterio que SUBSCRIPTIONS/MODEL_PRICING en coffe-mbz); no se emite un
  reporte silenciosamente sin energía.
- **Provenance siempre `assumed`.** La energía nunca es reported: no hay
  telemetría de proveedores. Se registra el método en metadata
  (`energy_method`: "tokens × J/token por tier, cache_read × factor").
- **Unidades y pesos de cómputo.** `tokens_frescos` = input + output +
  cache_write a peso completo (×1.0: escribir KV es cómputo de prefill, cuenta
  como token fresco — el ×1.25 de model_pricing es pricing, no física);
  cache_read entra ponderado por `cache_read_energy_factor`. kWh mensual por
  modelo: `(fresh_tokens + cache_read × factor) × J_per_token / 3.6e6`.
- **Granularidad de versión: por bucket mensual.** La versión de coeficientes
  se elige con `effective` ≤ primer día del mes del bucket (a diferencia de
  `estimate_cost(when)`, que es por interacción): `tokens_by_model` es un
  agregado mensual y partir un mes entre versiones exigiría acumulación por
  interacción sin valor estadístico. Mes anterior a toda versión → abort
  loud (el autor de config cubre el rango de datos, criterio fail-loud).

## Risks / Trade-offs
- Cifras de orden de magnitud, no mediciones → mitigado por provenance assumed
  + método visible + coeficientes versionados.
- Tier default puede mal-clasificar un modelo nuevo → `energy_tier` por modelo
  hace la clasificación auditable en el reporte; el default queda registrado.
- Regeneración del dataset puede romper goldens dataset-derived (fpa-summary,
  fpa-f2) → REGEN_GOLDEN=1 tras regen, igual que coffe-85z.

## Migration Plan
Aditivo: campos nuevos en el reporte y en el schema; nada existente cambia de
semántica. Rollback = revertir config + regenerar dataset.

## Open Questions
- Ninguna abierta para el reporte; la banda visual en el dashboard queda como
  follow-up a decidir después de ver las cifras en el reporte.
