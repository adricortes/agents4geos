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
from agents4geosx.knowledge.preprocessing_rules import PARAMETER_RULES


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


@mcp.tool
def expand_parameters(doc_id: str) -> dict:
    """Expand $Name$ parameter patterns in all document attributes.

    Reads parameter values from the <Parameters> section and substitutes
    them into all attribute values throughout the document.

    Args:
        doc_id: Document ID from create_document or load_xml
    """
    from agents4geosx.tools.xml_tools import _store

    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    # Build parameter map from <Parameters> section
    param_map: dict[str, str] = {}
    for section in doc.root.children:
        if section.schema_element.name == "Parameters":
            for param in section.children:
                pname = param.attributes.get("name", "")
                pvalue = param.attributes.get("value", "")
                if pname:
                    param_map[pname] = pvalue

    regex = re.compile(PARAMETER_RULES["regex"])
    max_nesting = PARAMETER_RULES["max_nesting"]
    substitutions = 0
    unresolved: set[str] = set()
    details: list[dict] = []

    def _expand_attrs(el, path: str) -> None:
        nonlocal substitutions
        el_name = el.schema_element.name if hasattr(el, "schema_element") else "?"
        current = f"{path}/{el_name}" if path else el_name

        for attr_name in list(el.attributes.keys()):
            attr_value = el.attributes[attr_name]
            if "$" not in attr_value:
                continue
            original = attr_value
            value = attr_value
            iterations = 0
            while "$" in value and iterations < max_nesting:
                def _replace(m: re.Match) -> str:
                    name = m.group(1)
                    if name in param_map:
                        return param_map[name]
                    if name:
                        unresolved.add(name)
                    return m.group(0)
                new_value = regex.sub(_replace, value)
                if new_value == value:
                    break
                value = new_value
                iterations += 1

            if value != original:
                el.attributes[attr_name] = value
                substitutions += 1
                details.append({
                    "path": f"{current}/@{attr_name}",
                    "before": original,
                    "after": value,
                })

        for child in el.children:
            _expand_attrs(child, current)

    _expand_attrs(doc.root, "")

    return {
        "parameters_found": param_map,
        "substitutions_made": substitutions,
        "unresolved": sorted(unresolved),
        "details": details,
    }
