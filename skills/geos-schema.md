---
name: geos-schema
description: Query the GEOS XSD schema — available elements, attributes, types, cross-references.
---

Schema introspection tools for understanding GEOS input structure.

## Tools
- `list_sections()` — top-level sections (Solvers, Mesh, etc.)
- `list_elements(section, scope)` — elements in a section (v1 or all)
- `describe_element(element_name)` — full details: attributes, children, description
- `list_attributes(element_name, group)` — filtered by essential/physics/advanced
- `get_type_info(type_name)` — type constraints, patterns, enums
- `lookup_field_names(solver_type)` — valid BC/IC field names per solver
- `get_cross_references(element_name)` — what this element references
