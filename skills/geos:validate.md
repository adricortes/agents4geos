---
name: geos:validate
description: Validate a GEOS XML file — schema validation, cross-reference checks, and physics sanity.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools. NEVER run xmllint manually via Bash.

## Validation Steps (run ALL three)

1. `validate_xml(file_path)` — xmllint schema check (structural validity)
2. `load_xml(file_path)` → `validate_cross_references(doc_id)` — name consistency
   - Checks: discretization → NumericalMethods, targetRegions → ElementRegions,
     materialList → Constitutive, setNames → Geometry, solidModelName/porosityModelName/permeabilityModelName → Constitutive
3. `sanity_check(doc_id)` — physics heuristics + structural checks
   - Permeability range (1e-20 to 1e-8 m²)
   - Porosity range (0.001 to 0.5)
   - Pressure positive
   - Temperature range (273-573 K)
   - Composition fractions sum to ~1.0 (compositional flows)
   - materialList has at least fluid + coupled solid

## Report Format
Group findings by severity:
- **Errors** (schema violations) — must fix before GEOS will load the file
- **Warnings** (broken cross-refs) — will cause GEOS runtime crash
- **Advisories** (sanity) — simulation may produce unphysical results
