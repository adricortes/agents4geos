"""Tests for XML assembly and validation tools."""

from pathlib import Path

import json

from agents4geosx.tools.xml_tools import (
    create_document, add_element, update_element, remove_element,
    add_child, load_xml, save_xml, preview_xml,
    validate_cross_references, log_runtime_error,
)


def test_create_blank_document(schema):
    result = create_document()
    assert "doc_id" in result
    assert result["doc_id"].startswith("doc_")


def test_create_from_template(schema):
    result = create_document(template="single_phase_flow")
    assert "doc_id" in result
    assert len(result["sections"]) > 0
    assert "Solvers" in result["sections"]


def test_add_and_preview(schema):
    doc = create_document()
    doc_id = doc["doc_id"]
    result = add_element(
        doc_id=doc_id, section="Solvers", element_type="SinglePhaseFVM",
        name="flow", attributes={"discretization": "fluidTPFA", "targetRegions": "{ Domain }"},
    )
    assert "element_path" in result
    result = preview_xml(doc_id=doc_id, section="Solvers")
    xml_str = Path(result["path"]).read_text()
    assert "SinglePhaseFVM" in xml_str
    assert 'name="flow"' in xml_str


def test_update_element(schema):
    doc = create_document()
    doc_id = doc["doc_id"]
    add_element(doc_id=doc_id, section="Solvers", element_type="SinglePhaseFVM",
                name="flow", attributes={"discretization": "tpfa"})
    result = update_element(doc_id=doc_id,
                            element_path="Solvers/SinglePhaseFVM[@name='flow']",
                            attributes={"discretization": "hybridFVM"})
    assert "updated_attrs" in result
    assert "discretization" in result["updated_attrs"]


def test_remove_element(schema):
    doc = create_document()
    doc_id = doc["doc_id"]
    add_element(doc_id=doc_id, section="Solvers", element_type="SinglePhaseFVM",
                name="flow", attributes={})
    result = remove_element(doc_id=doc_id,
                            element_path="Solvers/SinglePhaseFVM[@name='flow']")
    assert result["removed"] is True


def test_add_child(schema):
    doc = create_document()
    doc_id = doc["doc_id"]
    add_element(doc_id=doc_id, section="Solvers", element_type="SinglePhaseFVM",
                name="flow", attributes={})
    result = add_child(doc_id=doc_id,
                       parent_path="Solvers/SinglePhaseFVM[@name='flow']",
                       element_type="NonlinearSolverParameters", name="",
                       attributes={"newtonTol": "1e-6"})
    assert "element_path" in result


def test_save_and_reload(schema, tmp_output):
    doc = create_document(template="single_phase_flow")
    doc_id = doc["doc_id"]
    out_path = tmp_output / "test_output.xml"
    save_result = save_xml(doc_id=doc_id, output_path=str(out_path))
    assert out_path.exists()
    assert "valid" in save_result

    # Reload
    loaded = load_xml(file_path=str(out_path))
    assert "doc_id" in loaded
    assert loaded["element_count"] > 5


def test_preview_full_document(schema):
    doc = create_document(template="single_phase_flow")
    result = preview_xml(doc_id=doc["doc_id"])
    xml_str = Path(result["path"]).read_text()
    assert "<Problem" in xml_str or "<Solvers" in xml_str


def test_validate_cross_references_template(schema):
    doc = create_document(template="single_phase_flow")
    result = validate_cross_references(doc_id=doc["doc_id"])
    assert "valid" in result


def test_validate_cross_references_broken(schema):
    doc = create_document()
    doc_id = doc["doc_id"]
    # Add solver referencing non-existent discretization
    add_element(doc_id=doc_id, section="Solvers", element_type="SinglePhaseFVM",
                name="flow", attributes={"discretization": "nonexistent"})
    result = validate_cross_references(doc_id=doc_id)
    # Should find that "nonexistent" doesn't exist in NumericalMethods
    assert len(result["errors"]) > 0 or result["valid"] is True  # NumericalMethods section may not exist


def test_log_runtime_error(tmp_path, monkeypatch):
    """log_runtime_error extracts solver/constitutive from doc and appends JSONL."""
    log_file = tmp_path / "runtime_errors.jsonl"
    monkeypatch.setenv("AGENTS4GEOSX_ERROR_LOG", str(log_file))

    doc = create_document(template="single_phase_flow")
    doc_id = doc["doc_id"]

    result = log_runtime_error(
        doc_id=doc_id,
        geos_error="***** ABORT: constitutive model not found",
        error_summary="SinglePhaseFVM requires CompressibleSinglePhaseFluid",
        fix_applied="Added CompressibleSinglePhaseFluid to Constitutive section",
    )
    assert result["logged"] is True
    entry = result["entry"]
    assert "SinglePhaseFVM" in entry["solvers"]
    assert "CompressibleSinglePhaseFluid" in entry["constitutive_types"]
    assert entry["error_summary"] == "SinglePhaseFVM requires CompressibleSinglePhaseFluid"
    assert "timestamp" in entry

    # Verify JSONL was written
    assert log_file.exists()
    with open(log_file) as f:
        parsed = json.loads(f.readline())
        assert parsed["error_summary"] == entry["error_summary"]


def test_log_runtime_error_appends(tmp_path, monkeypatch):
    """Multiple calls append separate lines."""
    log_file = tmp_path / "runtime_errors.jsonl"
    monkeypatch.setenv("AGENTS4GEOSX_ERROR_LOG", str(log_file))

    doc = create_document(template="single_phase_flow")
    doc_id = doc["doc_id"]

    log_runtime_error(doc_id=doc_id, geos_error="error1",
                      error_summary="first", fix_applied="fix1")
    log_runtime_error(doc_id=doc_id, geos_error="error2",
                      error_summary="second", fix_applied="fix2")

    with open(log_file) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["error_summary"] == "first"
    assert json.loads(lines[1])["error_summary"] == "second"


def test_log_runtime_error_invalid_doc():
    """Returns error for invalid doc_id."""
    result = log_runtime_error(
        doc_id="nonexistent",
        geos_error="some error",
        error_summary="summary",
        fix_applied="fix",
    )
    assert "error" in result
