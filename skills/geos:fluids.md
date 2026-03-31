---
name: geos:fluids
description: Compute fluid PVT properties for GEOS simulations (all SI units).
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools. All inputs and outputs are in SI units.

## Tools
- `compute_gas_properties(pressure_Pa, temperature_K, specific_gravity)` — Z, density, viscosity, Bg, Cg
- `compute_oil_properties(pressure_Pa, temperature_K, api, gas_sg, rsb)` — Pb, Rs, Bo, density, viscosity
- `compute_brine_properties(pressure_Pa, temperature_K, salinity_wt_pct)` — density, viscosity, Bw
- `generate_pvt_table(fluid_type, pressure_range_Pa, temperature_K)` — full table
- `generate_rel_perm(model, swc, sorg, exponents, n_rows)` — relative permeability table
- `generate_cap_pressure(model, entry_pressure_Pa, swc, exponent)` — capillary pressure curve
- `recommend_fluid_model(description)` — NL → GEOS solver + full constitutive assembly

## recommend_fluid_model Output

This tool returns a complete constitutive assembly:
- `solver`: Solver element type (e.g., "SinglePhaseFVM", "CompositionalMultiphaseFVM")
- `solver_attrs`: Extra solver attributes if needed (e.g., {"isThermal": "1"} for thermal)
- `material_list`: Names for CellElementRegion materialList (e.g., ["water", "rock"])
- `constitutive_elements`: Full list of ALL elements to add to Constitutive section, including:
  - Fluid model
  - Coupled solid (CompressibleSolidConstantPermeability)
  - NullModel, PressurePorosity, ConstantPermeability (sub-models)
  - Relative permeability (for multiphase)
  - Thermal models (for thermal coupling)

## Supported Physics Keywords
- "single phase", "water", "brine" → SinglePhaseFVM
- "thermal", "heat", "geothermal" → SinglePhaseFVM with isThermal="1"
- "dead oil", "black oil" → CompositionalMultiphaseFVM + DeadOilFluid
- "CO2", "carbon", "sequestration" → CompositionalMultiphaseFVM + CO2BrinePhillipsFluid
- "compositional", "multiphase", "EOS" → CompositionalMultiphaseFVM + CompositionalMultiphaseFluid
- "immiscible", "two-phase" → ImmiscibleMultiphaseFlow

## Units (ALL SI)
- Pressure: Pa (not psi, not bar)
- Temperature: K (not degF, not degC)
- Density: kg/m³
- Viscosity: Pa·s (not cP)
- Permeability: m² (not mD)
- Compressibility: 1/Pa
