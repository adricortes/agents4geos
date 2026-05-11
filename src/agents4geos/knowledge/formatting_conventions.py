"""GEOS XML output formatting conventions.

Encodes the formatting rules used by geos-xml-tools to produce
canonical XML output. Use these conventions when generating XML
so the agent's output matches the style of hand-edited GEOS files.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools
"""

from __future__ import annotations

DEFAULT_FORMAT: dict = {
    "indent": 2,
    "style": "fixed",
    "block_separation_max_depth": 2,
    "sort_attributes": False,
    "close_tag_newline": False,
}

ATTRIBUTE_FORMATTING: dict[str, dict] = {
    "comma_spacing": {
        "pattern": r",\s*",
        "replacement": ", ",
    },
    "brace_opening": {
        "pattern": r"\{\s*",
        "replacement": "{ ",
    },
    "brace_closing": {
        "pattern": r"\s*\}",
        "replacement": " }",
    },
    "whitespace_consolidation": {
        "pattern": r"\s+",
        "replacement": " ",
    },
    "array_split_pattern": r"\s*\{\s*(\{[-+.,0-9a-zA-Z\s]*\},?\s*)*\s*\}",
}

PROTECTED_EXPRESSIONS: list[dict] = [
    {"element": "SymbolicFunction", "attribute": "expression"},
    {"element": "CompositeFunction", "attribute": "expression"},
]
