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


# ---------------------------------------------------------------------------
# resolve_includes
# ---------------------------------------------------------------------------

@mcp.tool
def resolve_includes(doc_id: str) -> dict:
    """Merge <Included> file blocks into the document.

    Reads File elements from the <Included> section, parses each referenced
    XML file, and merges its content into the document. The <Included> block
    is replaced with an XML comment listing merged files for provenance.

    Args:
        doc_id: Document ID from create_document or load_xml
    """
    from pathlib import Path
    from lxml import etree
    from agents4geosx.tools.xml_tools import _store
    from agents4geosx.config import get_schema
    from agents4geosx.knowledge.preprocessing_rules import INCLUDE_RULES

    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    include_sections = [
        s for s in doc.root.children
        if s.schema_element.name == "Included"
    ]
    if not include_sections:
        return {"files_merged": [], "elements_added": 0, "comment": ""}

    schema = get_schema()
    insert_only = set(INCLUDE_RULES["insert_only_elements"])
    files_merged: list[str] = []
    elements_added = 0
    errors: list[str] = []

    for inc_section in include_sections:
        for file_el in inc_section.children:
            file_path = file_el.attributes.get("name", "")
            if not file_path:
                continue
            try:
                parser = etree.XMLParser(remove_blank_text=True)
                tree = etree.parse(file_path, parser)
                inc_root = tree.getroot()
                count = _merge_lxml_into_doc(doc.root, inc_root, schema, insert_only)
                elements_added += count
                files_merged.append(file_path)
            except Exception as exc:
                errors.append(f"Failed to include '{file_path}': {exc}")

    # Replace Included sections with provenance comments
    for inc_section in include_sections:
        doc.root.children.remove(inc_section)
    if files_merged:
        file_names = ", ".join(Path(f).name for f in files_merged)
        comment = f"<!-- Included files merged: {file_names} -->"
        doc.root.comments.append(comment)
    else:
        comment = ""

    result: dict = {
        "files_merged": files_merged,
        "elements_added": elements_added,
        "comment": comment,
    }
    if errors:
        result["errors"] = errors
    return result


def _merge_lxml_into_doc(doc_root, lxml_root, schema, insert_only: set) -> int:
    """Merge elements from an lxml tree into the DocumentState tree."""
    from geos_tui.xml.state import ElementState

    count = 0
    for lxml_section in lxml_root:
        if not isinstance(lxml_section.tag, str):
            continue
        section_name = lxml_section.tag

        target_section = None
        for s in doc_root.children:
            if s.schema_element.name == section_name:
                target_section = s
                break
        if target_section is None:
            section_schema = next(
                (c for c in schema.root.children if c.name == section_name),
                None,
            )
            if section_schema is None:
                continue
            target_section = ElementState(schema_element=section_schema)
            doc_root.children.append(target_section)

        for lxml_el in lxml_section:
            if not isinstance(lxml_el.tag, str):
                continue
            el_type = lxml_el.tag
            el_name = lxml_el.get("name", "")

            existing = None
            if el_name and el_type not in insert_only:
                for child in target_section.children:
                    if (child.schema_element.name == el_type and
                            child.attributes.get("name") == el_name):
                        existing = child
                        break

            if existing is not None:
                for attr_name, attr_value in lxml_el.attrib.items():
                    existing.attributes[attr_name] = attr_value
            else:
                schema_el = schema.elements.get(el_type)
                if schema_el is None:
                    continue
                new_el = ElementState(
                    schema_element=schema_el,
                    attributes=dict(lxml_el.attrib),
                )
                target_section.children.append(new_el)
                count += 1

    return count


# ---------------------------------------------------------------------------
# format_xml
# ---------------------------------------------------------------------------

@mcp.tool
def format_xml(input_path: str, output_path: str = "") -> dict:
    """Format a GEOS XML file to match canonical geos-xml-tools style.

    Applies 2-space indentation, attribute value normalization (comma and
    brace spacing), and preserves protected expressions (SymbolicFunction,
    CompositeFunction).

    Args:
        input_path: Path to the XML file to format
        output_path: Path to write formatted output (empty = overwrite input)
    """
    from pathlib import Path
    from lxml import etree
    from agents4geosx.knowledge.formatting_conventions import (
        DEFAULT_FORMAT,
        ATTRIBUTE_FORMATTING,
        PROTECTED_EXPRESSIONS,
    )

    if not Path(input_path).exists():
        return {"error": f"File not found: {input_path}"}

    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(input_path, parser)
        root = tree.getroot()
    except Exception as exc:
        return {"error": f"Failed to parse XML: {exc}"}

    protected_set = {(p["element"], p["attribute"]) for p in PROTECTED_EXPRESSIONS}
    protected_count = _normalize_attributes(root, ATTRIBUTE_FORMATTING, protected_set)

    indent_str = " " * DEFAULT_FORMAT["indent"]
    _indent_tree(root, level=0, indent_str=indent_str)

    out = output_path if output_path else input_path
    tree.write(out, xml_declaration=True, encoding="utf-8", pretty_print=False)
    content = Path(out).read_bytes().decode("utf-8")
    Path(out).write_text(content)

    return {
        "input": input_path,
        "output": out,
        "format_applied": DEFAULT_FORMAT,
        "protected_expressions_preserved": protected_count,
    }


def _normalize_attributes(el, formatting: dict, protected_set: set, depth: int = 0) -> int:
    """Normalize attribute values and protect special expressions."""
    protected_count = 0
    tag = el.tag if isinstance(el.tag, str) else ""

    for attr_name in list(el.attrib.keys()):
        if (tag, attr_name) in protected_set:
            protected_count += 1
            continue
        value = el.get(attr_name)
        for rule_name in ("comma_spacing", "brace_opening", "brace_closing",
                          "whitespace_consolidation"):
            rule = formatting[rule_name]
            value = re.sub(rule["pattern"], rule["replacement"], value)
        el.set(attr_name, value)

    for child in el:
        protected_count += _normalize_attributes(child, formatting, protected_set, depth + 1)
    return protected_count


def _indent_tree(elem, level: int = 0, indent_str: str = "  ") -> None:
    """Add indentation whitespace to an lxml element tree."""
    indent = "\n" + indent_str * level
    child_indent = "\n" + indent_str * (level + 1)

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_indent
        for i, child in enumerate(elem):
            _indent_tree(child, level + 1, indent_str)
            if not child.tail or not child.tail.strip():
                child.tail = child_indent if i < len(elem) - 1 else indent
    if not elem.tail or not elem.tail.strip():
        elem.tail = indent if level > 0 else "\n"
