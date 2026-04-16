"""Tests for preprocessing MCP tools."""
from __future__ import annotations

import pytest
from pathlib import Path
from agents4geosx.tools.preproc_tools import (
    convert_units, expand_parameters, resolve_includes, format_xml,
)
from agents4geosx.tools.xml_tools import create_document, add_element


class TestConvertUnits:
    def test_si_base_no_conversion(self):
        result = convert_units("9.81[m/s**2]")
        assert result["valid"] is True
        assert result["numeric_value"] == 9.81
        assert result["unit_expression"] == "m/s**2"
        assert abs(result["si_value"] - 9.81) < 1e-10

    def test_millidarcy(self):
        result = convert_units("100[mD]")
        assert result["valid"] is True
        assert result["numeric_value"] == 100.0
        # 1 mD = milli (1e-3) * darcy (9.869233e-13) = 9.869233e-16 m^2
        # 100 mD = 9.869233e-14 m^2
        expected = 100 * 1e-3 * 9.869233e-13
        assert abs(result["si_value"] - expected) / expected < 1e-4

    def test_prefix_kilo(self):
        result = convert_units("3.0[km]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 3000.0) < 1e-10

    def test_prefix_mega_pascal(self):
        result = convert_units("20[MPa]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 20e6) < 1e-2

    def test_psi(self):
        result = convert_units("1000[psi]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 6894760.0) < 100

    def test_barrel_per_day(self):
        result = convert_units("1.0[bbl/day]")
        assert result["valid"] is True
        expected = 0.1589873 / 86400.0
        assert abs(result["si_value"] - expected) / expected < 1e-4

    def test_scientific_notation_input(self):
        result = convert_units("3.14e-2[Pa]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 3.14e-2) < 1e-10

    def test_invalid_unit(self):
        result = convert_units("1.0[foobar]")
        assert result["valid"] is False
        assert "foobar" in result["unknown_units"]

    def test_no_brackets(self):
        result = convert_units("plain text")
        assert result["valid"] is True
        assert result["si_value"] is None

    def test_space_before_bracket(self):
        result = convert_units("1.0 [bbl]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 0.1589873) < 1e-6

    def test_centipoise(self):
        result = convert_units("1.0[cP]")
        assert result["valid"] is True
        # centi (1e-2) * poise (0.1) = 0.001 Pa·s
        assert abs(result["si_value"] - 0.001) < 1e-10

    def test_foot(self):
        result = convert_units("100[ft]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 30.48) < 1e-6


class TestExpandParameters:
    def test_basic_expansion(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        add_element(doc_id, "Parameters", "Parameter", "injRate",
                    {"value": "1e-4"})
        add_element(doc_id, "FieldSpecifications", "FieldSpecification", "injection",
                    {"scale": "$injRate$", "fieldName": "pressure"})
        result = expand_parameters(doc_id)
        assert result["parameters_found"]["injRate"] == "1e-4"
        assert result["substitutions_made"] >= 1
        assert len(result["unresolved"]) == 0

    def test_unresolved_parameter(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        add_element(doc_id, "FieldSpecifications", "FieldSpecification", "injection",
                    {"scale": "$undefinedParam$", "fieldName": "pressure"})
        result = expand_parameters(doc_id)
        assert "undefinedParam" in result["unresolved"]

    def test_no_parameters_section(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        result = expand_parameters(doc_id)
        assert result["parameters_found"] == {}
        assert result["substitutions_made"] == 0

    def test_invalid_doc_id(self):
        result = expand_parameters("nonexistent")
        assert "error" in result


class TestResolveIncludes:
    def test_no_includes(self, schema):
        doc = create_document(template="single_phase_flow")
        doc_id = doc["doc_id"]
        result = resolve_includes(doc_id)
        assert result["files_merged"] == []
        assert result["elements_added"] == 0

    def test_invalid_doc_id(self):
        result = resolve_includes("nonexistent")
        assert "error" in result

    def test_include_with_missing_file(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        add_element(doc_id, "Included", "File", "",
                    {"name": "/tmp/nonexistent_geos_test.xml"})
        result = resolve_includes(doc_id)
        assert len(result.get("errors", [])) > 0

    def test_include_merges_file(self, schema, tmp_output):
        include_path = tmp_output / "boxes.xml"
        include_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem>\n'
            '  <Geometry>\n'
            '    <Box name="source" xMin="{ -0.01, -0.01, -0.01 }" '
            'xMax="{ 10.01, 10.01, 10.01 }"/>\n'
            '  </Geometry>\n'
            '</Problem>\n'
        )
        # Use a template and add a Geometry section so the merge target exists
        doc = create_document(template="single_phase_flow")
        doc_id = doc["doc_id"]
        # Add a Geometry section with an existing box (merge will add "source")
        add_element(doc_id, "Geometry", "Box", "all",
                    {"xMin": "{ -1, -1, -1 }", "xMax": "{ 101, 101, 101 }"})
        add_element(doc_id, "Included", "File", "",
                    {"name": str(include_path)})
        result = resolve_includes(doc_id)
        assert str(include_path) in result["files_merged"]
        assert result["elements_added"] >= 1


class TestFormatXml:
    def test_basic_formatting(self, tmp_output):
        input_path = tmp_output / "messy.xml"
        output_path = tmp_output / "clean.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Solvers>'
            '<SinglePhaseFVM name="flow" targetRegions="{Domain}"/>'
            '</Solvers></Problem>\n'
        )
        result = format_xml(str(input_path), str(output_path))
        assert result["output"] == str(output_path)
        content = output_path.read_text()
        assert "  <Solvers" in content
        assert "{ Domain }" in content

    def test_overwrite_input(self, tmp_output):
        input_path = tmp_output / "sim.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Mesh/></Problem>\n'
        )
        result = format_xml(str(input_path))
        assert result["output"] == str(input_path)

    def test_comma_spacing(self, tmp_output):
        input_path = tmp_output / "commas.xml"
        output_path = tmp_output / "commas_out.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Geometry>'
            '<Box name="all" xMin="{-1,-1,-1}" xMax="{101,101,101}"/>'
            '</Geometry></Problem>\n'
        )
        result = format_xml(str(input_path), str(output_path))
        content = output_path.read_text()
        assert "{ -1, -1, -1 }" in content
        assert "{ 101, 101, 101 }" in content

    def test_protected_expression_preserved(self, tmp_output):
        input_path = tmp_output / "symbolic.xml"
        output_path = tmp_output / "symbolic_out.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Functions>'
            '<SymbolicFunction name="f1" expression="x^2 + y^2"/>'
            '</Functions></Problem>\n'
        )
        result = format_xml(str(input_path), str(output_path))
        content = output_path.read_text()
        assert 'expression="x^2 + y^2"' in content
        assert result["protected_expressions_preserved"] >= 1

    def test_nonexistent_file(self):
        result = format_xml("/nonexistent/path.xml")
        assert "error" in result
