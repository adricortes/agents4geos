---
name: geos:postprocess
description: Analyze GEOS simulation output — VTK fields, time evolution, material balance.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools.

## Tools
- `read_vtk_output(path)` — inspect arrays, scalar ranges
- `extract_field(path, field_name)` — min/max/mean/std statistics
- `screenshot_field(path, field_name, camera, colormap)` — headless visualization
- `compare_timesteps(file_paths, field_name)` — field evolution over time
- `compute_material_balance(pressure_history, production, temperature, fluid_type)` — reserves estimation (SI units)
- `compute_well_performance(Pr, Pwf, T, k, h)` — quick rate sanity check (SI units)
- `sanity_check(doc_id)` — physics heuristics on the input file

## IMPORTANT: Use Absolute Paths
The MCP server runs in a different directory than your workspace. ALWAYS use absolute file paths for all postprocessing tools. Use `Bash(pwd)` or `Bash(realpath run/file.vtu)` to resolve relative paths first.

## Workflow
1. `read_vtk_output` first to see what fields are available
2. `extract_field` for quick statistics
3. `screenshot_field` for visualization (headless, generates PNG)
4. For time series: collect multiple VTK files → `compare_timesteps`

## Publication-Quality Screenshots
`screenshot_field` produces publication-ready figures with:
- Vertical colorbar on the right with proper labels
- Axis widget showing X/Y/Z orientation
- Figure title in upper-left corner
- White background, proper font sizes

ALWAYS provide a descriptive `title` parameter, e.g.:
- `title="Pressure Field at t = 1 year [Pa]"`
- `title="ΔPressure (Final - Initial) [Pa]"`
- `title="Water Density [kg/m³]"`

Default colormap is `coolwarm` (blue-white-red, good for diverging data). Use `viridis` for sequential data (saturation, porosity).

## All units are SI
- Pressure: Pa
- Rate: m³/s
- Temperature: K
- Permeability: m²
