---
name: geos:edit
description: Edit an existing GEOS XML file — load, modify elements, validate, and save.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools. NEVER edit XML files directly with Edit/Write tools.

## Workflow

1. `load_xml(file_path)` — load and parse the file
2. `preview_xml(doc_id)` — ALWAYS preview first to understand current structure
3. Apply changes using the appropriate tool:
   - `update_element(doc_id, path, attributes)` — modify existing element attributes
   - `add_element(doc_id, section, type, name, attrs)` — add NEW elements only
   - `add_child(doc_id, parent_path, type, name, attrs)` — add nested child elements
   - `remove_element(doc_id, path)` — remove elements (check dangling_references in response)
4. `validate_cross_references(doc_id)` — ALWAYS check after changes
5. `sanity_check(doc_id)` — ALWAYS run physics checks
6. `preview_xml(doc_id)` — show user what changed
7. `save_xml(doc_id, path)` — write and auto-validate with xmllint

## Viewing XML
`preview_xml` writes to a file and returns `{"path": "/tmp/geos_preview.xml", "lines": N}`.
`Read` the returned path to load the XML, then output it to the user in a ```xml code block.

## Rules
- ALWAYS preview before AND after changes
- Element paths use format: `Section/ElementType[@name='value']`
- If removing an element, check the `dangling_references` in the response and fix them
- `diff_xml(path_a, path_b)` can compare original vs modified file after saving
- SourceFlux has NO fieldName — only name, objectPath, scale, setNames, optional component
- permeabilityComponents must be { x, y, z } triplet
