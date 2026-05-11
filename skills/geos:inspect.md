---
name: geos:inspect
description: Describe what a GEOS XML file contains — solvers, mesh, materials, BCs.
---

CRITICAL: Use ONLY the `agents4geos` MCP tools.

## Workflow

1. `load_xml(file_path)` — parse the file, get doc_id and section list
2. For each section, call `preview_xml(doc_id, section)` to show contents
3. Use `describe_element(element_name)` to explain what specific elements do
4. Summarize in a table: section → elements → key attributes

## Report Format
Present a structured summary:
- **Solver**: type, discretization, target regions
- **Mesh**: dimensions, cell count, element type
- **Constitutive**: fluid model, coupled solid, relperm (if any)
- **BCs/ICs**: what conditions are applied where
- **Events**: simulation time, timestep, output frequency
- **Outputs**: format, what fields are written
