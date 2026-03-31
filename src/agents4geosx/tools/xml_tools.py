"""XML assembly & validation MCP tools (Group 4)."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from agents4geosx.config import get_schema, ServerConfig
from agents4geosx.server import mcp
from agents4geosx.state.documents import DocumentStore
from geos_tui.xml.reader import XMLReader
from geos_tui.xml.writer import XMLWriter
from geos_tui.xml.state import DocumentState, ElementState
from geos_tui.domain.templates import build_template_state, TEMPLATES
from agents4geosx.knowledge.cross_refs import ATTRIBUTE_REFERENCES
from agents4geosx.knowledge.sanity_rules import run_sanity_checks

_store = DocumentStore()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_section(doc: DocumentState, section_name: str) -> ElementState | None:
    for child in doc.root.children:
        if child.schema_element.name == section_name:
            return child
    return None


def _find_element_by_path(doc: DocumentState, path: str) -> ElementState | None:
    """Find element by path like 'Solvers/SinglePhaseFVM[@name=\\'flow\\']'."""
    parts = path.split("/")
    current = doc.root
    for part in parts:
        if "[@name='" in part:
            elem_type = part.split("[@name='")[0]
            elem_name = part.split("[@name='")[1].rstrip("']")
            found = None
            for child in current.children:
                if child.schema_element.name == elem_type and child.attributes.get("name") == elem_name:
                    found = child
                    break
            if found is None:
                return None
            current = found
        else:
            found = None
            for child in current.children:
                if child.schema_element.name == part:
                    found = child
                    break
            if found is None:
                return None
            current = found
    return current


def _walk_for_refs(el: ElementState, name: str, path: str, refs: list[str]) -> None:
    current_path = f"{path}/{el.schema_element.name}" if path else el.schema_element.name
    for attr_name, attr_value in el.attributes.items():
        if name in str(attr_value) and attr_name in ATTRIBUTE_REFERENCES:
            refs.append(f"{current_path}/@{attr_name} references '{name}'")
    for child in el.children:
        _walk_for_refs(child, name, current_path, refs)


def _count_elements(el: ElementState) -> int:
    return 1 + sum(_count_elements(c) for c in el.children)


def _count_unknown(el: ElementState) -> int:
    count = 1 if el.read_only else 0
    return count + sum(_count_unknown(c) for c in el.children)


def _collect_names_recursive(el: ElementState, names: set[str]) -> None:
    """Recursively collect all named elements within a section."""
    for child in el.children:
        name = child.attributes.get("name")
        if name:
            names.add(name)
        _collect_names_recursive(child, names)


def _collect_attrs(el: ElementState, attrs: dict) -> None:
    attrs.update(el.attributes)
    for child in el.children:
        _collect_attrs(child, attrs)


def _run_xmllint(path: Path) -> dict:
    cfg = ServerConfig()
    try:
        result = subprocess.run(
            ["xmllint", "--schema", str(cfg.schema_path), str(path), "--noout"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"valid": True, "errors": []}
        errors = [{"message": line} for line in result.stderr.strip().split("\n")
                  if line and "validates" not in line]
        return {"valid": False, "errors": errors}
    except FileNotFoundError:
        return {"valid": None, "errors": [{"message": "xmllint not installed"}]}


def _check_refs(el: ElementState, path: str, named: dict[str, set[str]], errors: list) -> None:
    current = f"{path}/{el.schema_element.name}" if path else el.schema_element.name
    for attr_name, attr_value in el.attributes.items():
        if attr_name in ATTRIBUTE_REFERENCES:
            ref = ATTRIBUTE_REFERENCES[attr_name]
            target_section = ref["target_section"]
            if target_section in named:
                value = attr_value.strip()
                if value.startswith("{") and value.endswith("}"):
                    ref_names = [n.strip() for n in value[1:-1].split(",")]
                else:
                    ref_names = [value]
                for ref_name in ref_names:
                    if ref_name and ref_name not in named[target_section]:
                        errors.append({
                            "source": f"{current}/@{attr_name}",
                            "target": f"{target_section}/{ref_name}",
                            "message": f"'{ref_name}' not found in {target_section}",
                        })
    for child in el.children:
        _check_refs(child, current, named, errors)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool
def list_templates() -> list[dict]:
    """List available document templates with their descriptions."""
    return [
        {
            "key": key,
            "label": tmpl["label"],
            "description": tmpl["description"],
            "sections": list(tmpl["sections"].keys()),
        }
        for key, tmpl in TEMPLATES.items()
    ]


@mcp.tool
def generate_geometry_boxes(
    domain_lx: float,
    domain_ly: float,
    domain_lz: float,
    cell_dx: float,
    cell_dy: float,
    cell_dz: float,
) -> dict:
    """Generate standard geometry boxes for boundary conditions that correctly enclose cell centers.

    Produces boxes for: all, xneg (left), xpos (right), yneg (front), ypos (back), zneg (bottom), zpos (top).
    Each box extends one cell deep to capture ElementRegions cell centers.

    Args:
        domain_lx: Domain length in X (meters)
        domain_ly: Domain length in Y (meters)
        domain_lz: Domain length in Z (meters)
        cell_dx: Cell size in X (meters)
        cell_dy: Cell size in Y (meters)
        cell_dz: Cell size in Z (meters)
    """
    tol = 0.01
    boxes = {
        "all": {
            "xMin": f"{{ {-tol}, {-tol}, {-tol} }}",
            "xMax": f"{{ {domain_lx + tol}, {domain_ly + tol}, {domain_lz + tol} }}",
        },
        "xneg": {
            "xMin": f"{{ {-tol}, {-tol}, {-tol} }}",
            "xMax": f"{{ {cell_dx + tol}, {domain_ly + tol}, {domain_lz + tol} }}",
        },
        "xpos": {
            "xMin": f"{{ {domain_lx - cell_dx - tol}, {-tol}, {-tol} }}",
            "xMax": f"{{ {domain_lx + tol}, {domain_ly + tol}, {domain_lz + tol} }}",
        },
        "yneg": {
            "xMin": f"{{ {-tol}, {-tol}, {-tol} }}",
            "xMax": f"{{ {domain_lx + tol}, {cell_dy + tol}, {domain_lz + tol} }}",
        },
        "ypos": {
            "xMin": f"{{ {-tol}, {domain_ly - cell_dy - tol}, {-tol} }}",
            "xMax": f"{{ {domain_lx + tol}, {domain_ly + tol}, {domain_lz + tol} }}",
        },
        "zneg": {
            "xMin": f"{{ {-tol}, {-tol}, {-tol} }}",
            "xMax": f"{{ {domain_lx + tol}, {domain_ly + tol}, {cell_dz + tol} }}",
        },
        "zpos": {
            "xMin": f"{{ {-tol}, {-tol}, {domain_lz - cell_dz - tol} }}",
            "xMax": f"{{ {domain_lx + tol}, {domain_ly + tol}, {domain_lz + tol} }}",
        },
    }

    xml_snippets = []
    for name, coords in boxes.items():
        xml_snippets.append(f'<Box name="{name}" xMin="{coords["xMin"]}" xMax="{coords["xMax"]}"/>')

    return {"boxes": boxes, "xml_snippets": xml_snippets}


@mcp.tool
def create_document(template: str | None = None) -> dict:
    """Create a new GEOS XML document, optionally from a template.

    Args:
        template: 'blank', 'single_phase_flow', 'compositional_two_phase', 'co2_injection', or None
    """
    schema = get_schema()
    if template and template != "blank":
        doc = build_template_state(template, schema)
    else:
        root_state = ElementState(schema_element=schema.root)
        doc = DocumentState(root=root_state)
    doc_id = _store.create(doc)
    sections = [c.schema_element.name for c in doc.root.children]
    return {
        "doc_id": doc_id,
        "sections": sections,
        "summary": f"Created from {'template: ' + template if template else 'blank'}",
    }


@mcp.tool
def add_element(doc_id: str, section: str, element_type: str, name: str, attributes: dict) -> dict:
    """Add an element to a section of the document.

    Args:
        doc_id: Document ID from create_document or load_xml
        section: Section name (e.g., 'Solvers', 'Constitutive')
        element_type: Element type (e.g., 'SinglePhaseFVM')
        name: Value for the 'name' attribute (pass empty string for elements
              that don't accept a name, e.g. FiniteVolume)
        attributes: Dict of attribute name->value pairs
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}
    schema = get_schema()
    el_schema = schema.elements.get(element_type)
    if el_schema is None:
        return {"error": f"Element type '{element_type}' not found in schema"}

    section_state = _find_section(doc, section)
    if section_state is None:
        section_schema = next((c for c in schema.root.children if c.name == section), None)
        if section_schema is None:
            return {"error": f"Section '{section}' not in schema"}
        section_state = ElementState(schema_element=section_schema)
        doc.root.children.append(section_state)

    has_name_attr = any(a.name == "name" for a in el_schema.attributes)
    attrs = {**attributes}
    warnings = []
    if name:
        if has_name_attr:
            attrs["name"] = name
        else:
            warnings.append(
                f"{element_type} does not accept a 'name' attribute in the schema "
                f"— the provided name '{name}' was ignored"
            )
    new_state = ElementState(schema_element=el_schema, attributes=attrs)
    section_state.children.append(new_state)
    doc.is_modified = True

    for ra in el_schema.attributes:
        if ra.required and ra.name not in attrs and ra.name != "name":
            warnings.append(f"Missing required attribute: {ra.name}")

    path_suffix = f"[@name='{name}']" if name and has_name_attr else ""
    return {"element_path": f"{section}/{element_type}{path_suffix}", "warnings": warnings}


@mcp.tool
def update_element(doc_id: str, element_path: str, attributes: dict) -> dict:
    """Update attributes on an existing element.

    Args:
        doc_id: Document ID
        element_path: Path like "Solvers/SinglePhaseFVM[@name='flow']"
        attributes: Dict of attribute name->value pairs to set
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}
    el = _find_element_by_path(doc, element_path)
    if el is None:
        return {"error": f"Element not found at path: {element_path}"}
    el.attributes.update(attributes)
    doc.is_modified = True
    return {"updated_attrs": list(attributes.keys()), "warnings": []}


@mcp.tool
def remove_element(doc_id: str, element_path: str) -> dict:
    """Remove an element from the document and report any dangling references.

    Args:
        doc_id: Document ID
        element_path: Path to the element to remove
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    # Find the parent by walking to one level above
    parts = element_path.split("/")
    if len(parts) < 2:
        return {"error": "Path must have at least section/element"}

    # Find the target and its parent
    target = _find_element_by_path(doc, element_path)
    if target is None:
        return {"error": f"Element not found: {element_path}"}

    parent_path = "/".join(parts[:-1])
    parent = _find_element_by_path(doc, parent_path) if len(parts) > 2 else None
    if parent is None:
        # Parent is a top-level section
        for child in doc.root.children:
            if child.schema_element.name == parts[0]:
                parent = child
                break

    if parent is None:
        return {"error": f"Parent not found for: {element_path}"}

    removed_name = target.attributes.get("name", "")
    parent.children.remove(target)
    doc.is_modified = True

    dangling: list[str] = []
    if removed_name:
        _walk_for_refs(doc.root, removed_name, "", dangling)

    return {"removed": True, "dangling_references": dangling}


@mcp.tool
def add_child(doc_id: str, parent_path: str, element_type: str, name: str, attributes: dict) -> dict:
    """Add a child element under an existing parent element.

    Args:
        doc_id: Document ID
        parent_path: Path to parent (e.g., "Solvers/SinglePhaseFVM[@name='flow']")
        element_type: Child element type (e.g., 'NonlinearSolverParameters')
        name: Name attribute (pass empty string for elements that don't accept a name)
        attributes: Attribute dict
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}
    schema = get_schema()
    parent = _find_element_by_path(doc, parent_path)
    if parent is None:
        return {"error": f"Parent not found: {parent_path}"}
    child_schema = schema.elements.get(element_type)
    if child_schema is None:
        return {"error": f"Element type '{element_type}' not found"}

    has_name_attr = any(a.name == "name" for a in child_schema.attributes)
    warnings = []
    attrs = {**attributes}
    if name:
        if has_name_attr:
            attrs["name"] = name
        else:
            warnings.append(
                f"{element_type} does not accept a 'name' attribute in the schema "
                f"— the provided name '{name}' was ignored"
            )
    child_state = ElementState(schema_element=child_schema, attributes=attrs)
    parent.children.append(child_state)
    doc.is_modified = True
    path = f"{parent_path}/{element_type}" + (f"[@name='{name}']" if name and has_name_attr else "")
    return {"element_path": path, "warnings": warnings}


@mcp.tool
def load_xml(file_path: str) -> dict:
    """Load an existing GEOS XML file for editing. Preserves comments and unknown elements.

    Args:
        file_path: Path to the XML file
    """
    schema = get_schema()
    reader = XMLReader(schema)
    doc = reader.load(Path(file_path))
    doc_id = _store.create(doc)
    return {
        "doc_id": doc_id,
        "sections": [c.schema_element.name for c in doc.root.children],
        "element_count": _count_elements(doc.root),
        "unknown_elements": _count_unknown(doc.root),
        "summary": f"Loaded {file_path}",
    }


@mcp.tool
def save_xml(doc_id: str, output_path: str) -> dict:
    """Save a document to XML file and auto-validate with xmllint.

    Args:
        doc_id: Document ID
        output_path: File path to write the XML to
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}
    writer = XMLWriter()
    path = Path(output_path)
    writer.save(doc, path)
    doc.is_modified = False
    doc.source_path = path
    validation = _run_xmllint(path)
    return {"path": str(path), **validation}


@mcp.tool
def preview_xml(doc_id: str, section: str | None = None, output_path: str | None = None) -> dict:
    """Preview XML content of a document. Writes to a temp file for readable display.

    Args:
        doc_id: Document ID
        section: Optional section name to preview (e.g., 'Solvers')
        output_path: Optional file path to write preview. If not provided, writes to /tmp/geos_preview.xml
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}
    writer = XMLWriter()
    root_el = writer._build_element(doc.root)
    if section:
        section_el = root_el.find(section)
        if section_el is None:
            return {"error": f"Section '{section}' not found"}
        xml_str = etree.tostring(section_el, pretty_print=True, encoding="unicode")
    else:
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root_el, pretty_print=True, encoding="unicode")

    preview_path = Path(output_path) if output_path else Path("/tmp/geos_preview.xml")
    preview_path.write_text(xml_str, encoding="utf-8")
    return {"path": str(preview_path), "lines": xml_str.count("\n") + 1}


@mcp.tool
def validate_xml(file_path: str) -> dict:
    """Validate an XML file against the GEOS XSD schema using xmllint.

    Args:
        file_path: Path to the XML file to validate
    """
    return _run_xmllint(Path(file_path))


@mcp.tool
def validate_cross_references(doc_id: str) -> dict:
    """Check that all internal cross-references in the document resolve correctly.

    Args:
        doc_id: Document ID
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    named: dict[str, set[str]] = {}
    for section in doc.root.children:
        section_name = section.schema_element.name
        named[section_name] = set()
        _collect_names_recursive(section, named[section_name])

    errors: list[dict] = []
    _check_refs(doc.root, "", named, errors)
    return {"valid": len(errors) == 0, "errors": errors}


@mcp.tool
def diff_xml(file_path_a: str, file_path_b: str) -> dict:
    """Compare two XML files and return a structured diff.

    Args:
        file_path_a: Path to first XML file
        file_path_b: Path to second XML file
    """
    tree_a = etree.parse(file_path_a)
    tree_b = etree.parse(file_path_b)
    diffs: list[dict] = []
    _diff_elements(tree_a.getroot(), tree_b.getroot(), "", diffs)
    return {"differences": diffs, "count": len(diffs)}


def _diff_elements(a, b, path: str, diffs: list) -> None:
    tag = a.tag if a is not None else b.tag
    current = f"{path}/{tag}" if path else tag
    if a is None:
        diffs.append({"path": current, "type": "added"})
        return
    if b is None:
        diffs.append({"path": current, "type": "removed"})
        return
    a_attrs, b_attrs = dict(a.attrib), dict(b.attrib)
    for key in set(a_attrs) | set(b_attrs):
        if key not in a_attrs:
            diffs.append({"path": f"{current}/@{key}", "type": "added", "value": b_attrs[key]})
        elif key not in b_attrs:
            diffs.append({"path": f"{current}/@{key}", "type": "removed", "value": a_attrs[key]})
        elif a_attrs[key] != b_attrs[key]:
            diffs.append({"path": f"{current}/@{key}", "type": "changed", "from": a_attrs[key], "to": b_attrs[key]})
    a_children = {(c.tag, c.get("name", "")): c for c in a}
    b_children = {(c.tag, c.get("name", "")): c for c in b}
    for key in set(a_children) | set(b_children):
        _diff_elements(a_children.get(key), b_children.get(key), current, diffs)


@mcp.tool
def log_runtime_error(
    doc_id: str,
    geos_error: str,
    error_summary: str,
    fix_applied: str,
) -> dict:
    """Log a GEOS runtime error with full context for future learning.

    Call this AFTER diagnosing and fixing (or failing to fix) a GEOS runtime error.
    Extracts solver and constitutive types from the document automatically.

    Args:
        doc_id: Document ID of the XML that caused the error.
        geos_error: Raw GEOS error text (copy the relevant lines).
        error_summary: Your one-line diagnosis of what went wrong.
        fix_applied: What resolved the issue, or "UNRESOLVED" if unfixed after 3 attempts.
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    # Extract context from document
    xml_file = doc.source_path.name if doc.source_path else "unknown"
    solvers = []
    constitutive_types = []
    for section in doc.root.children:
        sec_name = section.schema_element.name
        if sec_name == "Solvers":
            for child in section.children:
                solvers.append(child.schema_element.name)
        elif sec_name == "Constitutive":
            for child in section.children:
                constitutive_types.append(child.schema_element.name)

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "xml_file": xml_file,
        "solvers": solvers,
        "constitutive_types": constitutive_types,
        "geos_error": geos_error,
        "error_summary": error_summary,
        "fix_applied": fix_applied,
    }

    # Append to JSONL log
    log_path = os.environ.get(
        "AGENTS4GEOSX_ERROR_LOG",
        str(Path(__file__).resolve().parent.parent.parent.parent / "knowledge" / "runtime_errors.jsonl"),
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"logged": True, "entry": entry, "log_file": log_path}
