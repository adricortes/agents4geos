---
name: geos-validate
description: Validate a GEOS XML file — schema validation, cross-reference checks, and physics sanity.
---

Run comprehensive validation on a GEOS XML file.

## Steps
1. `validate_xml(file_path)` — xmllint schema check
2. `load_xml(file_path)` → `validate_cross_references(doc_id)` — name consistency
3. `sanity_check(doc_id)` — physics heuristics (permeability range, pressure, temperature)

Report all findings grouped by severity: errors (schema violations), warnings (broken refs), advisories (sanity).
