# Preprocessing Tools Design Specification (Part 2)

**Date:** 2026-04-15
**Scope:** 4 new MCP tools in a new `preproc_tools.py` module
**Depends on:** Knowledge enrichment (Part 1) — `unit_conventions.py`, `preprocessing_rules.py`, `formatting_conventions.py`

---

## Purpose

Add 4 new MCP tools that use the knowledge modules from Part 1 to give agents
active preprocessing capabilities: unit conversion, parameter expansion, include
resolution, and XML formatting.

---

## New File: `src/agents4geosx/tools/preproc_tools.py`

### Tool 1: `convert_units(expression: str) -> dict`

Takes a single bracket notation string, returns the SI value.

**Input:** `"9.81[m/s**2]"`, `"100[mD]"`, or plain text without brackets.

**Output:**
```python
{
    "original": "9.81[m/s**2]",
    "numeric_value": 9.81,       # value before unit conversion
    "unit_expression": "m/s**2", # unit part from brackets
    "si_value": 9.81,            # converted SI value
    "units_found": ["m", "s"],   # unit names parsed
    "valid": True,
}
```

If no bracket notation found:
```python
{"original": "plain text", "si_value": None, "valid": True, "message": "No bracket notation found"}
```

If invalid units:
```python
{"original": "1.0[foobar]", "si_value": None, "valid": False, "unknown_units": ["foobar"]}
```

**Knowledge used:** `UNIT_DEFINITIONS`, `SI_PREFIXES`, `BRACKET_NOTATION_REGEX` from `unit_conventions.py`.

**Conversion logic:** Extract numeric value and unit expression via regex. Replace each
unit name in the expression with its SI scale factor from `UNIT_DEFINITIONS` (applying
`SI_PREFIXES` for prefixed units). Evaluate the resulting arithmetic expression to get
the SI scale factor. Multiply numeric value by scale factor.

### Tool 2: `expand_parameters(doc_id: str) -> dict`

Expands all `$Name$` patterns in a loaded document's attributes using values from
the `<Parameters>` section.

**Input:** Document ID from `create_document` or `load_xml`.

**Output:**
```python
{
    "parameters_found": {"injRate": "1e-4", "permX": "1e-13"},
    "substitutions_made": 5,
    "unresolved": [],
    "details": [
        {"path": "Solvers/.../@scale", "before": "$injRate$", "after": "1e-4"},
    ],
}
```

**Knowledge used:** `PARAMETER_RULES` from `preprocessing_rules.py`.

**Logic:**
1. Scan document for `<Parameters>` section, build name→value map
2. Walk all elements, for each attribute value containing `$`:
   - Apply regex substitution using the parameter map
   - Iterate up to `max_nesting` (100) for nested parameters
3. Collect unresolved parameters (names not in the map)
4. Update attribute values in-place in the document

### Tool 3: `resolve_includes(doc_id: str) -> dict`

Merges `<Included>` file blocks into the loaded document. Replaces the `<Included>`
block with an XML comment listing merged files (provenance).

**Input:** Document ID.

**Output:**
```python
{
    "files_merged": ["path/to/mesh.xml", "path/to/constitutive.xml"],
    "elements_added": 12,
    "comment": "<!-- Included files merged: mesh.xml, constitutive.xml -->",
}
```

**Knowledge used:** `INCLUDE_RULES` from `preprocessing_rules.py`.

**Merge strategy** (from geos-xml-tools):
- Attributes are overridden (newer values win)
- Named elements matched by `name` attribute
- `Nodeset` elements always inserted (never merged by name)
- Root `Problem` node is unnamed, merged at level 0
- Max recursion depth: 100
- After merging, replace `<Included>` block with an XML comment

### Tool 4: `format_xml(input_path: str, output_path: str = "") -> dict`

Reformats an XML file to match geos-xml-tools canonical style.

**Input:** File path. If `output_path` is empty, overwrites input file.

**Output:**
```python
{
    "input": "/path/to/sim.xml",
    "output": "/path/to/sim_formatted.xml",
    "format_applied": {"indent": 2, "style": "fixed", ...},
    "protected_expressions_preserved": 0,
}
```

**Knowledge used:** `DEFAULT_FORMAT`, `ATTRIBUTE_FORMATTING`, `PROTECTED_EXPRESSIONS`
from `formatting_conventions.py`.

**Formatting rules:**
- 2-space indentation (fixed style)
- Attribute value normalization: comma spacing (`", "`), brace spacing (`"{ "` / `" }"`), whitespace consolidation
- Blank lines between children up to `block_separation_max_depth` (2)
- Self-closing tags use inline `/>` (no newline)
- `SymbolicFunction`/`CompositeFunction` `expression` attributes are NEVER reformatted

---

## Server Registration

Add to `server.py`'s `register_all_tools`:
```python
import agents4geosx.tools.preproc_tools  # noqa: F401
```

---

## AGENTS.md Update

Add 4 tools to Section 4 (Tool Inventory) under a new "Preprocessing" group.
Update tool count (48 → 52). Update README.md tool count to match.

---

## Which agents benefit

| Tool | Used by agents |
|------|---------------|
| `convert_units` | fluids, geos, edit |
| `expand_parameters` | edit, inspect, geos |
| `resolve_includes` | edit, inspect, validate |
| `format_xml` | edit, geos |

---

## Non-goals

- No changes to skill files (agents discover tools via MCP schema)
- No new knowledge modules (Part 1 already delivered them)
- `convert_units` operates on single expressions, not document-wide (YAGNI)

---

## Success Criteria

- All 4 tools are callable via MCP and return correct results
- `convert_units` handles SI base, imperial, prefixed, and compound unit expressions
- `expand_parameters` resolves nested parameters up to 100 levels
- `resolve_includes` merges files and leaves a provenance comment
- `format_xml` produces output matching geos-xml-tools canonical style
- All existing tests continue to pass
- New tests cover each tool with happy path and error cases
