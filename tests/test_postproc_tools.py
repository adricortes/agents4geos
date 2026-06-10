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
