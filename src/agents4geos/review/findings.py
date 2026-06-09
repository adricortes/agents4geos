"""Canonical contract for geos-reviewer findings.

The geos-reviewer subagent returns a JSON list of findings; this module is the
single source of truth for that shape. Used by the review eval harness now, and
the designed-in sink for a future Dolt errors/lessons table (see
docs/superpowers/specs/2026-06-09-independent-reviewer-subagent-design.md sec.5).
"""
from __future__ import annotations

from dataclasses import dataclass

SEVERITIES = ("error", "warning", "advisory")
CATEGORIES = ("schema", "xref", "physics", "intent")
BLOCKING_SEVERITIES = ("error", "warning")


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    category: str
    location: str
    issue: str
    suggested_fix: str
    intent_mismatch: bool = False

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"invalid severity {self.severity!r}; expected one of {SEVERITIES}"
            )
        if self.category not in CATEGORIES:
            raise ValueError(
                f"invalid category {self.category!r}; expected one of {CATEGORIES}"
            )

    @property
    def is_blocking(self) -> bool:
        return self.severity in BLOCKING_SEVERITIES


def parse_findings(items: list[dict]) -> list[ReviewFinding]:
    """Validate and parse the reviewer's JSON output into ReviewFinding objects.

    Raises ValueError if any item is missing required keys or has an invalid
    severity/category.
    """
    required = {"severity", "category", "location", "issue", "suggested_fix"}
    findings: list[ReviewFinding] = []
    for i, item in enumerate(items):
        missing = required - item.keys()
        if missing:
            raise ValueError(f"finding[{i}] missing keys: {sorted(missing)}")
        findings.append(
            ReviewFinding(
                severity=item["severity"],
                category=item["category"],
                location=item["location"],
                issue=item["issue"],
                suggested_fix=item["suggested_fix"],
                intent_mismatch=item.get("intent_mismatch", False),
            )
        )
    return findings


def has_blocking(findings: list[ReviewFinding]) -> bool:
    """True if any finding is error/warning (drives the orchestrator fix loop)."""
    return any(f.is_blocking for f in findings)
