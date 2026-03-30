"""Post-processing & verification MCP tools (Group 5)."""

from __future__ import annotations

import numpy as np

from agents4geosx.server import mcp
from agents4geosx.knowledge.sanity_rules import run_sanity_checks


@mcp.tool
def read_vtk_output(file_path: str) -> dict:
    """Inspect a GEOS VTK output file: cell/point counts, available arrays, scalar ranges."""
    import pyvista as pv

    mesh = pv.read(file_path)
    scalar_ranges = {}
    for name in mesh.array_names:
        arr = mesh[name]
        if arr.ndim == 1:
            scalar_ranges[name] = [float(arr.min()), float(arr.max())]
    return {
        "n_cells": mesh.n_cells,
        "n_points": mesh.n_points,
        "bounds": list(mesh.bounds),
        "array_names": list(mesh.array_names),
        "scalar_ranges": scalar_ranges,
    }


@mcp.tool
def extract_field(file_path: str, field_name: str) -> dict:
    """Extract summary statistics for a scalar field from a VTK file."""
    import pyvista as pv

    mesh = pv.read(file_path)
    arr = mesh[field_name]
    if arr.ndim > 1:
        arr = np.linalg.norm(arr, axis=1)
    return {
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "count": len(arr),
    }


@mcp.tool
def screenshot_field(
    file_path: str,
    field_name: str,
    camera_position: str = "iso",
    colormap: str = "viridis",
    clim: list[float] | None = None,
    output_path: str = "field_screenshot.png",
) -> str:
    """Generate a headless screenshot of a scalar field on a mesh."""
    import pyvista as pv

    pv.OFF_SCREEN = True
    mesh = pv.read(file_path)
    plotter = pv.Plotter(off_screen=True, window_size=(1920, 1080))
    plotter.add_mesh(mesh, scalars=field_name, cmap=colormap, clim=clim,
                     show_edges=False, scalar_bar_args={"title": field_name})
    plotter.camera_position = camera_position
    plotter.screenshot(output_path)
    plotter.close()
    return output_path


@mcp.tool
def compare_timesteps(file_paths: list[str], field_name: str) -> dict:
    """Compare a scalar field across multiple timestep VTK files."""
    import pyvista as pv

    evolution = []
    for i, fp in enumerate(file_paths):
        mesh = pv.read(fp)
        arr = mesh[field_name]
        evolution.append({
            "timestep": i, "file": fp,
            "min": float(arr.min()), "max": float(arr.max()), "mean": float(arr.mean()),
        })
    return {"field": field_name, "timesteps": len(file_paths), "evolution": evolution}


@mcp.tool
def compute_material_balance(
    pressure_history_Pa: list[float],
    cumulative_production_m3: list[float],
    temperature_K: float,
    fluid_type: str = "gas",
    specific_gravity: float = 0.7,
) -> dict:
    """Compute original-in-place estimate from pressure and production history (SI units)."""
    from pyrestoolbox import matbal

    if fluid_type == "gas":
        result = matbal.gas_matbal(
            p=pressure_history_Pa, Gp=cumulative_production_m3,
            degf=temperature_K, sg=specific_gravity, units="SI",
        )
        return {"original_in_place_m3": float(result.ogip), "r_squared": float(result.r_squared)}
    return {"error": "Oil material balance not yet integrated"}


@mcp.tool
def compute_well_performance(
    reservoir_pressure_Pa: float,
    flowing_pressure_Pa: float,
    temperature_K: float,
    permeability_m2: float,
    thickness_m: float,
    wellbore_radius_m: float = 0.1,
    drainage_radius_m: float = 500.0,
    fluid_type: str = "gas",
    specific_gravity: float = 0.7,
) -> dict:
    """Quick well rate estimate for sanity-checking simulation output."""
    from pyrestoolbox import gas

    if fluid_type == "gas":
        rate = gas.gas_rate_radial(
            k=permeability_m2, h=thickness_m, pr=reservoir_pressure_Pa,
            pwf=flowing_pressure_Pa, r_w=wellbore_radius_m,
            r_ext=drainage_radius_m, degf=temperature_K,
            sg=specific_gravity, units="SI",
        )
        return {"rate_m3_s": float(rate), "fluid_type": "gas"}
    return {"error": "Oil well performance not yet integrated"}


@mcp.tool
def sanity_check(doc_id: str) -> dict:
    """Run physics sanity checks on a document's parameters."""
    from agents4geosx.tools.xml_tools import _store
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    all_attrs: dict[str, str] = {}
    _collect_all_attrs(doc.root, all_attrs)
    checks = run_sanity_checks(all_attrs)
    return {
        "checks": checks,
        "total": len(checks),
        "failures": sum(1 for c in checks if c["status"] == "fail"),
    }


def _collect_all_attrs(el, attrs: dict) -> None:
    attrs.update(el.attributes)
    for child in el.children:
        _collect_all_attrs(child, attrs)
