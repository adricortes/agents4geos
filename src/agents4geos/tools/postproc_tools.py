"""Post-processing & verification MCP tools (Group 5)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from agents4geos.server import mcp
from agents4geos.knowledge.sanity_rules import run_sanity_checks, check_document_structure
from agents4geos.tools.colormaps import SEQUENTIAL_DEFAULT, resolve_colormap


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
    colormap: str = SEQUENTIAL_DEFAULT,
    clim: list[float] | None = None,
    output_path: str = "field_screenshot.png",
    title: str | None = None,
) -> str:
    """Generate a publication-quality screenshot of a scalar field on a mesh.

    Includes: titled colorbar (vertical, right side), axis widget, figure title,
    proper font sizes, white background. Suitable for papers and presentations.

    Args:
        file_path: Path to VTK file
        field_name: Scalar field to visualize
        camera_position: 'xy', 'xz', 'yz', or 'iso'
        colormap: Scientific colormap. Default cmc.batlow (perceptually uniform,
            colour-blind-safe). Pass cmc.vik for diverging fields. jet/rainbow are
            rejected.
        clim: Color limits [min, max], or None for auto
        output_path: Path to save PNG
        title: Optional figure title (defaults to field_name)
    """
    import pyvista as pv

    colormap = resolve_colormap(colormap, strict=True)

    pv.OFF_SCREEN = True
    pv.global_theme.font.size = 16
    pv.global_theme.font.label_size = 14
    pv.global_theme.font.title_size = 20
    pv.global_theme.font.family = "arial"

    mesh = pv.read(file_path)
    plotter = pv.Plotter(off_screen=True, window_size=(1920, 1080))

    sbar_args = {
        "title": field_name,
        "vertical": True,
        "position_x": 0.85,
        "position_y": 0.15,
        "width": 0.05,
        "height": 0.7,
        "title_font_size": 24,
        "label_font_size": 20,
        "n_labels": 5,
        "fmt": "%.4g",
        "shadow": True,
    }

    plotter.add_mesh(
        mesh, scalars=field_name, cmap=colormap, clim=clim,
        show_edges=False, scalar_bar_args=sbar_args,
    )
    plotter.show_axes()
    plotter.add_axes(line_width=2, labels_off=False)
    fig_title = title or field_name
    plotter.add_text(fig_title, position="upper_left", font_size=16, shadow=True)
    plotter.camera_position = camera_position
    plotter.set_background("white")
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
def compute_darcy_velocity(
    file_path: str,
    permeability_m2: float,
    viscosity_Pa_s: float,
    output_path: str | None = None,
) -> dict:
    """Compute Darcy velocity v = -(k/mu) * grad(p) from a pressure field and add it to the mesh.

    Saves the mesh with the new 'darcy_velocity' and 'darcy_velocity_magnitude' arrays.

    Args:
        file_path: Path to VTK file containing a 'pressure' field
        permeability_m2: Isotropic permeability (m^2)
        viscosity_Pa_s: Dynamic viscosity (Pa.s)
        output_path: Where to save the result (default: appends _velocity to filename)
    """
    import pyvista as pv

    mesh = pv.read(file_path)
    if "pressure" not in mesh.array_names:
        return {"error": "No 'pressure' field found in mesh"}

    # Compute pressure gradient
    grad = mesh.compute_derivative(scalars="pressure", gradient="pressure_gradient")
    p_grad = grad["pressure_gradient"]  # shape (n_cells, 3)

    # Darcy velocity: v = -(k/mu) * grad(p)
    k_over_mu = permeability_m2 / viscosity_Pa_s
    velocity = -k_over_mu * p_grad
    magnitude = np.linalg.norm(velocity, axis=1)

    mesh["darcy_velocity"] = velocity
    mesh["darcy_velocity_magnitude"] = magnitude

    if output_path is None:
        p = Path(file_path)
        output_path = str(p.parent / f"{p.stem}_velocity{p.suffix}")

    mesh.save(output_path)

    return {
        "output_path": output_path,
        "velocity_min_m_s": float(magnitude.min()),
        "velocity_max_m_s": float(magnitude.max()),
        "velocity_mean_m_s": float(magnitude.mean()),
        "k_over_mu": k_over_mu,
    }


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
    from agents4geos.tools.xml_tools import _store
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    all_attrs: list[tuple[str, str]] = []
    _collect_all_attrs(doc.root, all_attrs)
    checks = run_sanity_checks(all_attrs)
    structural = check_document_structure(doc.root)
    checks.extend(structural)

    # Unit expression validation (from unit_conventions knowledge module)
    from agents4geos.knowledge.unit_conventions import validate_unit_expression
    from agents4geos.knowledge.preprocessing_rules import SPECIAL_CHARACTERS
    import re
    for attr_name, attr_value in all_attrs:
        # Check bracket notation uses valid units
        if "[" in attr_value and "]" in attr_value:
            unit_result = validate_unit_expression(attr_value)
            if not unit_result["valid"]:
                checks.append({
                    "name": "invalid_unit_expression",
                    "attribute": attr_name,
                    "value": attr_value,
                    "status": "fail",
                    "message": f"Unknown unit(s) in bracket notation: {unit_result['unknown']}",
                })
        # Flag leftover special characters (unresolved preprocessing)
        for char in SPECIAL_CHARACTERS:
            if char in attr_value:
                # Skip bracket notation (valid unit expressions contain [ and ])
                if char in "[]" and re.search(r"\d\s*\[", attr_value):
                    continue
                # Flag unresolved parameters ($) and symbolic expressions (`)
                if char in "$`":
                    checks.append({
                        "name": "unresolved_preprocessing",
                        "attribute": attr_name,
                        "value": attr_value,
                        "status": "advisory",
                        "message": f"Contains '{char}' — may be an unresolved "
                                   f"{'parameter' if char == '$' else 'symbolic expression'}",
                    })

    return {
        "checks": checks,
        "total": len(checks),
        "failures": sum(1 for c in checks if c["status"] == "fail"),
    }


def _collect_all_attrs(el, pairs: list) -> None:
    """Append every (attribute_name, value) on this element and its descendants.

    Collects a list of pairs (not a name-keyed dict) so identically-named
    attributes on different elements are preserved rather than overwriting
    each other.
    """
    for name, value in el.attributes.items():
        pairs.append((name, value))
    for child in el.children:
        _collect_all_attrs(child, pairs)
