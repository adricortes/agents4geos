"""Schema & introspection MCP tools (Group 1)."""

from __future__ import annotations

from agents4geos.config import get_schema
from agents4geos.server import mcp
from agents4geos.geos.domain.scope import filter_elements_for_section
from agents4geos.geos.domain.descriptions import get_description
from agents4geos.geos.domain.curation import get_field_groups
from agents4geos.knowledge.field_names import get_field_names
from agents4geos.knowledge import cross_refs as xref_module


@mcp.tool
def list_sections() -> list[str]:
    """List all top-level XML sections available in the GEOS schema."""
    schema = get_schema()
    if schema.root is None:
        return []
    return [child.name for child in schema.root.children]


@mcp.tool
def list_elements(section: str, scope: str = "v1") -> list[dict]:
    """List elements available in a section. Use scope='v1' for supported only, 'all' for everything."""
    schema = get_schema()
    if schema.root is None:
        return []
    section_el = next((c for c in schema.root.children if c.name == section), None)
    if section_el is None:
        return []
    elements = section_el.children
    if scope == "v1":
        elements = filter_elements_for_section(section, elements)
    return [
        {"name": el.name, "description": get_description(el.name, None, el.description)}
        for el in elements
    ]


@mcp.tool
def describe_element(element_name: str) -> dict:
    """Get full details for a GEOS element: description, attributes, children."""
    schema = get_schema()
    el = schema.elements.get(element_name)
    if el is None:
        return {"error": f"Element '{element_name}' not found in schema"}
    return {
        "name": el.name,
        "type_name": el.type_name,
        "description": get_description(el.name, None, el.description),
        "attributes": [
            {
                "name": a.name,
                "type": a.type_name,
                "required": a.required,
                "default": a.default,
                "description": get_description(el.name, a.name, a.description),
            }
            for a in el.attributes
        ],
        "children": [c.name for c in el.children],
    }


@mcp.tool
def list_attributes(element_name: str, group: str = "all") -> list[dict]:
    """List attributes for an element, optionally filtered by group."""
    schema = get_schema()
    el = schema.elements.get(element_name)
    if el is None:
        return []
    if group == "all":
        attrs = el.attributes
    else:
        groups = get_field_groups(el.type_name)
        target_group = next((g for g in groups if g.label.lower() == group.lower()), None)
        if target_group is None:
            attrs = el.attributes
        else:
            name_set = set(target_group.field_names)
            attrs = [a for a in el.attributes if a.name in name_set]
    return [
        {
            "name": a.name,
            "type": a.type_name,
            "required": a.required,
            "default": a.default,
            "description": get_description(el.name, a.name, a.description),
        }
        for a in attrs
    ]


@mcp.tool
def get_type_info(type_name: str) -> dict:
    """Get details about a schema type: base type, pattern, enum values."""
    schema = get_schema()
    t = schema.types.get(type_name)
    if t is None:
        return {"error": f"Type '{type_name}' not found"}
    return {
        "name": t.name,
        "base": t.base,
        "pattern": t.pattern,
        "enumeration": t.enumeration,
        "has_expression_passthrough": t.has_expression_passthrough,
    }


@mcp.tool
def lookup_field_names(solver_type: str) -> list[str]:
    """Get valid FieldSpecification field names for a solver type."""
    return get_field_names(solver_type)


@mcp.tool
def get_cross_references(element_name: str) -> list[dict]:
    """Get cross-references for an element — what other sections its attributes point to."""
    schema = get_schema()
    el = schema.elements.get(element_name)
    if el is None:
        return []
    return xref_module.get_cross_references(el.name, el.attributes)
