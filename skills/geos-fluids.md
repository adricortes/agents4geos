---
name: geos-fluids
description: Compute fluid PVT properties for GEOS simulations (all SI units).
---

Fluid property computation using pyResToolbox (SI units).

## Tools
- `compute_gas_properties(pressure_Pa, temperature_K, specific_gravity)` — Z, density, viscosity, Bg, Cg
- `compute_oil_properties(pressure_Pa, temperature_K, api, gas_sg, rsb)` — Pb, Rs, Bo, density, viscosity
- `compute_brine_properties(pressure_Pa, temperature_K, salinity_wt_pct)` — density, viscosity, Bw
- `generate_pvt_table(fluid_type, pressure_range_Pa, temperature_K)` — full table
- `recommend_fluid_model(description)` — NL → GEOS solver + constitutive models
