---
name: geos-mesh
description: Create, visualize, or analyze meshes for GEOS simulations.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools.

## Tools
- `create_structured_mesh(nx, ny, nz, dx, dy, dz)` — saves VTK file
- `create_rectilinear_mesh(x_coords, y_coords, z_coords)` — variable spacing
- `load_mesh(path)` — inspect existing mesh
- `mesh_statistics(path)` — cell volumes, quality metrics
- `screenshot_mesh(path, scalars, camera)` — headless visualization
- `generate_internal_mesh_xml(nx, ny, nz, dx, dy, dz)` — GEOS XML snippet
- `define_geometry_box(name, x_min, x_max)` — BC region definition
- `suggest_mesh_resolution(domain_size, features)` — resolution advisor

## IMPORTANT Conventions
- dx/dy/dz are CELL SIZES in meters, not domain extents. Domain = nx * dx.
- All GEOS examples use C3D8 (hexahedral) elements
- Geometry boxes for BCs: use ±0.01m tolerance around face coordinates
  - Left face (x=0): xMin={ -0.01, -0.01, -0.01 }, xMax={ 0.01, Ly+0.01, Lz+0.01 }
  - Right face (x=Lx): xMin={ Lx-0.01, -0.01, -0.01 }, xMax={ Lx+0.01, Ly+0.01, Lz+0.01 }
  - "all" box: xMin={ -0.01, -0.01, -0.01 }, xMax={ Lx+0.01, Ly+0.01, Lz+0.01 }
- GEOS InternalMesh uses xCoords/yCoords/zCoords (domain boundaries) + nx/ny/nz (cell counts)
