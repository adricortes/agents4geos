---
name: geos-mesh
description: Create, visualize, or analyze meshes for GEOS simulations.
---

Mesh creation and analysis tools.

## Tools
- `create_structured_mesh(nx, ny, nz, dx, dy, dz)` — uniform grid, saves VTK
- `create_rectilinear_mesh(x_coords, y_coords, z_coords)` — variable spacing
- `load_mesh(path)` — inspect existing mesh
- `mesh_statistics(path)` — cell volumes, quality metrics
- `screenshot_mesh(path, scalars, camera)` — headless visualization
- `generate_internal_mesh_xml(nx, ny, nz, dx, dy, dz)` — GEOS XML snippet
- `define_geometry_box(name, x_min, x_max)` — BC region definition
- `suggest_mesh_resolution(domain_size, features)` — resolution advisor
