---
name: geos:relperm
description: Generate relative permeability and capillary pressure curves.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools.

## Tools
- `generate_rel_perm(model, swc, sorg, exponents, n_rows)` — Brooks-Corey, VanGenuchten, or LET
- `fit_rel_perm(measured_S, measured_Kr, model)` — fit model to lab data
- `generate_cap_pressure(model, entry_pressure_Pa, swc, exponent)` — Pc curve

## GEOS Relative Permeability Models
In GEOS, relative permeability is specified via BrooksCoreyRelativePermeability element:
```xml
<BrooksCoreyRelativePermeability
  name="relperm"
  phaseNames="{ oil, gas, water }"
  phaseMinVolumeFraction="{ 0.1, 0.15, 0.15 }"
  phaseRelPermExponent="{ 2.0, 2.0, 2.0 }"
  phaseRelPermMaxValue="{ 0.8, 0.9, 0.9 }"/>
```

Key parameters:
- `phaseNames`: must match fluid model phases
- `phaseMinVolumeFraction`: residual saturation per phase
- `phaseRelPermExponent`: Brooks-Corey exponent per phase (higher = more curvature)
- `phaseRelPermMaxValue`: endpoint relative permeability per phase

For 3-phase (oil-gas-water), there are also Baker and Stone II models:
- BrooksCoreyBakerRelativePermeability: separate water-oil and gas-oil curves
- BrooksCoreyStone2RelativePermeability: Stone II three-phase model
