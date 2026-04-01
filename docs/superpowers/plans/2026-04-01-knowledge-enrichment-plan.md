# Knowledge Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the Agents4GEOSX knowledge base with unit conventions, preprocessing rules, and formatting conventions from geos-xml-tools, then wire them into existing tools.

**Architecture:** Three layers — new knowledge modules (pure data), updates to existing modules (new rules), and tool wiring (existing tools read new knowledge). Each layer builds on the previous.

**Tech Stack:** Python 3.11+, pytest, regex, pyResToolbox constants

**User Verification:** NO — no user verification required.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/agents4geosx/knowledge/unit_conventions.py` | GEOS unit definitions, SI prefixes, pyResToolbox bridge, bracket notation validation |
| Create | `src/agents4geosx/knowledge/preprocessing_rules.py` | XML preprocessing pipeline, parameter/symbolic/include rules |
| Create | `src/agents4geosx/knowledge/formatting_conventions.py` | XML output formatting rules |
| Create | `tests/test_unit_conventions.py` | Tests for unit conventions |
| Create | `tests/test_preprocessing_rules.py` | Tests for preprocessing rules |
| Create | `tests/test_formatting_conventions.py` | Tests for formatting conventions |
| Modify | `src/agents4geosx/knowledge/sanity_rules.py` | Add InputFlags, redundancy, zero-children rules |
| Modify | `src/agents4geosx/knowledge/cross_refs.py` | Add NESTING_CONSTRAINTS + check_nesting |
| Modify | `knowledge/lessons_learned.md` | Add schema validation lesson |
| Modify | `src/agents4geosx/tools/postproc_tools.py` | Wire unit validation + special char detection into sanity_check |
| Modify | `src/agents4geosx/tools/xml_tools.py` | Wire nesting constraints into validate_cross_references |
| Modify | `tests/test_postproc_tools.py` | Tests for wired-in sanity checks |
| Modify | `tests/test_xml_tools.py` | Tests for wired-in nesting validation |

---

### Task 1: Create unit_conventions.py knowledge module

**Goal:** Create the unit conventions module bridging GEOS bracket notation and pyResToolbox.

**Files:**
- Create: `src/agents4geosx/knowledge/unit_conventions.py`
- Create: `tests/test_unit_conventions.py`

**Acceptance Criteria:**
- [ ] UNIT_DEFINITIONS covers all SI base, imperial, and other units from geos-xml-tools
- [ ] SI_PREFIXES covers giga through nano
- [ ] PYRESTOOLBOX_MAPPING bridges GEOS unit names to pyResToolbox constants
- [ ] BRACKET_NOTATION_REGEX matches valid unit expressions
- [ ] validate_unit_expression returns {valid, units_found, unknown}
- [ ] geos-xml-tools credited in docstring
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_unit_conventions.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

```python
# tests/test_unit_conventions.py
"""Tests for unit conventions knowledge module."""
import re
import pytest
from agents4geosx.knowledge.unit_conventions import (
    UNIT_DEFINITIONS,
    SI_PREFIXES,
    PYRESTOOLBOX_MAPPING,
    BRACKET_NOTATION_REGEX,
    validate_unit_expression,
)


class TestUnitDefinitions:
    def test_si_base_units_present(self):
        for unit in ["gram", "meter", "second", "pascal", "newton", "joule", "watt"]:
            assert unit in UNIT_DEFINITIONS, f"Missing SI base unit: {unit}"

    def test_imperial_units_present(self):
        for unit in ["pound", "foot", "psi", "barrel", "gallon"]:
            assert unit in UNIT_DEFINITIONS, f"Missing imperial unit: {unit}"

    def test_other_units_present(self):
        for unit in ["bar", "atmosphere", "poise", "dyne"]:
            assert unit in UNIT_DEFINITIONS, f"Missing other unit: {unit}"

    def test_unit_structure(self):
        for name, defn in UNIT_DEFINITIONS.items():
            assert "value" in defn, f"{name} missing 'value'"
            assert "alt" in defn, f"{name} missing 'alt'"
            assert "usePrefix" in defn, f"{name} missing 'usePrefix'"
            assert isinstance(defn["value"], (int, float)), f"{name} value not numeric"
            assert isinstance(defn["alt"], list), f"{name} alt not list"
            assert isinstance(defn["usePrefix"], bool), f"{name} usePrefix not bool"

    def test_meter_value_is_one(self):
        assert UNIT_DEFINITIONS["meter"]["value"] == 1.0

    def test_gram_value_is_1e_minus_3(self):
        assert UNIT_DEFINITIONS["gram"]["value"] == 1e-3

    def test_inch_no_prefix(self):
        assert UNIT_DEFINITIONS["inch"]["usePrefix"] is False


class TestSIPrefixes:
    def test_all_prefixes_present(self):
        expected = ["giga", "mega", "kilo", "hecto", "deca", "",
                    "deci", "centi", "milli", "micro", "nano"]
        for prefix in expected:
            assert prefix in SI_PREFIXES, f"Missing prefix: {prefix!r}"

    def test_kilo_value(self):
        assert SI_PREFIXES["kilo"]["value"] == 1e3

    def test_milli_value(self):
        assert SI_PREFIXES["milli"]["value"] == 1e-3

    def test_prefix_structure(self):
        for name, defn in SI_PREFIXES.items():
            assert "value" in defn
            assert "alt" in defn


class TestPyResToolboxMapping:
    def test_common_mappings_present(self):
        for unit in ["mD", "psi", "bbl", "ft", "cP"]:
            assert unit in PYRESTOOLBOX_MAPPING, f"Missing mapping: {unit}"

    def test_mapping_values_are_strings(self):
        for unit, const in PYRESTOOLBOX_MAPPING.items():
            assert isinstance(const, str), f"{unit} mapping not string"


class TestBracketNotationRegex:
    def test_matches_simple(self):
        m = re.search(BRACKET_NOTATION_REGEX, "9.81[m/s**2]")
        assert m is not None
        assert m.group(1) == "9.81"
        assert m.group(2) == "m/s**2"

    def test_matches_scientific_notation(self):
        m = re.search(BRACKET_NOTATION_REGEX, "3.14e-2[Pa]")
        assert m is not None
        assert m.group(1) == "3.14e-2"

    def test_matches_with_space(self):
        m = re.search(BRACKET_NOTATION_REGEX, "1.0 [bbl/day]")
        assert m is not None

    def test_no_match_without_brackets(self):
        m = re.search(BRACKET_NOTATION_REGEX, "9.81")
        assert m is None


class TestValidateUnitExpression:
    def test_valid_simple(self):
        result = validate_unit_expression("9.81[m/s**2]")
        assert result["valid"] is True
        assert len(result["unknown"]) == 0

    def test_valid_with_prefix(self):
        result = validate_unit_expression("3.0[km]")
        assert result["valid"] is True

    def test_invalid_unit(self):
        result = validate_unit_expression("1.0[foobar]")
        assert result["valid"] is False
        assert "foobar" in result["unknown"]

    def test_no_brackets_returns_valid(self):
        result = validate_unit_expression("9.81")
        assert result["valid"] is True
        assert result["units_found"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_unit_conventions.py -v`
Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Write implementation**

```python
# src/agents4geosx/knowledge/unit_conventions.py
"""GEOS unit system conventions and pyResToolbox conversion bridge.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools

pyResToolbox unit mappings from the SI-refactored fork.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# SI prefixes (geos-xml-tools unit_manager.py)
# ---------------------------------------------------------------------------
SI_PREFIXES: dict[str, dict] = {
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
}

# ---------------------------------------------------------------------------
# Unit definitions (geos-xml-tools unit_manager.py)
# All values are SI scale factors (multiply value in unit to get SI base)
# ---------------------------------------------------------------------------
UNIT_DEFINITIONS: dict[str, dict] = {
    # SI base
    "gram":    {"value": 1e-3,               "alt": ["g", "grams"],          "usePrefix": True},
    "meter":   {"value": 1.0,                "alt": ["m", "meters"],         "usePrefix": True},
    "second":  {"value": 1.0,                "alt": ["s", "seconds"],        "usePrefix": True},
    "minute":  {"value": 60.0,               "alt": ["min", "minutes"],      "usePrefix": True},
    "hour":    {"value": 3600.0,             "alt": ["hr", "hours", "hrs"],  "usePrefix": True},
    "day":     {"value": 86400.0,            "alt": ["d", "dy"],             "usePrefix": True},
    "year":    {"value": 31557600.0,         "alt": ["yr", "years"],         "usePrefix": True},
    "pascal":  {"value": 1.0,                "alt": ["Pa"],                  "usePrefix": True},
    "newton":  {"value": 1.0,                "alt": ["N"],                   "usePrefix": True},
    "joule":   {"value": 1.0,                "alt": ["J"],                   "usePrefix": True},
    "watt":    {"value": 1.0,                "alt": ["W"],                   "usePrefix": True},
    # Imperial
    "pound":      {"value": 0.453592,           "alt": ["lb", "pounds", "lbs"],  "usePrefix": True},
    "poundforce": {"value": 0.453592 * 9.81,    "alt": ["lbf"],                  "usePrefix": True},
    "stone":      {"value": 6.35029,            "alt": ["st"],                   "usePrefix": True},
    "ton":        {"value": 907.185,            "alt": ["tons"],                 "usePrefix": True},
    "inch":       {"value": 0.0254,             "alt": ["in", "inches"],         "usePrefix": False},
    "foot":       {"value": 0.3048,             "alt": ["ft", "feet"],           "usePrefix": True},
    "yard":       {"value": 0.9144,             "alt": ["yd", "yards"],          "usePrefix": True},
    "rod":        {"value": 5.0292,             "alt": ["rd", "rods"],           "usePrefix": True},
    "mile":       {"value": 1609.34,            "alt": ["mi", "miles"],          "usePrefix": True},
    "acre":       {"value": 4046.86,            "alt": ["acres"],                "usePrefix": True},
    "gallon":     {"value": 0.00378541,         "alt": ["gal", "gallons"],       "usePrefix": True},
    "psi":        {"value": 6894.76,            "alt": [],                       "usePrefix": True},
    "psf":        {"value": 1853.184,           "alt": [],                       "usePrefix": True},
    # Other
    "dyne":       {"value": 1.0e-5,             "alt": ["dynes"],                "usePrefix": True},
    "bar":        {"value": 1.0e5,              "alt": ["bars"],                 "usePrefix": True},
    "atmosphere": {"value": 101325.0,           "alt": ["atm", "atmospheres"],   "usePrefix": True},
    "poise":      {"value": 0.1,                "alt": ["P"],                    "usePrefix": True},
    "barrel":     {"value": 0.1589873,          "alt": ["bbl", "barrels"],       "usePrefix": True},
    "horsepower": {"value": 745.7,              "alt": ["hp", "horsepowers"],    "usePrefix": True},
}

# ---------------------------------------------------------------------------
# Bracket notation regex (geos-xml-tools regex_tools.py)
# Matches: 9.81[m/s**2], 3.14e-2[Pa], 1.0 [bbl/day]
# Group 1: numeric value, Group 2: unit expression
# ---------------------------------------------------------------------------
BRACKET_NOTATION_REGEX = r"([0-9]*?\.?[0-9]+(?:[eE][-+]?[0-9]*?)?)\ *?\[([-+.*/()a-zA-Z0-9]*)\]"

# Regex for extracting individual unit names from a unit expression
_UNIT_NAME_REGEX = r"[a-zA-Z]+"

# ---------------------------------------------------------------------------
# pyResToolbox conversion constant mapping
# Maps GEOS bracket notation unit aliases → pyResToolbox constant names
# from pyrestoolbox.constants.constants
# ---------------------------------------------------------------------------
PYRESTOOLBOX_MAPPING: dict[str, str] = {
    # Permeability
    "mD": "MD_TO_M2",              # 9.869233e-16
    # Pressure
    "psi": "PSI_TO_PA",            # 6894.757
    "bar": "BAR_TO_PA",            # 1e5
    "atm": "ATM_TO_PA",            # 101325
    # Length
    "ft": "FT_TO_M",              # 0.3048
    "in": "IN_TO_M",              # 0.0254
    # Volume
    "bbl": "BBL_TO_M3",           # 0.1589873
    "gal": "GAL_TO_M3",           # 0.00378541
    # Viscosity
    "cP": "CP_TO_PAS",            # 0.001
    # Density
    "lb/ft**3": "LBCUFT_TO_KGM3",  # 16.01846
    # Temperature (functions, not constants)
    "degF": "degf_to_degc",        # function
    "degC": "degc_to_kelvin",      # function
}


def _build_valid_unit_names() -> set[str]:
    """Build the complete set of valid unit names (full names + aliases + prefixed)."""
    names: set[str] = set()
    for name, defn in UNIT_DEFINITIONS.items():
        names.add(name)
        names.update(defn["alt"])
        if defn["usePrefix"]:
            for prefix_name, prefix_def in SI_PREFIXES.items():
                if prefix_name:  # skip empty prefix
                    names.add(prefix_name + name)
                    names.add(prefix_def["alt"] + name)
                    for alt in defn["alt"]:
                        names.add(prefix_name + alt)
                        names.add(prefix_def["alt"] + alt)
    return names


_VALID_UNIT_NAMES = _build_valid_unit_names()


def validate_unit_expression(expr: str) -> dict:
    """Validate that a string's bracket unit expressions use valid GEOS units.

    Args:
        expr: Attribute value string, possibly containing bracket notation.

    Returns:
        {"valid": bool, "units_found": list[str], "unknown": list[str]}
    """
    match = re.search(BRACKET_NOTATION_REGEX, expr)
    if match is None:
        return {"valid": True, "units_found": [], "unknown": []}

    unit_expr = match.group(2)
    unit_names = re.findall(_UNIT_NAME_REGEX, unit_expr)
    unknown = [u for u in unit_names if u not in _VALID_UNIT_NAMES]
    return {
        "valid": len(unknown) == 0,
        "units_found": unit_names,
        "unknown": unknown,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_unit_conventions.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/knowledge/unit_conventions.py tests/test_unit_conventions.py
git commit -m "feat: add unit_conventions.py knowledge module

GEOS unit definitions, SI prefixes, pyResToolbox bridge, and bracket
notation validation. Sourced from geos-xml-tools."
```

---

### Task 2: Create preprocessing_rules.py knowledge module

**Goal:** Create the preprocessing rules module encoding the full XML processing pipeline.

**Files:**
- Create: `src/agents4geosx/knowledge/preprocessing_rules.py`
- Create: `tests/test_preprocessing_rules.py`

**Acceptance Criteria:**
- [ ] PROCESSING_PIPELINE has 5 ordered stages
- [ ] PARAMETER_RULES has regex, naming conventions, nesting limit
- [ ] SYMBOLIC_MATH_RULES has regex, allowed chars, protected elements
- [ ] INCLUDE_RULES has max depth, merge strategy, insert-only elements
- [ ] SPECIAL_CHARACTERS lists all 4 characters
- [ ] geos-xml-tools credited in docstring
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_preprocessing_rules.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

```python
# tests/test_preprocessing_rules.py
"""Tests for preprocessing rules knowledge module."""
import re
import pytest
from agents4geosx.knowledge.preprocessing_rules import (
    PROCESSING_PIPELINE,
    PARAMETER_RULES,
    SYMBOLIC_MATH_RULES,
    INCLUDE_RULES,
    SPECIAL_CHARACTERS,
)


class TestProcessingPipeline:
    def test_has_five_stages(self):
        assert len(PROCESSING_PIPELINE) == 5

    def test_stages_ordered(self):
        stages = [s["stage"] for s in PROCESSING_PIPELINE]
        assert stages == [1, 2, 3, 4, 5]

    def test_includes_before_parameters(self):
        names = [s["name"] for s in PROCESSING_PIPELINE]
        assert names.index("include_merging") < names.index("parameter_substitution")

    def test_parameters_before_units(self):
        names = [s["name"] for s in PROCESSING_PIPELINE]
        assert names.index("parameter_substitution") < names.index("unit_conversion")

    def test_units_before_symbolic(self):
        names = [s["name"] for s in PROCESSING_PIPELINE]
        assert names.index("unit_conversion") < names.index("symbolic_math")

    def test_validation_is_last(self):
        assert PROCESSING_PIPELINE[-1]["name"] == "special_char_validation"


class TestParameterRules:
    def test_regex_matches_dollar_name_dollar(self):
        m = re.search(PARAMETER_RULES["regex"], "$myParam$")
        assert m is not None
        assert m.group(1) == "myParam"

    def test_regex_matches_dollar_colon_name(self):
        m = re.search(PARAMETER_RULES["regex"], "$:myParam")
        assert m is not None
        assert m.group(1) == "myParam"

    def test_regex_matches_dollar_name_no_trailing(self):
        m = re.search(PARAMETER_RULES["regex"], "$myParam")
        assert m is not None
        assert m.group(1) == "myParam"

    def test_max_nesting(self):
        assert PARAMETER_RULES["max_nesting"] == 100

    def test_source_element(self):
        assert PARAMETER_RULES["source_element"] == "Parameters/Parameter"


class TestSymbolicMathRules:
    def test_regex_matches_backtick_expr(self):
        m = re.search(SYMBOLIC_MATH_RULES["regex"], "`1 + 2.34e5*2`")
        assert m is not None
        assert m.group(1) == "1 + 2.34e5*2"

    def test_max_nesting(self):
        assert SYMBOLIC_MATH_RULES["max_nesting"] == 100

    def test_protected_elements(self):
        elements = [p["element"] for p in SYMBOLIC_MATH_RULES["protected_elements"]]
        assert "SymbolicFunction" in elements
        assert "CompositeFunction" in elements

    def test_regex_no_match_without_backticks(self):
        m = re.search(SYMBOLIC_MATH_RULES["regex"], "1 + 2")
        assert m is None


class TestIncludeRules:
    def test_max_depth(self):
        assert INCLUDE_RULES["max_depth"] == 100

    def test_insert_only_elements(self):
        assert "Nodeset" in INCLUDE_RULES["insert_only_elements"]

    def test_root_element(self):
        assert INCLUDE_RULES["root_element"] == "Problem"


class TestSpecialCharacters:
    def test_all_four_present(self):
        assert "$" in SPECIAL_CHARACTERS
        assert "[" in SPECIAL_CHARACTERS
        assert "]" in SPECIAL_CHARACTERS
        assert "`" in SPECIAL_CHARACTERS

    def test_length(self):
        assert len(SPECIAL_CHARACTERS) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_preprocessing_rules.py -v`
Expected: ImportError.

- [ ] **Step 3: Write implementation**

```python
# src/agents4geosx/knowledge/preprocessing_rules.py
"""GEOS XML preprocessing pipeline and conventions.

Encodes the strict order of operations and syntax rules for XML
preprocessing features: file inclusion, parameter substitution,
unit conversion, and symbolic math evaluation.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Processing pipeline — strict order of operations
# Order matters: parameters can appear inside unit expressions,
# units can appear inside symbolic expressions.
# ---------------------------------------------------------------------------
PROCESSING_PIPELINE: list[dict] = [
    {
        "stage": 1,
        "name": "include_merging",
        "description": "Merge <Included> file blocks into main document",
        "nesting_limit": 100,
    },
    {
        "stage": 2,
        "name": "parameter_substitution",
        "description": "Expand $Name$ patterns from <Parameters> section",
        "nesting_limit": 100,
    },
    {
        "stage": 3,
        "name": "unit_conversion",
        "description": "Evaluate [unit] bracket notation to SI values",
        "nesting_limit": None,
    },
    {
        "stage": 4,
        "name": "symbolic_math",
        "description": "Evaluate `expression` backtick notation",
        "nesting_limit": 100,
    },
    {
        "stage": 5,
        "name": "special_char_validation",
        "description": "Flag leftover $, [, ], ` as unresolved",
        "nesting_limit": None,
    },
]

# ---------------------------------------------------------------------------
# Parameter substitution rules (geos-xml-tools regex_tools.py)
# ---------------------------------------------------------------------------
PARAMETER_RULES: dict = {
    "regex": r"\$:?([a-zA-Z_0-9]*)\$?",
    "valid_name_chars": "[a-zA-Z_0-9]",
    "colon_prefix_optional": True,
    "trailing_dollar_optional": True,
    "max_nesting": 100,
    "source_element": "Parameters/Parameter",
    "source_attrs": {"name": "parameter name", "value": "parameter value"},
    "cli_override": True,
}

# ---------------------------------------------------------------------------
# Symbolic math rules (geos-xml-tools regex_tools.py)
# ---------------------------------------------------------------------------
SYMBOLIC_MATH_RULES: dict = {
    "regex": r"\`([-+.*/() 0-9eE]*)\`",
    "allowed_chars": "+-.*/()" + "0123456789" + "eE ",
    "max_nesting": 100,
    "protected_elements": [
        {"element": "SymbolicFunction", "attribute": "expression"},
        {"element": "CompositeFunction", "attribute": "expression"},
    ],
}

# ---------------------------------------------------------------------------
# Include merging rules (geos-xml-tools xml_processor.py)
# ---------------------------------------------------------------------------
INCLUDE_RULES: dict = {
    "max_depth": 100,
    "merge_strategy": "attributes overridden, named elements matched by name attr",
    "insert_only_elements": ["Nodeset"],
    "root_element": "Problem",
    "source_structure": "Included/File[@name]",
}

# ---------------------------------------------------------------------------
# Special characters that must be fully consumed after processing.
# Leftover means unresolved parameter, unit, or expression.
# ---------------------------------------------------------------------------
SPECIAL_CHARACTERS: list[str] = ["$", "[", "]", "`"]
```

- [ ] **Step 4: Run tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_preprocessing_rules.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/knowledge/preprocessing_rules.py tests/test_preprocessing_rules.py
git commit -m "feat: add preprocessing_rules.py knowledge module

XML preprocessing pipeline, parameter substitution, symbolic math,
include merging rules. Sourced from geos-xml-tools."
```

---

### Task 3: Create formatting_conventions.py knowledge module

**Goal:** Create the formatting conventions module.

**Files:**
- Create: `src/agents4geosx/knowledge/formatting_conventions.py`
- Create: `tests/test_formatting_conventions.py`

**Acceptance Criteria:**
- [ ] DEFAULT_FORMAT has all 5 fields
- [ ] ATTRIBUTE_FORMATTING has 4 normalization patterns + array split
- [ ] PROTECTED_EXPRESSIONS lists 2 element/attribute combos
- [ ] geos-xml-tools credited in docstring
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_formatting_conventions.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

```python
# tests/test_formatting_conventions.py
"""Tests for formatting conventions knowledge module."""
import re
import pytest
from agents4geosx.knowledge.formatting_conventions import (
    DEFAULT_FORMAT,
    ATTRIBUTE_FORMATTING,
    PROTECTED_EXPRESSIONS,
)


class TestDefaultFormat:
    def test_indent(self):
        assert DEFAULT_FORMAT["indent"] == 2

    def test_style(self):
        assert DEFAULT_FORMAT["style"] == "fixed"

    def test_block_separation(self):
        assert DEFAULT_FORMAT["block_separation_max_depth"] == 2

    def test_sort_attributes(self):
        assert DEFAULT_FORMAT["sort_attributes"] is False

    def test_close_tag_newline(self):
        assert DEFAULT_FORMAT["close_tag_newline"] is False


class TestAttributeFormatting:
    def test_comma_spacing_pattern_compiles(self):
        p = ATTRIBUTE_FORMATTING["comma_spacing"]
        re.compile(p["pattern"])

    def test_comma_spacing_replacement(self):
        p = ATTRIBUTE_FORMATTING["comma_spacing"]
        result = re.sub(p["pattern"], p["replacement"], "a,b,  c")
        assert result == "a, b, c"

    def test_brace_opening(self):
        p = ATTRIBUTE_FORMATTING["brace_opening"]
        result = re.sub(p["pattern"], p["replacement"], "{value")
        assert result == "{ value"

    def test_brace_closing(self):
        p = ATTRIBUTE_FORMATTING["brace_closing"]
        result = re.sub(p["pattern"], p["replacement"], "value}")
        assert result == "value }"

    def test_whitespace_consolidation(self):
        p = ATTRIBUTE_FORMATTING["whitespace_consolidation"]
        result = re.sub(p["pattern"], p["replacement"], "a  b   c")
        assert result == "a b c"


class TestProtectedExpressions:
    def test_symbolic_function_protected(self):
        elements = [p["element"] for p in PROTECTED_EXPRESSIONS]
        assert "SymbolicFunction" in elements

    def test_composite_function_protected(self):
        elements = [p["element"] for p in PROTECTED_EXPRESSIONS]
        assert "CompositeFunction" in elements

    def test_expression_attribute(self):
        for entry in PROTECTED_EXPRESSIONS:
            assert entry["attribute"] == "expression"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_formatting_conventions.py -v`
Expected: ImportError.

- [ ] **Step 3: Write implementation**

```python
# src/agents4geosx/knowledge/formatting_conventions.py
"""GEOS XML output formatting conventions.

Encodes the formatting rules used by geos-xml-tools to produce
canonical XML output. Use these conventions when generating XML
so the agent's output matches the style of hand-edited GEOS files.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Default XML formatting options (geos-xml-tools xml_formatter.py)
# ---------------------------------------------------------------------------
DEFAULT_FORMAT: dict = {
    "indent": 2,                        # spaces per level
    "style": "fixed",                   # "fixed" (standard indent) or "hanging" (align with tag)
    "block_separation_max_depth": 2,    # blank lines between children up to this depth
    "sort_attributes": False,           # alphabetize attributes
    "close_tag_newline": False,         # True: />\n on new line, False: inline />
}

# ---------------------------------------------------------------------------
# Attribute value normalization (geos-xml-tools xml_formatter.py)
# ---------------------------------------------------------------------------
ATTRIBUTE_FORMATTING: dict[str, dict] = {
    "comma_spacing": {
        "pattern": r",\s*",
        "replacement": ", ",
    },
    "brace_opening": {
        "pattern": r"\{\s*",
        "replacement": "{ ",
    },
    "brace_closing": {
        "pattern": r"\s*\}",
        "replacement": " }",
    },
    "whitespace_consolidation": {
        "pattern": r"\s+",
        "replacement": " ",
    },
    "array_split_pattern": r"\s*\{\s*(\{[-+.,0-9a-zA-Z\s]*\},?\s*)*\s*\}",
}

# ---------------------------------------------------------------------------
# Element/attribute combinations whose values must never be reformatted
# (geos-xml-tools xml_formatter.py — mathpresso expression preservation)
# ---------------------------------------------------------------------------
PROTECTED_EXPRESSIONS: list[dict] = [
    {"element": "SymbolicFunction", "attribute": "expression"},
    {"element": "CompositeFunction", "attribute": "expression"},
]
```

- [ ] **Step 4: Run tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_formatting_conventions.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/knowledge/formatting_conventions.py tests/test_formatting_conventions.py
git commit -m "feat: add formatting_conventions.py knowledge module

XML output formatting rules: indentation, attribute spacing, brace
normalization, protected expressions. Sourced from geos-xml-tools."
```

---

### Task 4: Update existing knowledge modules

**Goal:** Add new rules to sanity_rules.py, cross_refs.py, and lessons_learned.md.

**Files:**
- Modify: `src/agents4geosx/knowledge/sanity_rules.py`
- Modify: `src/agents4geosx/knowledge/cross_refs.py`
- Modify: `knowledge/lessons_learned.md`
- Modify: `tests/test_postproc_tools.py`
- Modify: `tests/test_xml_tools.py`

**Acceptance Criteria:**
- [ ] sanity_rules.py has STRUCTURAL_RULES with InputFlags, redundancy, zero-children
- [ ] cross_refs.py has NESTING_CONSTRAINTS and check_nesting function
- [ ] lessons_learned.md has schema validation lesson
- [ ] All existing tests still pass
- [ ] New tests cover new rules

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/ -v`

**Steps:**

- [ ] **Step 1: Add STRUCTURAL_RULES to sanity_rules.py**

Add after `COUPLED_SOLID_TYPES` (line 53):

```python
# Structural validation rules beyond physics heuristics.
# These check document structure patterns that the XSD schema alone cannot enforce.
STRUCTURAL_RULES: list[dict] = [
    {
        "name": "required_attributes",
        "description": "REQUIRED attributes (InputFlags) must be present",
        "severity": "error",
    },
    {
        "name": "redundant_defaults",
        "description": "Attributes matching schema default values are redundant",
        "severity": "advisory",
    },
    {
        "name": "empty_elements",
        "description": "Elements with no required children and no actual children may be unnecessary",
        "severity": "advisory",
    },
]
```

- [ ] **Step 2: Add NESTING_CONSTRAINTS and check_nesting to cross_refs.py**

Add after `get_cross_references` function (line 33):

```python
# Nesting constraints from geos-xml-tools attribute coverage analysis.
# Elements that cannot appear nested within themselves.
NESTING_CONSTRAINTS: dict = {
    "self_nesting_prohibited": [
        "PeriodicEvent",
    ],
}


def check_nesting(parent_type: str, child_type: str) -> dict:
    """Check if nesting child_type inside parent_type is valid.

    Returns:
        {"valid": bool, "reason": str}
    """
    if child_type in NESTING_CONSTRAINTS["self_nesting_prohibited"]:
        if parent_type == child_type:
            return {
                "valid": False,
                "reason": f"{child_type} cannot be nested within itself",
            }
    return {"valid": True, "reason": ""}
```

- [ ] **Step 3: Add schema validation lesson to lessons_learned.md**

Append at the end of the file:

```markdown

## Schema Validation

### Schema validation is necessary but not sufficient
- **Context:** The XSD schema (`schema.xsd`) is auto-generated from C++ source code
- **Limitation:** `xmllint` validates XML structure against the schema, but cannot catch
  physics errors (wrong permeability range), cross-reference inconsistencies (dangling
  names), or preprocessing issues (unresolved parameters)
- **Right approach:** Always use all three validation layers together:
  1. Schema validation (`validate_xml` / `xmllint`)
  2. Cross-reference validation (`validate_cross_references`)
  3. Physics sanity checks (`sanity_check`)
- **Source:** GEOS Developer Guide — XML Key Components
```

- [ ] **Step 4: Write tests for new rules**

Add to `tests/test_postproc_tools.py` — test that STRUCTURAL_RULES is importable:

```python
def test_structural_rules_exist():
    from agents4geosx.knowledge.sanity_rules import STRUCTURAL_RULES
    assert len(STRUCTURAL_RULES) == 3
    names = [r["name"] for r in STRUCTURAL_RULES]
    assert "required_attributes" in names
    assert "redundant_defaults" in names
    assert "empty_elements" in names
```

Add to `tests/test_xml_tools.py` — test check_nesting:

```python
def test_nesting_self_prohibited():
    from agents4geosx.knowledge.cross_refs import check_nesting
    result = check_nesting("PeriodicEvent", "PeriodicEvent")
    assert result["valid"] is False

def test_nesting_different_types_ok():
    from agents4geosx.knowledge.cross_refs import check_nesting
    result = check_nesting("Solvers", "SinglePhaseFVM")
    assert result["valid"] is True
```

- [ ] **Step 5: Run all tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/ -v`
Expected: All tests PASS (existing + new).

- [ ] **Step 6: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/knowledge/sanity_rules.py \
        src/agents4geosx/knowledge/cross_refs.py \
        knowledge/lessons_learned.md \
        tests/test_postproc_tools.py \
        tests/test_xml_tools.py
git commit -m "feat: enrich existing knowledge modules

Add STRUCTURAL_RULES (InputFlags, redundancy, empty elements) to sanity_rules.
Add NESTING_CONSTRAINTS and check_nesting to cross_refs.
Add schema validation lesson to lessons_learned."
```

---

### Task 5: Wire new knowledge into sanity_check and validate_cross_references

**Goal:** Update existing tools to read from new knowledge modules.

**Files:**
- Modify: `src/agents4geosx/tools/postproc_tools.py`
- Modify: `src/agents4geosx/tools/xml_tools.py`
- Modify: `tests/test_postproc_tools.py`
- Modify: `tests/test_xml_tools.py`

**Acceptance Criteria:**
- [ ] sanity_check validates bracket notation unit expressions in attribute values
- [ ] sanity_check flags leftover special characters ($, [, ], `)
- [ ] validate_cross_references checks nesting constraints
- [ ] All tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/ -v`

**Steps:**

- [ ] **Step 1: Add unit validation and special char detection to sanity_check**

In `postproc_tools.py`, modify `sanity_check` function (currently lines 228-244). Add after `checks.extend(structural)` (line 239):

```python
    # Unit expression validation
    from agents4geosx.knowledge.unit_conventions import validate_unit_expression
    from agents4geosx.knowledge.preprocessing_rules import SPECIAL_CHARACTERS
    for attr_name, attr_value in all_attrs.items():
        # Check bracket notation uses valid units
        if "[" in attr_value and "]" in attr_value:
            unit_result = validate_unit_expression(attr_value)
            if not unit_result["valid"]:
                checks.append({
                    "name": "invalid_unit_expression",
                    "attribute": attr_name,
                    "value": attr_value,
                    "status": "fail",
                    "message": f"Unknown unit(s) in bracket notation: {unit_result['unknown']}",
                })
        # Check for leftover special characters (unresolved preprocessing)
        for char in SPECIAL_CHARACTERS:
            if char in attr_value:
                # Skip bracket notation values (those are valid units, not leftovers)
                if char in "[]" and re.search(r"\d\[", attr_value):
                    continue
                # Skip expressions that look like GEOS symbolic pass-through
                if char == "$" or char == "`":
                    checks.append({
                        "name": "unresolved_preprocessing",
                        "attribute": attr_name,
                        "value": attr_value,
                        "status": "advisory",
                        "message": f"Contains '{char}' — may be an unresolved {{'$': 'parameter', '`': 'symbolic expression'}.get(char, 'expression')}",
                    })
```

Also add `import re` at the top of the function if not already present.

- [ ] **Step 2: Add nesting check to validate_cross_references**

In `xml_tools.py`, modify the `_check_refs` helper or add a new helper called from `validate_cross_references`. Add after the existing cross-reference check (line 489):

```python
    # Nesting constraint checks
    from agents4geosx.knowledge.cross_refs import check_nesting
    nesting_errors = []
    _check_nesting_recursive(doc.root, nesting_errors)
    errors.extend(nesting_errors)
    return {"valid": len(errors) == 0, "errors": errors}
```

Add a new helper function:

```python
def _check_nesting_recursive(el, errors: list, parent_type: str = "") -> None:
    el_type = el.schema_element.name if hasattr(el, "schema_element") else ""
    if parent_type and el_type:
        result = check_nesting(parent_type, el_type)
        if not result["valid"]:
            errors.append({
                "path": f"{parent_type}/{el_type}",
                "error": result["reason"],
            })
    for child in el.children:
        _check_nesting_recursive(child, errors, el_type)
```

- [ ] **Step 3: Write tests for wired-in checks**

Add to `tests/test_postproc_tools.py`:

```python
def test_sanity_check_flags_invalid_unit(mock_document_store):
    """sanity_check should flag unknown units in bracket notation."""
    # Create a document with an attribute containing invalid unit notation
    doc_id = create_test_doc_with_attrs({"someAttr": "9.81[foobar/s]"})
    result = sanity_check(doc_id)
    unit_failures = [c for c in result["checks"] if c["name"] == "invalid_unit_expression"]
    assert len(unit_failures) > 0
```

Add to `tests/test_xml_tools.py`:

```python
def test_validate_cross_refs_catches_self_nesting(mock_document_store):
    """validate_cross_references should flag self-nested elements."""
    # Create a document with PeriodicEvent nested inside PeriodicEvent
    doc_id = create_test_doc_with_nesting("PeriodicEvent", "PeriodicEvent")
    result = validate_cross_references(doc_id)
    assert result["valid"] is False
    nesting_errors = [e for e in result["errors"] if "nested" in e.get("error", "").lower()]
    assert len(nesting_errors) > 0
```

Note: The exact test helper functions (`create_test_doc_with_attrs`, `create_test_doc_with_nesting`) depend on the existing test fixtures in `conftest.py`. The implementer should read `tests/conftest.py` and existing test patterns to create appropriate test helpers.

- [ ] **Step 4: Run all tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/tools/postproc_tools.py \
        src/agents4geosx/tools/xml_tools.py \
        tests/test_postproc_tools.py \
        tests/test_xml_tools.py
git commit -m "feat: wire unit validation and nesting checks into existing tools

sanity_check now validates bracket notation units and flags leftover
special characters. validate_cross_references now checks nesting constraints."
```
