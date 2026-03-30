---
name: geos-relperm
description: Generate relative permeability and capillary pressure curves.
---

Relative permeability and capillary pressure tools.

## Tools
- `generate_rel_perm(model, swc, sorg, exponents, n_rows)` — Brooks-Corey, VanGenuchten, or LET
- `fit_rel_perm(measured_S, measured_Kr, model)` — fit model to lab data
- `generate_cap_pressure(model, entry_pressure_Pa, swc, exponent)` — Pc curve
