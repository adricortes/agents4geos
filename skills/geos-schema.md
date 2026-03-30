---
name: geos-schema
description: Query the GEOS XSD schema — available elements, attributes, types, cross-references.
---

Answer schema questions using ONLY the `agents4geosx` MCP tools below. Do NOT use Bash, grep,
or read the XSD file directly. The MCP tools parse the schema correctly and apply v1 scope filtering.

## MANDATORY: Use these MCP tools (server: agents4geosx)

For "what solvers/elements are available?":
→ Call `list_elements` with section="Solvers" (or "Constitutive", "Mesh", etc.) and scope="v1"

For "describe element X" or "what attributes does X have?":
→ Call `describe_element` with element_name="X"

For "what attributes are essential for X?":
→ Call `list_attributes` with element_name="X" and group="essential"

For "what type is X?" or "what values can X take?":
→ Call `get_type_info` with type_name="X"

For "what field names can I use with solver X?":
→ Call `lookup_field_names` with solver_type="X"

For "what does element X reference?":
→ Call `get_cross_references` with element_name="X"

For "what sections exist?":
→ Call `list_sections`

## Rules
- NEVER parse the XSD file with grep/python/bash — use the MCP tools
- ALWAYS use scope="v1" unless the user explicitly asks for all solvers
- Present results in a clean table or grouped list
