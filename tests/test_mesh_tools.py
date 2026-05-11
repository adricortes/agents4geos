"""Tests for mesh creation and visualization tools."""

from pathlib import Path

from agents4geos.tools.mesh_tools import (
    create_structured_mesh, load_mesh, mesh_statistics,
    generate_internal_mesh_xml, define_geometry_box, suggest_mesh_resolution,
)


def test_create_structured_mesh(tmp_output):
    result = create_structured_mesh(
        nx=10, ny=10, nz=5, dx=100.0, dy=100.0, dz=20.0,
        output_dir=str(tmp_output),
    )
    assert result["n_cells"] == 500
    assert result["n_points"] == 11 * 11 * 6
    assert Path(result["vtk_path"]).exists()


def test_load_mesh(tmp_output):
    create_structured_mesh(nx=5, ny=5, nz=3, dx=10, dy=10, dz=5,
                           output_dir=str(tmp_output))
    result = load_mesh(file_path=str(tmp_output / "mesh.vti"))
    assert result["n_cells"] == 75
    assert result["n_points"] > 0


def test_mesh_statistics(tmp_output):
    create_structured_mesh(nx=5, ny=5, nz=3, dx=10, dy=10, dz=5,
                           output_dir=str(tmp_output))
    result = mesh_statistics(file_path=str(tmp_output / "mesh.vti"))
    assert result["total_volume"] > 0
    assert result["mean_cell_volume"] > 0


def test_generate_internal_mesh_xml():
    xml = generate_internal_mesh_xml(nx=50, ny=50, nz=10, dx=20.0, dy=20.0, dz=10.0)
    assert "<InternalMesh" in xml
    assert "C3D8" in xml
    assert "50" in xml


def test_define_geometry_box():
    xml = define_geometry_box(
        name="left_face", x_min=[0.0, 0.0, 0.0], x_max=[0.0, 1000.0, 100.0],
    )
    assert '<Box name="left_face"' in xml
    assert "xMin" in xml
    assert "xMax" in xml


def test_suggest_mesh_resolution():
    result = suggest_mesh_resolution(
        domain_size_m=[1000.0, 1000.0, 100.0], features=["well at center"],
    )
    assert result["nx"] > 0
    assert result["ny"] > 0
    assert result["nz"] > 0
    assert result["total_cells"] > 0
