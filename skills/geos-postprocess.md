---
name: geos-postprocess
description: Analyze GEOS simulation output — VTK fields, time evolution, material balance.
---

Post-processing tools for GEOS VTK output.

## Tools
- `read_vtk_output(path)` — inspect arrays, scalar ranges
- `extract_field(path, field_name)` — min/max/mean/std statistics
- `screenshot_field(path, field_name, camera, colormap)` — headless visualization
- `compare_timesteps(file_paths, field_name)` — field evolution over time
- `compute_material_balance(pressure_history, production, temperature, fluid_type)` — reserves estimation
- `compute_well_performance(Pr, Pwf, T, k, h)` — quick rate sanity check
