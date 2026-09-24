## ADDED Requirements

### Requirement: banda de sensibilidad de caché por mes

El reporte SHALL (debe) emitir `monthly[m].energy_kwh_band: {low, high}` —
kWh estimados recomputados con `cache_read_energy_factor` 0.0 y 1.0
respectivamente, mismos buckets, coeficientes versionados y `energy_version`
que la emisión nominal de 7mj.1. Los meses que emiten `energy_kwh: null`
deben emitir banda `null` con la misma razón. La metadata SHALL (debe)
registrar `energy_band_cache_factors: [0.0, 1.0]`.

#### Scenario: extremos de banda coherentes con el nominal

- **WHEN** un mes tiene tokens con cache_read > 0 y telemetría completa
- **THEN** `energy_kwh_band.low ≤ energy_kwh ≤ energy_kwh_band.high` y los
  extremos coinciden con recomputar el método 7mj con factor 0.0 y 1.0

#### Scenario: mes sin telemetría hereda null

- **WHEN** un mes solo tiene modelos sin telemetría de tokens (p.ej. amp)
- **THEN** `energy_kwh_band` es `null` con la misma razón que `energy_kwh`
