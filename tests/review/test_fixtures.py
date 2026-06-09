"""Validates the review fixtures: tool-catchable defects ARE caught by the
deterministic MCP tools; intent-mismatch defects are NOT (so only the LLM
reviewer can catch them — which is the whole point of geos-reviewer).

Tool return shapes (verified against source 2026-06-09):
  validate_xml(path)               -> {"valid": True|False|None, "errors": [...]}
                                      (None = xmllint not installed; False can ALSO
                                      mean no GEOS schema.xsd is configured — see
                                      _xsd_available below)
  load_xml(path)                   -> {"doc_id": "...", ...}
  validate_cross_references(doc)   -> {"valid": bool, "errors": [...]}
  sanity_check(doc)                -> {"checks": [{"status": "fail|advisory|pass",
                                       "message": ...}], "total": int, "failures": int}
These tools are plain callable functions (not FastMCP-wrapped) and share a
module-level DocumentStore, so load_xml then validate/sanity in sequence works.
sanity_check lives in postproc_tools, the rest in xml_tools.

Environment note: validate_xml shells out to `xmllint --schema <GEOS schema.xsd>`.
The repo ships a parsed schema.json (so get_schema works) but NOT the raw
schema.xsd, which is a GEOS build artifact. When GEOS_SCHEMA is unset and no
.xsd exists, xmllint cannot validate and validate_xml returns valid=False for
EVERY deck — an environmental indeterminacy, not a deck defect. The schema
assertion below is therefore gated on _xsd_available(); the xref + sanity
assertions (which need no .xsd) carry the load-bearing proof regardless.
"""
import json
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "review"


def _manifest():
    return json.loads((FIX / "manifest.json").read_text())


def _xsd_available() -> bool:
    """True only if a GEOS schema.xsd is configured AND present — i.e. xmllint
    can actually schema-validate. Otherwise validate_xml's verdict is meaningless."""
    from agents4geos.config import ServerConfig

    sp = ServerConfig().schema_path
    return sp is not None and Path(sp).exists()


@pytest.mark.parametrize("case", _manifest()["cases"], ids=lambda c: c["name"])
def test_fixture_exists_and_is_xml(case):
    p = FIX / f"{case['name']}.xml"
    assert p.exists() and p.read_text().lstrip().startswith("<")


def test_intent_mismatch_passes_deterministic_tools():
    """The duration-mismatch deck must be schema-valid and pass sanity/xref —
    proving the deterministic layer cannot catch intent errors."""
    from agents4geos.tools.xml_tools import (
        load_xml, validate_cross_references, validate_xml,
    )
    from agents4geos.tools.postproc_tools import sanity_check

    deck = str(FIX / "duration_mismatch.xml")
    # Schema validity is only meaningful when an XSD is configured. Without one,
    # xmllint returns False for every deck (missing schema resource), so skip the
    # assertion rather than fail on an environmental gap.
    if _xsd_available():
        assert validate_xml(deck)["valid"] is not False
    doc = load_xml(deck)["doc_id"]
    assert validate_cross_references(doc)["errors"] == []
    checks = sanity_check(doc)["checks"]
    assert not any(c["status"] == "fail" for c in checks)


def test_tool_catchable_defects_are_caught():
    """The contrast that justifies the fixtures: the defects labelled
    tool_catchable in the manifest ARE flagged by the deterministic tools
    (xref for the broken materialList ref, sanity for the negative pressure),
    while the intent defect (tested above) is not."""
    from agents4geos.tools.xml_tools import load_xml, validate_cross_references
    from agents4geos.tools.postproc_tools import sanity_check

    xref_doc = load_xml(str(FIX / "broken_materiallist_ref.xml"))["doc_id"]
    xref_errors = validate_cross_references(xref_doc)["errors"]
    assert any("nonexistentRock" in str(e) for e in xref_errors)

    phys_doc = load_xml(str(FIX / "negative_pressure.xml"))["doc_id"]
    phys_fails = [c for c in sanity_check(phys_doc)["checks"] if c["status"] == "fail"]
    assert any("pressure" in c.get("name", "").lower() for c in phys_fails)
