"""Tests for post-processing tools."""

import inspect

import numpy as np
import pytest
from pathlib import Path

from agents4geos.tools.postproc_tools import (
    read_vtk_output, extract_field, sanity_check, screenshot_field,
)
from agents4geos.tools.xml_tools import create_document
from agents4geos.tools.colormaps import SEQUENTIAL_DEFAULT


def _create_test_vtk(tmp_path: Path) -> Path:
    """Create a simple VTK file with scalar data for testing."""
    import pyvista as pv

    grid = pv.ImageData(dimensions=(6, 6, 4), spacing=(10, 10, 5))
    grid["pressure"] = np.random.uniform(1e7, 3e7, grid.n_cells)
    grid["temperature"] = np.random.uniform(300, 400, grid.n_cells)
    path = tmp_path / "output.vti"
    grid.save(str(path))
    return path


def test_read_vtk_output(tmp_output):
    vtk_path = _create_test_vtk(tmp_output)
    result = read_vtk_output(file_path=str(vtk_path))
    assert "pressure" in result["array_names"]
    assert "temperature" in result["array_names"]
    assert result["n_cells"] > 0


def test_extract_field(tmp_output):
    vtk_path = _create_test_vtk(tmp_output)
    result = extract_field(file_path=str(vtk_path), field_name="pressure")
    assert result["min"] > 0
    assert result["max"] > result["min"]
    assert result["mean"] > 0


def _create_test_multiblock(tmp_path: Path) -> Path:
    import pyvista as pv
    import numpy as np
    g = pv.ImageData(dimensions=(3, 3, 3)).cast_to_unstructured_grid()
    g.cell_data["pressure"] = np.linspace(1.0e7, 1.5e7, g.n_cells)
    mb = pv.MultiBlock()
    mb.append(g, "rank0")
    mb.append(g.copy(), "rank1")
    path = tmp_path / "vtkOutput.vtm"
    mb.save(str(path))
    return path


def test_read_vtk_output_handles_multiblock(tmp_path):
    from agents4geos.tools.postproc_tools import read_vtk_output
    path = _create_test_multiblock(tmp_path)
    r = read_vtk_output(file_path=str(path))
    assert "error" not in r
    assert "pressure" in r["array_names"]
    assert r["n_cells"] == 16  # 8 cells x 2 blocks


def test_extract_field_handles_multiblock(tmp_path):
    from agents4geos.tools.postproc_tools import extract_field
    path = _create_test_multiblock(tmp_path)
    r = extract_field(file_path=str(path), field_name="pressure")
    assert r["count"] == 16
    assert 1.0e7 <= r["min"] <= r["max"] <= 1.5e7


def test_sanity_check_template(schema):
    doc = create_document(template="single_phase_flow")
    result = sanity_check(doc_id=doc["doc_id"])
    assert "checks" in result
    assert isinstance(result["total"], int)


def test_screenshot_default_is_scientific_not_coolwarm():
    sig = inspect.signature(screenshot_field)
    assert sig.parameters["colormap"].default == SEQUENTIAL_DEFAULT


def test_screenshot_rejects_banned_colormap_before_render(tmp_path):
    # A banned map must raise at the guard, before any PyVista I/O — so a
    # non-existent file path is fine; the ValueError fires first.
    with pytest.raises(ValueError):
        screenshot_field(
            file_path=str(tmp_path / "nope.vtu"),
            field_name="pressure",
            colormap="jet",
        )
