"""Regression tests for three sanity_check gaps (agents4geos-j3a):

1. list-valued attributes (GEOS `{ ... }` literals) were silently skipped by a bare
   float(), so an out-of-range permeability was never flagged;
2. the rule matcher did not lowercase the pattern, so mixed-case patterns
   (`referencePorosity`, `cflFactor`) never matched any attribute — dead rules;
3. attributes were collected into a name-keyed dict, so same-named attributes on
   different elements (e.g. two `referencePressure`) collided and only the last
   survived.

`run_sanity_checks` now takes a list of (attr_name, value) pairs so duplicates are
preserved; `_collect_all_attrs` builds that list.
"""
from pathlib import Path

from agents4geos.knowledge.sanity_rules import run_sanity_checks

FIX = Path(__file__).resolve().parent / "fixtures" / "review"


def _checks(name, results):
    return [c for c in results if c["name"] == name]


# --- Bug 1: list-valued (GEOS `{ ... }`) attributes ------------------------------

def test_permeability_list_literal_out_of_range_is_flagged():
    res = run_sanity_checks([("permeabilityComponents", "{ 1e-2, 1e-2, 1e-2 }")])
    perm = _checks("permeability_range", res)
    assert perm and any(c["status"] == "fail" for c in perm)


def test_permeability_list_literal_in_range_passes():
    res = run_sanity_checks([("permeabilityComponents", "{ 1e-16, 1e-16, 1e-16 }")])
    perm = _checks("permeability_range", res)
    assert perm and all(c["status"] == "pass" for c in perm)


def test_permeability_list_with_one_bad_component_fails():
    res = run_sanity_checks([("permeabilityComponents", "{ 1e-16, 1e-2, 1e-16 }")])
    assert any(c["status"] == "fail" for c in _checks("permeability_range", res))


# --- Bug 2: case-insensitive pattern matching ------------------------------------

def test_porosity_rule_matches_default_reference_porosity():
    # 'referencePorosity' pattern must match 'defaultReferencePorosity'
    res = run_sanity_checks([("defaultReferencePorosity", "0.8")])  # > 0.5 ceiling
    por = _checks("porosity_range", res)
    assert por and any(c["status"] == "fail" for c in por)


def test_cfl_rule_matches_cfl_factor():
    res = run_sanity_checks([("cflFactor", "5")])  # > 1
    cfl = _checks("cfl_range", res)
    assert cfl and any(c["status"] == "fail" for c in cfl)


# --- Bug 3: duplicate-named attributes are not deduped ---------------------------

def test_run_sanity_checks_evaluates_duplicate_named_attrs():
    res = run_sanity_checks([("referencePressure", "-100"), ("referencePressure", "0.0")])
    press = _checks("pressure_positive", res)
    statuses = sorted(c["status"] for c in press)
    assert statuses == ["fail", "pass"]  # both evaluated, not collapsed to one


def test_collect_all_attrs_preserves_duplicate_names():
    from agents4geos.tools.postproc_tools import _collect_all_attrs
    from agents4geos.tools.xml_tools import load_xml, _store

    doc_id = load_xml(str(FIX / "negative_pressure.xml"))["doc_id"]
    doc = _store.get(doc_id)
    pairs: list[tuple[str, str]] = []
    _collect_all_attrs(doc.root, pairs)
    rp = [v for (n, v) in pairs if n == "referencePressure"]
    assert rp.count("-100") == 2  # both occurrences preserved, not flattened to one


# --- Regression: scalar path still works -----------------------------------------

def test_scalar_negative_pressure_still_flagged():
    res = run_sanity_checks([("referencePressure", "-100")])
    assert any(c["status"] == "fail" for c in _checks("pressure_positive", res))


def test_scalar_in_range_passes():
    res = run_sanity_checks([("temperature", "300")])  # within 273..573 K
    temp = _checks("temperature_range", res)
    assert temp and all(c["status"] == "pass" for c in temp)


# --- Conditional requirements (agents4geos-evo) ----------------------------------

def test_massrate_without_surface_conditions_fails_structure_check():
    from agents4geos.knowledge.sanity_rules import check_document_structure
    from agents4geos.tools.xml_tools import load_xml, _store

    doc_id = load_xml(str(FIX / "massrate_missing_surface.xml"))["doc_id"]
    doc = _store.get(doc_id)
    results = check_document_structure(doc.root)
    cond = [c for c in results if c["name"] == "conditional_requirement"]
    assert cond, "massRate without useSurfaceConditions must produce a conditional_requirement result"
    assert any(c["status"] == "fail" and "useSurfaceConditions" in c["attribute"] for c in cond)


def test_massrate_with_surface_conditions_passes():
    from agents4geos.knowledge.sanity_rules import check_document_structure
    from agents4geos.tools.xml_tools import load_xml, _store
    import tempfile, pathlib

    xml = (FIX / "massrate_missing_surface.xml").read_text().replace(
        'control="massRate"',
        'control="massRate" useSurfaceConditions="1" surfacePressure="101325" '
        'surfaceTemperature="288.71"',
    )
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "ok.xml"
        p.write_text(xml)
        doc_id = load_xml(str(p))["doc_id"]
    doc = _store.get(doc_id)
    cond = [c for c in check_document_structure(doc.root)
            if c["name"] == "conditional_requirement"]
    assert cond and all(c["status"] == "pass" for c in cond)
