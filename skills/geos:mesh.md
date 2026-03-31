---
name: geos:mesh
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
- GEOS InternalMesh uses xCoords/yCoords/zCoords (domain boundaries) + nx/ny/nz (cell counts)

## Geometry Boxes — CRITICAL for BCs

Boxes that target `objectPath="ElementRegions/..."` (SourceFlux, most FieldSpecifications) must enclose at least one layer of CELL CENTERS, not just the face.

For a domain Lx × Ly × Lz with cell sizes dx, dy, dz:
- Left face source/BC: xMin={ -0.01, -0.01, -0.01 }, xMax={ **dx+0.01**, Ly+0.01, Lz+0.01 }
- Right face source/BC: xMin={ **Lx-dx-0.01**, -0.01, -0.01 }, xMax={ Lx+0.01, Ly+0.01, Lz+0.01 }
- "all" box (ICs): xMin={ -0.01, -0.01, -0.01 }, xMax={ Lx+0.01, Ly+0.01, Lz+0.01 }

A thin slab box (±0.01m at a face) only captures nodes/edges/faces, NOT cells — GEOS will error with "targets empty set" for ElementRegions.
