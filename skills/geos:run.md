---
name: geos:run
description: Run a GEOS simulation and analyze the output.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools for post-processing. Use Bash ONLY for the GEOS run itself.

## Workflow

1. **Verify the XML** before running:
   ```
   /geos:validate <file.xml>
   ```

2. **Run GEOS** via Bash (this is the one place Bash is appropriate):
   ```bash
   cd <run_directory>
   geos/build/bin/geosx -i <file.xml>
   ```
   Check the output for errors. Common issues:
   - "coupled solid constitutive model not found" → missing CompressibleSolidConstantPermeability in materialList
   - "targets empty set" → geometry box doesn't enclose cell centers (needs to be one cell deep)
   - "component fractions do not sum to 1" → globalCompFraction initialization error

3. **Locate the VTK output** (usually in `vtkOutput/` subdirectory):
   ```bash
   find . -name "*.vtu" | head -5
   ```

4. **Analyze with MCP tools** (use ABSOLUTE paths):
   - `read_vtk_output(path)` → list available fields
   - `extract_field(path, field_name)` → statistics
   - `screenshot_field(path, field_name, title="...", output_path="...")` → publication-quality figure
   - `compute_darcy_velocity(path, permeability_m2, viscosity_Pa_s)` → derive velocity from pressure
   - `compare_timesteps(file_paths, field_name)` → time evolution

## Tips
- GEOS VTK output structure: `vtkOutput/<timestep>/mesh/Level0/<region>/rank_0.vtu`
- Use `ls vtkOutput/` to see timestep directories (000000, 000001, etc.)
- The last timestep directory has the final state
- Always provide a descriptive `title` for screenshots (e.g., "Pressure at t=1yr [Pa]")
