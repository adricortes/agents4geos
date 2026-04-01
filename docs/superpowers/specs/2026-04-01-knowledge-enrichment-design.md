# Knowledge Enrichment Design Specification

**Date:** 2026-04-01
**Scope:** New and updated knowledge modules for Agents4GEOSX, plus wiring into existing tools
**Source:** [geos-xml-tools](https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools) (GEOS-DEV/geosPythonPackages)
**Part:** 1 of 2 — knowledge enrichment only. New tools (convert_units, expand_parameters, resolve_includes, format_xml) will be a separate spec.

---

## Purpose

Enrich the Agents4GEOSX knowledge base with preprocessing rules, unit conventions,
and formatting conventions discovered in geos-xml-tools. These are XML conventions
that live outside the XSD schema and are currently invisible to our agents. Landing
this knowledge immediately improves `sanity_check` and `validate_cross_references`
output quality.

---

## Architecture: Layered Approach

Three layers, each building on the previous:

1. **New knowledge modules** — pure data structures, independently testable
2. **Updates to existing modules** — new rules added to existing data structures
3. **Tool wiring** — existing tools read from new/updated knowledge

---

## Layer 1: New Knowledge Modules

All new modules go in `src/agents4geosx/knowledge/`. Each must credit
geos-xml-tools as source in a module-level docstring.

### `unit_conventions.py`

Bridges GEOS bracket notation and pyResToolbox conversion constants.

**`UNIT_DEFINITIONS`** — dict mapping GEOS unit names to SI values and metadata.
Sourced from geos-xml-tools `unit_manager.py`.

```python
# SI base units
"gram":   {"value": 1e-3,  "alt": ["g", "grams"],  "usePrefix": True},
"meter":  {"value": 1.0,   "alt": ["m", "meters"],  "usePrefix": True},
"second": {"value": 1.0,   "alt": ["s", "seconds"], "usePrefix": True},
"minute": {"value": 60.0,  "alt": ["min", "minutes"], "usePrefix": True},
"hour":   {"value": 3600.0, "alt": ["hr", "hours", "hrs"], "usePrefix": True},
"day":    {"value": 86400.0, "alt": ["d", "dy"], "usePrefix": True},
"year":   {"value": 31557600.0, "alt": ["yr", "years"], "usePrefix": True},
"pascal": {"value": 1.0,   "alt": ["Pa"],  "usePrefix": True},
"newton": {"value": 1.0,   "alt": ["N"],   "usePrefix": True},
"joule":  {"value": 1.0,   "alt": ["J"],   "usePrefix": True},
"watt":   {"value": 1.0,   "alt": ["W"],   "usePrefix": True},
# Imperial
"pound":  {"value": 0.453592, "alt": ["lb", "pounds", "lbs"], "usePrefix": True},
"foot":   {"value": 0.3048,   "alt": ["ft", "feet"],  "usePrefix": True},
"inch":   {"value": 0.0254,   "alt": ["in", "inches"], "usePrefix": False},
"mile":   {"value": 1609.34,  "alt": ["mi", "miles"],  "usePrefix": True},
"psi":    {"value": 6894.76,  "alt": [],  "usePrefix": True},
"gallon": {"value": 0.00378541, "alt": ["gal", "gallons"], "usePrefix": True},
"barrel": {"value": 0.1589873, "alt": ["bbl", "barrels"], "usePrefix": True},
# Other
"bar":        {"value": 1.0e5,    "alt": ["bars"],  "usePrefix": True},
"atmosphere": {"value": 101325.0, "alt": ["atm"],   "usePrefix": True},
"poise":      {"value": 0.1,      "alt": ["P"],     "usePrefix": True},
"dyne":       {"value": 1.0e-5,   "alt": ["dynes"], "usePrefix": True},
# ... (complete list from geos-xml-tools)
```

**`SI_PREFIXES`** — dict mapping prefix names to scale factors.

```python
"giga":  {"value": 1e9,  "alt": "G"},
"mega":  {"value": 1e6,  "alt": "M"},
"kilo":  {"value": 1e3,  "alt": "k"},
"hecto": {"value": 1e2,  "alt": "H"},
"deca":  {"value": 1e1,  "alt": "D"},
"":      {"value": 1.0,  "alt": ""},
"deci":  {"value": 1e-1, "alt": "d"},
"centi": {"value": 1e-2, "alt": "c"},
"milli": {"value": 1e-3, "alt": "m"},
"micro": {"value": 1e-6, "alt": "mu"},
"nano":  {"value": 1e-9, "alt": "n"},
```

**`PYRESTOOLBOX_MAPPING`** — dict bridging GEOS unit names to pyResToolbox constants.

```python
# Maps GEOS bracket notation units → pyResToolbox constant names
"mD":  "MD_TO_M2",      # 9.869233e-16
"psi": "PSI_TO_PA",     # 6894.757
"bbl": "BBL_TO_M3",     # 0.1589873
"ft":  "FT_TO_M",       # 0.3048
"cP":  "CP_TO_PAS",     # 0.001
# ... (all mappings from pyResToolbox constants.py)
```

**`BRACKET_NOTATION_REGEX`** — pattern for matching unit expressions.

```python
r"([0-9]*?\.?[0-9]+(?:[eE][-+]?[0-9]*?)?)\ *?\[([-+.*/()a-zA-Z0-9]*)\]"
# Group 1: numeric value (e.g., "9.81")
# Group 2: unit expression (e.g., "m**2/s")
```

**`validate_unit_expression(expr: str) -> dict`** — checks if a bracket expression
uses only valid unit names/prefixes. Returns `{valid, units_found, unknown}`.

### `preprocessing_rules.py`

Encodes the full XML preprocessing pipeline from geos-xml-tools.

**`PROCESSING_PIPELINE`** — ordered list defining the strict evaluation sequence:

```python
[
    {"stage": 1, "name": "include_merging",
     "description": "Merge <Included> file blocks into main document",
     "nesting_limit": 100},
    {"stage": 2, "name": "parameter_substitution",
     "description": "Expand $Name$ patterns from <Parameters> section",
     "nesting_limit": 100},
    {"stage": 3, "name": "unit_conversion",
     "description": "Evaluate [unit] bracket notation to SI values",
     "nesting_limit": None},
    {"stage": 4, "name": "symbolic_math",
     "description": "Evaluate `expression` backtick notation",
     "nesting_limit": 100},
    {"stage": 5, "name": "special_char_validation",
     "description": "Flag leftover $, [, ], ` as unresolved",
     "nesting_limit": None},
]
```

Order matters: parameters can appear inside unit expressions, so params expand
before units. Units can appear inside symbolic expressions, so units convert
before symbolic math.

**`PARAMETER_RULES`** — parameter substitution conventions:

```python
{
    "regex": r"\$:?([a-zA-Z_0-9]*)\$?",
    "valid_name_chars": "[a-zA-Z_0-9]",
    "colon_prefix_optional": True,
    "trailing_dollar_optional": True,
    "max_nesting": 100,
    "source_element": "Parameters/Parameter",
    "source_attrs": {"name": "parameter name", "value": "parameter value"},
    "cli_override": True,
}
```

**`SYMBOLIC_MATH_RULES`** — backtick expression syntax:

```python
{
    "regex": r"\`([-+.*/() 0-9eE]*)\`",
    "allowed_chars": "+-.*/()" + "0-9" + "eE",
    "max_nesting": 100,
    "protected_elements": [
        {"element": "SymbolicFunction", "attribute": "expression"},
        {"element": "CompositeFunction", "attribute": "expression"},
    ],
}
```

**`INCLUDE_RULES`** — `<Included>` merging behavior:

```python
{
    "max_depth": 100,
    "merge_strategy": "attributes overridden, named elements matched by name attr",
    "insert_only_elements": ["Nodeset"],  # Never merged by name
    "root_element": "Problem",  # Unnamed, merged at level 0
    "source_structure": "Included/File[@name]",
}
```

**`SPECIAL_CHARACTERS`** — characters that must be consumed after processing:

```python
["$", "[", "]", "`"]
```

### `formatting_conventions.py`

Encodes XML output style rules from geos-xml-tools.

**`DEFAULT_FORMAT`** — standard formatting options:

```python
{
    "indent": 2,                        # spaces
    "style": "fixed",                   # not hanging
    "block_separation_max_depth": 2,    # blank lines between children
    "sort_attributes": False,
    "close_tag_newline": False,         # inline /> for self-closing
}
```

**`ATTRIBUTE_FORMATTING`** — attribute value normalization regexes:

```python
{
    "comma_spacing":    {"pattern": r",\s*",  "replacement": ", "},
    "brace_opening":    {"pattern": r"{\s*",  "replacement": "{ "},
    "brace_closing":    {"pattern": r"\s*}",  "replacement": " }"},
    "whitespace_consolidation": {"pattern": r"\s+", "replacement": " "},
    "array_split_pattern": r"\s*{\s*({[-+.,0-9a-zA-Z\s]*},?\s*)*\s*}",
}
```

**`PROTECTED_EXPRESSIONS`** — element/attribute combos never reformatted:

```python
[
    {"element": "SymbolicFunction", "attribute": "expression"},
    {"element": "CompositeFunction", "attribute": "expression"},
]
```

---

## Layer 2: Updates to Existing Modules

### `sanity_rules.py`

Add three new rule categories to `SANITY_RULES`:

- **InputFlags enforcement** — REQUIRED attributes must be present. Check against
  schema's required attribute list.
- **Redundancy detection** (advisory) — attributes whose values match schema defaults
  are redundant. Flag as advisory, not error.
- **Zero-children pruning** (advisory) — elements with no required children and no
  actual children may be unnecessary.

### `cross_refs.py`

Add `NESTING_CONSTRAINTS` dict alongside existing `ATTRIBUTE_REFERENCES`:

```python
NESTING_CONSTRAINTS = {
    # Element types that cannot nest within themselves
    "self_nesting_prohibited": ["PeriodicEvent", ...],
    # Additional parent-child restrictions from geos-xml-tools analysis
}
```

Also add function `check_nesting(parent_type, child_type) -> dict` returning
`{valid, reason}`.

### `lessons_learned.md`

Add entry:

> **Schema validation is necessary but not sufficient.** The XSD is auto-generated
> from C++ source code and validates structure, but cannot catch physics errors,
> cross-reference inconsistencies, or preprocessing issues. Always use schema
> validation (xmllint) AND sanity checks AND cross-reference validation together.

---

## Layer 3: Tool Wiring

### `sanity_check` (in `postproc_tools.py`)

Currently reads `SANITY_RULES` and `COUPLED_SOLID_TYPES` from `sanity_rules.py`.
Add reads from:

- `sanity_rules.py` new rules → check InputFlags, flag redundancy, flag empty elements
- `unit_conventions.py` → validate bracket notation in attribute values
- `preprocessing_rules.py` → flag leftover special characters (`$`, `[`, `]`, `` ` ``)

### `validate_cross_references` (in `xml_tools.py`)

Currently reads `ATTRIBUTE_REFERENCES` from `cross_refs.py`. Add:

- `NESTING_CONSTRAINTS` → check no element violates nesting rules

---

## Non-goals

- No new MCP tools in this spec (convert_units, expand_parameters, etc. are Part 2)
- No changes to skill files — existing agents automatically benefit from smarter tools
- No changes to AGENTS.md — tool capabilities expand but no new agents

---

## Attribution

All new knowledge modules must include a docstring crediting geos-xml-tools:

```python
"""<Module description>.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools

pyResToolbox unit mappings from the SI-refactored fork.
"""
```

---

## Success Criteria

- All new knowledge modules have full test coverage
- `sanity_check` catches unit expression errors, leftover special characters,
  missing required attributes, and redundant defaults
- `validate_cross_references` catches nesting constraint violations
- Existing tests continue to pass (no regressions)
- All data structures match geos-xml-tools source (verified by comparison)
