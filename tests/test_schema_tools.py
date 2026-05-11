"""Tests for schema introspection tools."""

from agents4geos.tools.schema_tools import (
    list_sections, list_elements, describe_element, list_attributes,
    get_type_info, lookup_field_names, get_cross_references,
)


def test_list_sections(schema):
    result = list_sections()
    assert "Solvers" in result
    assert "Mesh" in result
    assert "Constitutive" in result


def test_list_elements_v1(schema):
    result = list_elements(section="Solvers", scope="v1")
    names = [e["name"] for e in result]
    assert "SinglePhaseFVM" in names
    assert "CompositionalMultiphaseFVM" in names


def test_list_elements_all(schema):
    result = list_elements(section="Solvers", scope="all")
    names = [e["name"] for e in result]
    # All scope should have more elements than v1
    assert len(names) >= len(list_elements(section="Solvers", scope="v1"))


def test_describe_element(schema):
    result = describe_element(element_name="SinglePhaseFVM")
    assert result["name"] == "SinglePhaseFVM"
    attr_names = [a["name"] for a in result["attributes"]]
    assert "name" in attr_names
    assert "discretization" in attr_names


def test_list_attributes_all(schema):
    result = list_attributes(element_name="SinglePhaseFVM", group="all")
    assert len(result) > 3


def test_get_type_info(schema):
    result = get_type_info(type_name="real64")
    assert result["name"] == "real64"
    assert "base" in result


def test_lookup_field_names_single_phase():
    result = lookup_field_names(solver_type="SinglePhaseFVM")
    assert "pressure" in result


def test_lookup_field_names_compositional():
    result = lookup_field_names(solver_type="CompositionalMultiphaseFVM")
    assert "pressure" in result
    assert "globalCompFraction" in result


def test_get_cross_references(schema):
    result = get_cross_references(element_name="SinglePhaseFVM")
    ref_attrs = [r["attribute"] for r in result]
    assert "discretization" in ref_attrs
    assert "targetRegions" in ref_attrs
