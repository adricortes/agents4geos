"""Mesh creation & visualization MCP tools (Group 3) — wraps PyVista."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from agents4geos.server import mcp


@mcp.tool
def create_structured_mesh(
    nx: int, ny: int, nz: int,
    dx: float, dy: float, dz: float,
    origin: list[float] | None = None,
    output_dir: str = ".",
) -> dict:
    """Create a uniform structured mesh and save as VTK."""
    import pyvista as pv

    if origin is None:
        origin = [0.0, 0.0, 0.0]
    grid = pv.ImageData(
        dimensions=(nx + 1, ny + 1, nz + 1),
        spacing=(dx, dy, dz),
        origin=origin,
    )
    out_path = Path(output_dir) / "mesh.vti"
    grid.save(str(out_path))
    return {
        "n_cells": grid.n_cells,
        "n_points": grid.n_points,
        "bounds": list(grid.bounds),
        "dimensions": [nx, ny, nz],
        "vtk_path": str(out_path),
    }


@mcp.tool
def create_rectilinear_mesh(
    x_coords: list[float],
    y_coords: list[float],
    z_coords: list[float],
    output_dir: str = ".",
) -> dict:
    """Create a rectilinear (variable-spacing) mesh and save as VTK."""
    import pyvista as pv

    grid = pv.RectilinearGrid(np.array(x_coords), np.array(y_coords), np.array(z_coords))
    out_path = Path(output_dir) / "mesh.vtr"
    grid.save(str(out_path))
    return {
        "n_cells": grid.n_cells,
        "n_points": grid.n_points,
        "bounds": list(grid.bounds),
        "dimensions": [len(x_coords) - 1, len(y_coords) - 1, len(z_coords) - 1],
        "vtk_path": str(out_path),
    }


@mcp.tool
def load_mesh(file_path: str) -> dict:
    """Load and inspect an existing VTK/mesh file."""
    import pyvista as pv

    mesh = pv.read(file_path)
    return {
        "n_cells": mesh.n_cells,
        "n_points": mesh.n_points,
        "bounds": list(mesh.bounds),
        "array_names": list(mesh.array_names),
    }


@mcp.tool
def mesh_statistics(file_path: str) -> dict:
    """Compute mesh quality statistics (cell volumes, aspect ratios)."""
    import pyvista as pv

    mesh = pv.read(file_path)
    sized = mesh.compute_cell_sizes()
    volumes = sized["Volume"]
    return {
        "total_volume": float(volumes.sum()),
        "min_cell_volume": float(volumes.min()),
        "max_cell_volume": float(volumes.max()),
        "mean_cell_volume": float(volumes.mean()),
        "bounding_box": list(mesh.bounds),
        "n_cells": mesh.n_cells,
    }


@mcp.tool
def screenshot_mesh(
    file_path: str,
    scalars: str | None = None,
    camera_position: str = "iso",
    output_path: str = "mesh_screenshot.png",
    title: str | None = None,
) -> str:
    """Generate a publication-quality headless screenshot of a mesh.

    Args:
        file_path: Path to mesh file
        scalars: Optional scalar field to color by
        camera_position: 'xy', 'xz', 'yz', or 'iso'
        output_path: Path to save PNG
        title: Optional title for the figure
    """
    import pyvista as pv

    pv.OFF_SCREEN = True
    pv.global_theme.font.size = 16
    pv.global_theme.font.label_size = 14
    pv.global_theme.font.title_size = 20
    pv.global_theme.font.family = "arial"

    mesh = pv.read(file_path)
    plotter = pv.Plotter(off_screen=True, window_size=(1920, 1080))

    sbar_args = {
        "title": scalars or "",
        "vertical": True,
        "position_x": 0.85,
        "position_y": 0.15,
        "width": 0.05,
        "height": 0.7,
        "title_font_size": 24,
        "label_font_size": 20,
        "n_labels": 5,
        "fmt": "%.2e",
        "shadow": True,
    } if scalars else {}

    plotter.add_mesh(
        mesh, scalars=scalars, show_edges=True, edge_color="gray",
        opacity=0.9, scalar_bar_args=sbar_args if scalars else None,
    )
    plotter.show_axes()
    plotter.add_axes(line_width=2, labels_off=False)
    if title:
        plotter.add_text(title, position="upper_left", font_size=16, shadow=True)
    plotter.camera_position = camera_position
    plotter.set_background("white")
    plotter.screenshot(output_path)
    plotter.close()
    return output_path


@mcp.tool
def generate_internal_mesh_xml(
    nx: int, ny: int, nz: int,
    dx: float, dy: float, dz: float,
    element_type: str = "C3D8",
    cell_block_names: list[str] | None = None,
) -> str:
    """Generate a GEOS InternalMesh XML snippet."""
    if cell_block_names is None:
        cell_block_names = ["block1"]
    blocks = ", ".join(cell_block_names)
    xmax = nx * dx
    ymax = ny * dy
    zmax = nz * dz
    return (
        f'<InternalMesh name="mesh1"\n'
        f'  elementTypes="{{ {element_type} }}"\n'
        f'  xCoords="{{ 0, {xmax} }}"\n'
        f'  yCoords="{{ 0, {ymax} }}"\n'
        f'  zCoords="{{ 0, {zmax} }}"\n'
        f'  nx="{{ {nx} }}"\n'
        f'  ny="{{ {ny} }}"\n'
        f'  nz="{{ {nz} }}"\n'
        f'  cellBlockNames="{{ {blocks} }}"/>'
    )


@mcp.tool
def define_geometry_box(
    name: str,
    x_min: list[float],
    x_max: list[float],
) -> str:
    """Generate a GEOS Geometry Box XML snippet for boundary condition regions."""
    xmin_str = f"{{ {x_min[0]}, {x_min[1]}, {x_min[2]} }}"
    xmax_str = f"{{ {x_max[0]}, {x_max[1]}, {x_max[2]} }}"
    return f'<Box name="{name}" xMin="{xmin_str}" xMax="{xmax_str}"/>'


@mcp.tool
def suggest_mesh_resolution(
    domain_size_m: list[float],
    features: list[str] | None = None,
) -> dict:
    """Suggest mesh resolution based on domain size and features."""
    lx, ly, lz = domain_size_m
    nx = max(10, int(lx / 30))
    ny = max(10, int(ly / 30))
    nz = max(5, int(lz / 8))
    if features:
        for f in features:
            if "well" in f.lower():
                nx = max(nx, int(lx / 20))
                ny = max(ny, int(ly / 20))
            if "fault" in f.lower():
                nx = max(nx, int(lx / 15))
    dx = lx / nx
    dy = ly / ny
    dz = lz / nz
    return {
        "nx": nx, "ny": ny, "nz": nz,
        "dx": round(dx, 2), "dy": round(dy, 2), "dz": round(dz, 2),
        "total_cells": nx * ny * nz,
        "reasoning": f"Target cell size: {dx:.0f}m x {dy:.0f}m x {dz:.0f}m for {lx:.0f}x{ly:.0f}x{lz:.0f}m domain",
    }
