---
name: geos-edit
description: Edit an existing GEOS XML file — load, modify elements, validate, and save.
---

Load an existing XML, apply requested changes, validate, and save.

## Tools
- `load_xml(file_path)` — load and parse
- `update_element(doc_id, path, attributes)` — modify attributes
- `add_element(doc_id, section, type, name, attrs)` — add new elements
- `remove_element(doc_id, path)` — remove elements (reports dangling refs)
- `validate_cross_references(doc_id)` — check consistency after changes
- `sanity_check(doc_id)` — physics heuristics
- `save_xml(doc_id, path)` — write and auto-validate
- `diff_xml(path_a, path_b)` — compare before/after
