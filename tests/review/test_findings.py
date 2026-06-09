import pytest
from agents4geos.review.findings import (
    ReviewFinding, parse_findings, has_blocking, SEVERITIES, CATEGORIES,
)


def test_blocking_severities():
    assert ReviewFinding("error", "schema", "Solvers", "x", "y").is_blocking
    assert ReviewFinding("warning", "xref", "a", "x", "y").is_blocking
    assert not ReviewFinding("advisory", "physics", "a", "x", "y").is_blocking


def test_invalid_severity_rejected():
    with pytest.raises(ValueError):
        ReviewFinding("fatal", "schema", "a", "x", "y")


def test_invalid_category_rejected():
    with pytest.raises(ValueError):
        ReviewFinding("error", "nonsense", "a", "x", "y")


def test_parse_findings_roundtrip():
    items = [{"severity": "error", "category": "intent", "location": "Events",
              "issue": "runs 1 month not 1 year",
              "suggested_fix": "set maxTime=3.15e7", "intent_mismatch": True}]
    fs = parse_findings(items)
    assert len(fs) == 1 and fs[0].intent_mismatch and fs[0].is_blocking


def test_parse_findings_missing_key_raises():
    with pytest.raises(ValueError):
        parse_findings([{"severity": "error", "category": "intent"}])


def test_parse_findings_defaults_intent_mismatch_false():
    items = [{"severity": "advisory", "category": "physics", "location": "a",
              "issue": "x", "suggested_fix": "y"}]
    assert parse_findings(items)[0].intent_mismatch is False


def test_has_blocking():
    advisory = parse_findings([{"severity": "advisory", "category": "physics",
                                "location": "a", "issue": "x", "suggested_fix": "y"}])
    assert not has_blocking(advisory)
    blocking = parse_findings([{"severity": "warning", "category": "xref",
                                "location": "a", "issue": "x", "suggested_fix": "y"}])
    assert has_blocking(blocking)
