import pytest
from agents4geos.dispatch.results import (
    FluidResult, MeshResult, ConstitutiveSpec,
    parse_fluid_result, parse_mesh_result, MESH_KINDS, INTERNAL_MESH_KEYS,
)
from agents4geos.dispatch.results import (
    PostprocessResult, FieldStat, FigureRef, parse_postprocess_result,
)


def _fluid_dict():
    return {
        "model_type": "CO2BrinePhillipsFluid",
        "constitutive": [
            {"element_type": "CO2BrinePhillipsFluid", "name": "fluid",
             "attributes": {"phasePVTParaFiles": "{ pvtgas.txt, pvtliquid.txt }"}}
        ],
        "pvt_table_paths": ["pvtgas.txt"],
        "notes": "Phillips: salinity below Ezrokhi threshold",
    }


def _internal_mesh_dict():
    return {
        "mesh_kind": "internal",
        "internal_mesh": {"xCoords": "{ 0, 100 }", "yCoords": "{ 0, 100 }",
                          "zCoords": "{ 0, 100 }", "nx": "{ 10 }", "ny": "{ 10 }",
                          "nz": "{ 10 }", "elementTypes": "{ C3D8 }"},
        "stats": {"n_cells": 1000},
        "notes": "100 m cube",
    }


def test_parse_fluid_result_roundtrip():
    fr = parse_fluid_result(_fluid_dict())
    assert isinstance(fr, FluidResult)
    assert fr.model_type == "CO2BrinePhillipsFluid"
    assert len(fr.constitutive) == 1
    assert isinstance(fr.constitutive[0], ConstitutiveSpec)
    assert fr.constitutive[0].name == "fluid"
    assert fr.pvt_table_paths == ["pvtgas.txt"]


def test_fluid_missing_model_type_raises():
    d = _fluid_dict(); del d["model_type"]
    with pytest.raises(ValueError):
        parse_fluid_result(d)


def test_fluid_constitutive_not_list_raises():
    d = _fluid_dict(); d["constitutive"] = {"element_type": "x"}
    with pytest.raises(ValueError):
        parse_fluid_result(d)


def test_fluid_constitutive_item_missing_keys_raises():
    d = _fluid_dict(); del d["constitutive"][0]["attributes"]
    with pytest.raises(ValueError):
        parse_fluid_result(d)


def test_fluid_defaults_when_optional_absent():
    d = _fluid_dict(); del d["pvt_table_paths"]; del d["notes"]
    fr = parse_fluid_result(d)
    assert fr.pvt_table_paths == [] and fr.notes == ""


def test_parse_mesh_internal_roundtrip():
    mr = parse_mesh_result(_internal_mesh_dict())
    assert isinstance(mr, MeshResult)
    assert mr.is_internal and not mr.is_vtk
    assert mr.internal_mesh["nx"] == "{ 10 }"
    assert mr.stats["n_cells"] == 1000


def test_mesh_internal_missing_a_key_raises():
    d = _internal_mesh_dict(); del d["internal_mesh"]["nz"]
    with pytest.raises(ValueError):
        parse_mesh_result(d)


def test_parse_mesh_vtk_roundtrip():
    mr = parse_mesh_result({"mesh_kind": "vtk", "vtk_path": "/tmp/mesh.vtu",
                            "stats": {"n_cells": 50}})
    assert mr.is_vtk and not mr.is_internal
    assert mr.vtk_path == "/tmp/mesh.vtu"


def test_mesh_vtk_missing_path_raises():
    with pytest.raises(ValueError):
        parse_mesh_result({"mesh_kind": "vtk"})


def test_mesh_unknown_kind_raises():
    with pytest.raises(ValueError):
        parse_mesh_result({"mesh_kind": "octree"})


def test_mesh_missing_kind_raises():
    with pytest.raises(ValueError):
        parse_mesh_result({"internal_mesh": {}})


def test_constants_exposed():
    assert MESH_KINDS == ("internal", "vtk")
    assert "elementTypes" in INTERNAL_MESH_KEYS


def _postproc_dict():
    return {
        "fields": [
            {"name": "pressure", "min": 1.0e6, "max": 2.0e7,
             "mean": 1.1e7, "std": 3.0e6, "units": "Pa"}
        ],
        "figures": [
            {"path": "/abs/pressure.png", "title": "Pressure at t = 1 yr [Pa]",
             "units": "Pa", "colormap": "cmc.vik", "map_type": "diverging"}
        ],
        "derived": {"material_balance_m3": 1.2e5},
        "notes": "final timestep",
    }


def test_parse_postprocess_roundtrip():
    pr = parse_postprocess_result(_postproc_dict())
    assert isinstance(pr, PostprocessResult)
    assert isinstance(pr.fields[0], FieldStat)
    assert pr.fields[0].units == "Pa"
    assert isinstance(pr.figures[0], FigureRef)
    assert pr.figures[0].map_type == "diverging"
    assert pr.derived["material_balance_m3"] == 1.2e5


def test_postproc_field_missing_stat_key_raises():
    d = _postproc_dict(); del d["fields"][0]["std"]
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_figure_missing_path_raises():
    d = _postproc_dict(); del d["figures"][0]["path"]
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_banned_colormap_fails_validation():
    d = _postproc_dict(); d["figures"][0]["colormap"] = "jet"
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_bad_map_type_raises():
    d = _postproc_dict(); d["figures"][0]["map_type"] = "rainbowish"
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_defaults_when_optional_absent():
    d = _postproc_dict(); del d["derived"]; del d["notes"]
    pr = parse_postprocess_result(d)
    assert pr.derived == {}
    assert pr.notes == ""
