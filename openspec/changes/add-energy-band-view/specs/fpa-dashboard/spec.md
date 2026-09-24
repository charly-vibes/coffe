## ADDED Requirements

### Requirement: vista de energía estimada con banda

El Dashboard SHALL (debe) incluir una vista "Energía" (tab F8) que muestre los
kWh estimados por mes del reporte como barras con banda low–high
(`energy_kwh_band`), el total del periodo con su banda (18/33/175 kWh en el
dataset actual), los meses `null` visibles con su razón (loss visible, no
silenciosa) y el tag *assumed* en toda cifra derivada de coeficientes. La
vista SHALL (debe) cumplir accesibilidad y mobile igual que las demás: readout
persistente por hover/focus/tap, touch targets ≥ 44×44 px y single-column
< 600px. El caption SHALL (debe) explicar que los extremos corresponden a 0% y
100% de acierto de caché y que el escenario base usa el factor nominal (10%).

#### Scenario: banda visible en la vista energía

- **WHEN** se abre la vista Energía con el dataset que tiene meses con telemetría
- **THEN** cada mes muestra su kWh nominal dentro de la banda low–high y el
  total del periodo muestra la banda completa con tag *assumed*

#### Scenario: mes sin telemetría visible con razón

- **WHEN** un mes tiene `energy_kwh` 0.0 porque sus modelos emitieron `null`
  con razón (sin telemetría)
- **THEN** la vista lo marca como sin telemetría y expone las razones por
  modelo, no lo presenta como una medición de cero kWh

#### Scenario: smoke de la vista energía

- **WHEN** el smoke test carga el dashboard y activa el tab Energía
- **THEN** la vista renderiza sin errores de consola y su total es legible en
  el readout accesible
