"""XML assembly & validation MCP tools (Group 4)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from lxml import etree

from agents4geosx.config import get_schema, ServerConfig
from agents4geosx.server import mcp
from agents4geosx.state.documents import DocumentStore
from geos_tui.xml.reader import XMLReader
from geos_tui.xml.writer import XMLWriter
from geos_tui.xml.state import DocumentState, ElementState
from geos_tui.domain.templates import build_template_state
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
        name: Value for the 'name' attribute
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

    attrs = {"name": name, **attributes}
    new_state = ElementState(schema_element=el_schema, attributes=attrs)
    section_state.children.append(new_state)
    doc.is_modified = True

    warnings = []
    for ra in el_schema.attributes:
        if ra.required and ra.name not in attrs and ra.name != "name":
            warnings.append(f"Missing required attribute: {ra.name}")

    return {"element_path": f"{section}/{element_type}[@name='{name}']", "warnings": warnings}


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
        name: Name attribute (empty string if not applicable)
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

    attrs = {"name": name, **attributes} if name else {**attributes}
    child_state = ElementState(schema_element=child_schema, attributes=attrs)
    parent.children.append(child_state)
    doc.is_modified = True
    path = f"{parent_path}/{element_type}" + (f"[@name='{name}']" if name else "")
    return {"element_path": path, "warnings": []}


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
def preview_xml(doc_id: str, section: str | None = None) -> str:
    """Preview XML content of a document without saving.

    Args:
        doc_id: Document ID
        section: Optional section name to preview (e.g., 'Solvers')
    """
    doc = _store.get(doc_id)
    if doc is None:
        return f"Error: Document '{doc_id}' not found"
    writer = XMLWriter()
    root_el = writer._build_element(doc.root)
    if section:
        section_el = root_el.find(section)
        if section_el is not None:
            return etree.tostring(section_el, pretty_print=True, encoding="unicode")
        return f"Section '{section}' not found"
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root_el, pretty_print=True, encoding="unicode")


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
        for child in section.children:
            name = child.attributes.get("name")
            if name:
                named[section_name].add(name)

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
