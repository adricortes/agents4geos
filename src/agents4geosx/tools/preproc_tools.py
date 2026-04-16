"""XML preprocessing MCP tools (Group 6).

Tools for unit conversion, parameter expansion, include resolution,
and XML formatting. Uses knowledge modules from the knowledge enrichment
(Part 1) implementation.
"""
from __future__ import annotations

import re

from agents4geosx.server import mcp
from agents4geosx.knowledge.unit_conventions import (
    UNIT_DEFINITIONS,
    SI_PREFIXES,
    BRACKET_NOTATION_REGEX,
    validate_unit_expression,
)


def _build_unit_scale_map() -> dict[str, float]:
    """Build a map from every valid unit name/alias to its SI scale factor."""
    scales: dict[str, float] = {}
    for name, defn in UNIT_DEFINITIONS.items():
        scales[name] = defn["value"]
        for alt in defn["alt"]:
            scales[alt] = defn["value"]
        if defn["usePrefix"]:
            for prefix_name, prefix_def in SI_PREFIXES.items():
                if prefix_name:
                    pval = prefix_def["value"]
                    scales[prefix_name + name] = pval * defn["value"]
                    scales[prefix_def["alt"] + name] = pval * defn["value"]
                    for alt in defn["alt"]:
                        scales[prefix_name + alt] = pval * defn["value"]
                        scales[prefix_def["alt"] + alt] = pval * defn["value"]
    return scales


_UNIT_SCALES = _build_unit_scale_map()
_UNIT_NAME_RE = re.compile(r"[a-zA-Z]+")


def _evaluate_unit_expression(unit_expr: str) -> float:
    """Replace unit names with scale factors and evaluate the arithmetic."""
    def _replace_unit(match: re.Match) -> str:
        name = match.group(0)
        if name in _UNIT_SCALES:
            return str(_UNIT_SCALES[name])
        if name in ("e", "E"):
            return name
        return name

    substituted = _UNIT_NAME_RE.sub(_replace_unit, unit_expr)
    # Sanitize: only allow digits, operators, dots, e/E, spaces, parens
    sanitized = re.sub(r"[a-df-zA-DF-Z]", "", substituted)
    return float(eval(sanitized, {"__builtins__": None}))


@mcp.tool
def convert_units(expression: str) -> dict:
    """Convert a GEOS bracket-notation expression to SI units.

    Parses expressions like "9.81[m/s**2]" or "100[mD]" and returns the
    SI-converted value. Supports all GEOS unit names, aliases, and SI prefixes.

    Args:
        expression: A string possibly containing bracket notation (e.g., "100[mD]")
    """
    match = re.search(BRACKET_NOTATION_REGEX, expression)
    if match is None:
        return {
            "original": expression,
            "si_value": None,
            "valid": True,
            "message": "No bracket notation found",
        }

    numeric_str = match.group(1)
    unit_expr = match.group(2)
    numeric_value = float(numeric_str)

    validation = validate_unit_expression(expression)
    if not validation["valid"]:
        return {
            "original": expression,
            "numeric_value": numeric_value,
            "unit_expression": unit_expr,
            "si_value": None,
            "valid": False,
            "unknown_units": validation["unknown"],
        }

    si_scale = _evaluate_unit_expression(unit_expr)
    si_value = numeric_value * si_scale

    return {
        "original": expression,
        "numeric_value": numeric_value,
        "unit_expression": unit_expr,
        "si_value": si_value,
        "units_found": validation["units_found"],
        "valid": True,
    }
