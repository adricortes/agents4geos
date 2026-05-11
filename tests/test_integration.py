"""End-to-end integration tests: NL → XML → validate."""

from agents4geos.tools.fluid_tools import recommend_fluid_model
from agents4geos.tools.schema_tools import describe_element, lookup_field_names
from agents4geos.tools.mesh_tools import generate_internal_mesh_xml, define_geometry_box
from agents4geos.tools.xml_tools import (
    create_document, add_element, add_child, save_xml,
    validate_cross_references, preview_xml, load_xml,
)
from agents4geos.tools.postproc_tools import sanity_check


def test_single_phase_flow_e2e(schema, tmp_output):
    """Full agent workflow: NL → solver selection → XML assembly → validate → save → reload."""
    # 1. Recommend model
    rec = recommend_fluid_model("single phase water flow through porous rock")
    assert "SinglePhaseFVM" in rec["solver"]

    # 2. Create document
    doc = create_document()
    doc_id = doc["doc_id"]

    # 3. Add solver
    add_element(doc_id, "Solvers", "SinglePhaseFVM", "flow", {
        "discretization": "fluidTPFA",
        "targetRegions": "{ Domain }",
    })

    # 4. Add mesh
    add_element(doc_id, "Mesh", "InternalMesh", "mesh1", {
        "elementTypes": "{ C3D8 }",
        "xCoords": "{ 0, 1000 }",
        "yCoords": "{ 0, 1000 }",
        "zCoords": "{ 0, 100 }",
        "nx": "{ 50 }",
        "ny": "{ 50 }",
        "nz": "{ 10 }",
        "cellBlockNames": "{ block1 }",
    })

    # 5. Add numerical methods
    add_element(doc_id, "NumericalMethods", "FiniteVolume", "fv", {})

    # 6. Add constitutive
    add_element(doc_id, "Constitutive", "CompressibleSinglePhaseFluid", "water", {
        "defaultDensity": "1000",
        "defaultViscosity": "0.001",
        "compressibility": "4.4e-10",
    })

    # 7. Add element region
    add_element(doc_id, "ElementRegions", "CellElementRegion", "Domain", {
        "cellBlocks": "{ block1 }",
        "materialList": "{ water }",
    })

    # 8. Preview
    from pathlib import Path as P  # noqa: N811
    result = preview_xml(doc_id)
    xml_str = P(result["path"]).read_text()
    assert "SinglePhaseFVM" in xml_str
    assert "CompressibleSinglePhaseFluid" in xml_str

    # 9. Validate cross-references
    xref = validate_cross_references(doc_id)
    assert "valid" in xref

    # 10. Save
    out_path = tmp_output / "single_phase.xml"
    result = save_xml(doc_id, str(out_path))
    assert out_path.exists()

    # 11. Reload and verify
    reloaded = load_xml(str(out_path))
    assert reloaded["element_count"] > 5


def test_co2_injection_from_template(schema, tmp_output):
    """Test creating a CO2 injection simulation from template."""
    doc = create_document(template="co2_injection")
    doc_id = doc["doc_id"]

    from pathlib import Path as P2  # noqa: N811
    result = preview_xml(doc_id)
    xml_str = P2(result["path"]).read_text()
    assert len(xml_str) > 100

    # Sanity check
    result = sanity_check(doc_id)
    assert "checks" in result

    out_path = tmp_output / "co2.xml"
    save_xml(doc_id, str(out_path))
    assert out_path.exists()


def test_schema_introspection_chain(schema):
    """Test chaining schema tools as the agent would."""
    # Agent discovers what SinglePhaseFVM needs
    desc = describe_element("SinglePhaseFVM")
    assert desc["name"] == "SinglePhaseFVM"

    # Agent looks up valid field names for BCs
    fields = lookup_field_names("SinglePhaseFVM")
    assert "pressure" in fields

    # Agent generates mesh XML
    mesh_xml = generate_internal_mesh_xml(50, 50, 10, 20.0, 20.0, 10.0)
    assert "<InternalMesh" in mesh_xml

    # Agent generates geometry boxes
    left = define_geometry_box("left", [0, 0, 0], [0, 1000, 100])
    assert '<Box name="left"' in left
