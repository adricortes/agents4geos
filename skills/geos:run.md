---
name: geos:run
description: Run a GEOS simulation and analyze the output.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools for post-processing. Use Bash ONLY for the GEOS run itself.

## Before Running

1. **Read lessons learned** — check `knowledge/lessons_learned.md` for known
   solver/constitutive compatibility rules that apply to your XML. This avoids
   repeat failures that previous runs have already diagnosed.

2. **Verify the XML** before running:
   ```
   /geos:validate <file.xml>
   ```

## Running GEOS

Run via Bash (this is the one place Bash is appropriate):
```bash
cd <run_directory>
geos/build/bin/geosx -i <file.xml>
```

## After a Failed Run

If `geosx -i` exits with a non-zero code:
1. Diagnose and fix the issue
2. Re-run to confirm the fix works
3. Call `log_runtime_error` with the full context: the GEOS error text,
   your one-line diagnosis, and what fix resolved it

If the fix fails after 3 attempts, call `log_runtime_error` anyway with
fix_applied="UNRESOLVED" so the error is captured for future curation.

This logging step is NOT optional. It captures your understanding of what
went wrong while the context is fresh.

## After a Successful Run

1. **Locate the VTK output** (usually in `vtkOutput/` subdirectory):
   ```bash
   find . -name "*.vtu" | head -5
   ```

2. **Analyze with MCP tools** (use ABSOLUTE paths):
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
