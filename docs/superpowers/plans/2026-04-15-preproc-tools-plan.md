# Preprocessing Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 new MCP tools (convert_units, expand_parameters, resolve_includes, format_xml) in a new `preproc_tools.py` module.

**Architecture:** New tool module registered in server.py, reading from existing knowledge modules (unit_conventions, preprocessing_rules, formatting_conventions). Each tool is a thin wrapper around knowledge + logic.

**Tech Stack:** Python 3.11+, FastMCP, lxml, pytest, regex

**User Verification:** NO

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/agents4geosx/tools/preproc_tools.py` | 4 new MCP tools |
| Create | `tests/test_preproc_tools.py` | Tests for all 4 tools |
| Modify | `src/agents4geosx/server.py` | Register new module |
| Modify | `AGENTS.md` | Add tools to inventory, update count |
| Modify | `README.md` | Update tool count |

---

### Task 1: Create `preproc_tools.py` with `convert_units` tool

**Goal:** Implement the `convert_units` MCP tool and register the new module.

**Files:**
- Create: `src/agents4geosx/tools/preproc_tools.py`
- Create: `tests/test_preproc_tools.py`
- Modify: `src/agents4geosx/server.py`

**Acceptance Criteria:**
- [ ] `convert_units("9.81[m/s**2]")` returns correct SI value
- [ ] `convert_units("100[mD]")` converts millidarcy correctly
- [ ] `convert_units("3.0[km]")` handles SI prefix
- [ ] `convert_units("1.0[foobar]")` returns valid=False with unknown units
- [ ] `convert_units("plain text")` returns si_value=None gracefully
- [ ] Module registered in server.py
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

```python
# tests/test_preproc_tools.py
"""Tests for preprocessing MCP tools."""
from __future__ import annotations

import pytest
from agents4geosx.tools.preproc_tools import convert_units


class TestConvertUnits:
    def test_si_base_no_conversion(self):
        result = convert_units("9.81[m/s**2]")
        assert result["valid"] is True
        assert result["numeric_value"] == 9.81
        assert result["unit_expression"] == "m/s**2"
        assert abs(result["si_value"] - 9.81) < 1e-10

    def test_millidarcy(self):
        result = convert_units("100[mD]")
        assert result["valid"] is True
        assert result["numeric_value"] == 100.0
        # 1 mD = 9.869233e-16 m^2, so 100 mD ≈ 9.869233e-14
        assert abs(result["si_value"] - 9.869233e-14) / 9.869233e-14 < 1e-4

    def test_prefix_kilo(self):
        result = convert_units("3.0[km]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 3000.0) < 1e-10

    def test_prefix_mega_pascal(self):
        result = convert_units("20[MPa]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 20e6) < 1e-2

    def test_psi(self):
        result = convert_units("1000[psi]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 6894760.0) < 100

    def test_barrel_per_day(self):
        result = convert_units("1.0[bbl/day]")
        assert result["valid"] is True
        # 1 bbl = 0.1589873 m^3, 1 day = 86400 s
        expected = 0.1589873 / 86400.0
        assert abs(result["si_value"] - expected) / expected < 1e-4

    def test_scientific_notation_input(self):
        result = convert_units("3.14e-2[Pa]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 3.14e-2) < 1e-10

    def test_invalid_unit(self):
        result = convert_units("1.0[foobar]")
        assert result["valid"] is False
        assert "foobar" in result["unknown_units"]

    def test_no_brackets(self):
        result = convert_units("plain text")
        assert result["valid"] is True
        assert result["si_value"] is None

    def test_space_before_bracket(self):
        result = convert_units("1.0 [bbl]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 0.1589873) < 1e-6

    def test_centipoise(self):
        result = convert_units("1.0[cP]")
        assert result["valid"] is True
        # centi + poise = 1e-2 * 0.1 = 0.001 Pa·s
        assert abs(result["si_value"] - 0.001) < 1e-10

    def test_foot(self):
        result = convert_units("100[ft]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 30.48) < 1e-6
```

- [ ] **Step 2: Write implementation**

```python
# src/agents4geosx/tools/preproc_tools.py
"""XML preprocessing MCP tools (Group 6).

Tools for unit conversion, parameter expansion, include resolution,
and XML formatting. Uses knowledge modules from the knowledge enrichment
(Part 1) implementation.
"""
from __future__ import annotations

import re

from agents4geosx.server import mcp
from agents4geosx.knowledge.unit_conventions import (
    UNIT_DEFINITIONS,
    SI_PREFIXES,
    BRACKET_NOTATION_REGEX,
    validate_unit_expression,
)


def _build_unit_scale_map() -> dict[str, float]:
    """Build a map from every valid unit name/alias to its SI scale factor."""
    scales: dict[str, float] = {}
    for name, defn in UNIT_DEFINITIONS.items():
        scales[name] = defn["value"]
        for alt in defn["alt"]:
            scales[alt] = defn["value"]
        if defn["usePrefix"]:
            for prefix_name, prefix_def in SI_PREFIXES.items():
                if prefix_name:
                    pval = prefix_def["value"]
                    scales[prefix_name + name] = pval * defn["value"]
                    scales[prefix_def["alt"] + name] = pval * defn["value"]
                    for alt in defn["alt"]:
                        scales[prefix_name + alt] = pval * defn["value"]
                        scales[prefix_def["alt"] + alt] = pval * defn["value"]
    return scales


_UNIT_SCALES = _build_unit_scale_map()
_UNIT_NAME_RE = re.compile(r"[a-zA-Z]+")


def _evaluate_unit_expression(unit_expr: str) -> float:
    """Replace unit names with scale factors and evaluate the arithmetic."""
    def _replace_unit(match: re.Match) -> str:
        name = match.group(0)
        if name in _UNIT_SCALES:
            return str(_UNIT_SCALES[name])
        if name in ("e", "E"):
            return name
        return name

    substituted = _UNIT_NAME_RE.sub(_replace_unit, unit_expr)
    # Sanitize: only allow digits, operators, dots, e/E, spaces, parens
    sanitized = re.sub(r"[a-df-zA-DF-Z]", "", substituted)
    return float(eval(sanitized, {"__builtins__": None}))


@mcp.tool
def convert_units(expression: str) -> dict:
    """Convert a GEOS bracket-notation expression to SI units.

    Parses expressions like "9.81[m/s**2]" or "100[mD]" and returns the
    SI-converted value. Supports all GEOS unit names, aliases, and SI prefixes.

    Args:
        expression: A string possibly containing bracket notation (e.g., "100[mD]")
    """
    match = re.search(BRACKET_NOTATION_REGEX, expression)
    if match is None:
        return {
            "original": expression,
            "si_value": None,
            "valid": True,
            "message": "No bracket notation found",
        }

    numeric_str = match.group(1)
    unit_expr = match.group(2)
    numeric_value = float(numeric_str)

    validation = validate_unit_expression(expression)
    if not validation["valid"]:
        return {
            "original": expression,
            "numeric_value": numeric_value,
            "unit_expression": unit_expr,
            "si_value": None,
            "valid": False,
            "unknown_units": validation["unknown"],
        }

    si_scale = _evaluate_unit_expression(unit_expr)
    si_value = numeric_value * si_scale

    return {
        "original": expression,
        "numeric_value": numeric_value,
        "unit_expression": unit_expr,
        "si_value": si_value,
        "units_found": validation["units_found"],
        "valid": True,
    }
```

- [ ] **Step 3: Register module in server.py**

Add to `register_all_tools` in `src/agents4geosx/server.py`:

```python
    import agents4geosx.tools.preproc_tools  # noqa: F401
```

- [ ] **Step 4: Run tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/tools/preproc_tools.py tests/test_preproc_tools.py src/agents4geosx/server.py
git commit -m "feat: add convert_units MCP tool in new preproc_tools.py

Parses GEOS bracket notation (e.g., '100[mD]') and converts to SI.
Supports all unit names, aliases, and SI prefixes from unit_conventions.
New module registered in server.py."
```

---

### Task 2: Add `expand_parameters` tool

**Goal:** Add parameter expansion tool to `preproc_tools.py`.

**Files:**
- Modify: `src/agents4geosx/tools/preproc_tools.py`
- Modify: `tests/test_preproc_tools.py`

**Acceptance Criteria:**
- [ ] Reads `<Parameters>` section from document
- [ ] Expands `$Name$`, `$:Name`, `$Name` patterns in all attributes
- [ ] Handles nested parameters up to 100 levels
- [ ] Reports unresolved parameters
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

Add to `tests/test_preproc_tools.py`:

```python
from agents4geosx.tools.preproc_tools import convert_units, expand_parameters
from agents4geosx.tools.xml_tools import create_document, add_element, add_child


class TestExpandParameters:
    def test_basic_expansion(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        # Add a Parameter
        add_element(doc_id, "Parameters", "Parameter", "injRate",
                    {"value": "1e-4"})
        # Add an element using the parameter
        add_element(doc_id, "FieldSpecifications", "FieldSpecification", "injection",
                    {"scale": "$injRate$", "fieldName": "pressure"})
        result = expand_parameters(doc_id)
        assert result["parameters_found"]["injRate"] == "1e-4"
        assert result["substitutions_made"] >= 1
        assert len(result["unresolved"]) == 0

    def test_unresolved_parameter(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        add_element(doc_id, "FieldSpecifications", "FieldSpecification", "injection",
                    {"scale": "$undefinedParam$", "fieldName": "pressure"})
        result = expand_parameters(doc_id)
        assert "undefinedParam" in result["unresolved"]

    def test_no_parameters_section(self, schema):
        doc = create_document()
        doc_id = doc["doc_id"]
        result = expand_parameters(doc_id)
        assert result["parameters_found"] == {}
        assert result["substitutions_made"] == 0

    def test_invalid_doc_id(self):
        result = expand_parameters("nonexistent")
        assert "error" in result
```

- [ ] **Step 2: Write implementation**

Add to `src/agents4geosx/tools/preproc_tools.py`:

```python
from agents4geosx.knowledge.preprocessing_rules import PARAMETER_RULES


@mcp.tool
def expand_parameters(doc_id: str) -> dict:
    """Expand $Name$ parameter patterns in all document attributes.

    Reads parameter values from the <Parameters> section and substitutes
    them into all attribute values throughout the document.

    Args:
        doc_id: Document ID from create_document or load_xml
    """
    from agents4geosx.tools.xml_tools import _store

    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    # Build parameter map from <Parameters> section
    param_map: dict[str, str] = {}
    for section in doc.root.children:
        if section.schema_element.name == "Parameters":
            for param in section.children:
                pname = param.attributes.get("name", "")
                pvalue = param.attributes.get("value", "")
                if pname:
                    param_map[pname] = pvalue

    if not param_map:
        return {
            "parameters_found": {},
            "substitutions_made": 0,
            "unresolved": [],
            "details": [],
        }

    regex = re.compile(PARAMETER_RULES["regex"])
    max_nesting = PARAMETER_RULES["max_nesting"]
    substitutions = 0
    unresolved: set[str] = set()
    details: list[dict] = []

    def _expand_attrs(el, path: str) -> None:
        nonlocal substitutions
        el_name = el.schema_element.name if hasattr(el, "schema_element") else "?"
        current = f"{path}/{el_name}" if path else el_name

        for attr_name, attr_value in list(el.attributes.items()):
            if "$" not in attr_value:
                continue
            original = attr_value
            value = attr_value
            iterations = 0
            while "$" in value and iterations < max_nesting:
                def _replace(m: re.Match) -> str:
                    name = m.group(1)
                    if name in param_map:
                        return param_map[name]
                    unresolved.add(name)
                    return m.group(0)  # Leave unresolved as-is
                value = regex.sub(_replace, value)
                iterations += 1
                if value == el.attributes[attr_name]:
                    break  # No more substitutions possible
                el.attributes[attr_name] = value

            if value != original:
                substitutions += 1
                details.append({
                    "path": f"{current}/@{attr_name}",
                    "before": original,
                    "after": value,
                })

        for child in el.children:
            _expand_attrs(child, current)

    _expand_attrs(doc.root, "")

    return {
        "parameters_found": param_map,
        "substitutions_made": substitutions,
        "unresolved": sorted(unresolved),
        "details": details,
    }
```

- [ ] **Step 3: Run tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/tools/preproc_tools.py tests/test_preproc_tools.py
git commit -m "feat: add expand_parameters MCP tool

Resolves \$Name\$ patterns in document attributes using values from
the <Parameters> section. Handles nested parameters up to 100 levels."
```

---

### Task 3: Add `resolve_includes` tool

**Goal:** Add include resolution tool to `preproc_tools.py`.

**Files:**
- Modify: `src/agents4geosx/tools/preproc_tools.py`
- Modify: `tests/test_preproc_tools.py`

**Acceptance Criteria:**
- [ ] Finds `<Included>` blocks and merges referenced files
- [ ] Replaces `<Included>` block with provenance comment
- [ ] Handles max depth (100)
- [ ] Reports files merged and elements added
- [ ] Returns gracefully when no includes found
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

Add to `tests/test_preproc_tools.py`:

```python
from agents4geosx.tools.preproc_tools import convert_units, expand_parameters, resolve_includes


class TestResolveIncludes:
    def test_no_includes(self, schema):
        doc = create_document(template="single_phase_flow")
        doc_id = doc["doc_id"]
        result = resolve_includes(doc_id)
        assert result["files_merged"] == []
        assert result["elements_added"] == 0

    def test_invalid_doc_id(self):
        result = resolve_includes("nonexistent")
        assert "error" in result

    def test_include_with_missing_file(self, schema, tmp_output):
        doc = create_document()
        doc_id = doc["doc_id"]
        # Add an Included section with a non-existent file
        add_element(doc_id, "Included", "File", "",
                    {"name": str(tmp_output / "nonexistent.xml")})
        result = resolve_includes(doc_id)
        assert len(result.get("errors", [])) > 0

    def test_include_merges_file(self, schema, tmp_output):
        # Create an include file with a Geometry box
        include_path = tmp_output / "boxes.xml"
        include_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem>\n'
            '  <Geometry>\n'
            '    <Box name="source" xMin="{ -0.01, -0.01, -0.01 }" '
            'xMax="{ 10.01, 10.01, 10.01 }"/>\n'
            '  </Geometry>\n'
            '</Problem>\n'
        )
        doc = create_document()
        doc_id = doc["doc_id"]
        add_element(doc_id, "Included", "File", "",
                    {"name": str(include_path)})
        result = resolve_includes(doc_id)
        assert str(include_path) in result["files_merged"]
        assert result["elements_added"] >= 1
```

- [ ] **Step 2: Write implementation**

Add to `src/agents4geosx/tools/preproc_tools.py`:

```python
from lxml import etree
from agents4geosx.knowledge.preprocessing_rules import INCLUDE_RULES


@mcp.tool
def resolve_includes(doc_id: str) -> dict:
    """Merge <Included> file blocks into the document.

    Reads File elements from the <Included> section, parses each referenced
    XML file, and merges its content into the document. The <Included> block
    is replaced with an XML comment listing merged files for provenance.

    Args:
        doc_id: Document ID from create_document or load_xml
    """
    from agents4geosx.tools.xml_tools import _store

    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    # Find Included sections
    include_sections = [
        s for s in doc.root.children
        if s.schema_element.name == "Included"
    ]
    if not include_sections:
        return {"files_merged": [], "elements_added": 0, "comment": ""}

    files_merged: list[str] = []
    elements_added = 0
    errors: list[str] = []
    max_depth = INCLUDE_RULES["max_depth"]
    insert_only = set(INCLUDE_RULES["insert_only_elements"])

    for inc_section in include_sections:
        for file_el in inc_section.children:
            file_path = file_el.attributes.get("name", "")
            if not file_path:
                continue
            try:
                tree = etree.parse(file_path)
                inc_root = tree.getroot()
                count = _merge_lxml_into_doc(doc.root, inc_root, insert_only)
                elements_added += count
                files_merged.append(file_path)
            except Exception as exc:
                errors.append(f"Failed to include '{file_path}': {exc}")

    # Replace Included sections with provenance comments
    for inc_section in include_sections:
        doc.root.children.remove(inc_section)
    if files_merged:
        file_names = ", ".join(Path(f).name for f in files_merged)
        comment = f"<!-- Included files merged: {file_names} -->"
        doc.root.comments.append(comment)
    else:
        comment = ""

    result = {
        "files_merged": files_merged,
        "elements_added": elements_added,
        "comment": comment,
    }
    if errors:
        result["errors"] = errors
    return result


def _merge_lxml_into_doc(doc_root, lxml_root, insert_only: set) -> int:
    """Merge elements from an lxml tree into the DocumentState tree."""
    from agents4geosx.config import get_schema

    schema = get_schema()
    count = 0

    for lxml_section in lxml_root:
        if not isinstance(lxml_section.tag, str):
            continue  # skip comments, PIs
        section_name = lxml_section.tag

        # Find matching section in doc
        target_section = None
        for s in doc_root.children:
            if s.schema_element.name == section_name:
                target_section = s
                break

        if target_section is None:
            continue  # Section not in document — skip

        for lxml_el in lxml_section:
            if not isinstance(lxml_el.tag, str):
                continue
            el_name = lxml_el.get("name", "")
            el_type = lxml_el.tag

            # Check if element with same name already exists
            existing = None
            if el_name and el_type not in insert_only:
                for child in target_section.children:
                    if (child.schema_element.name == el_type and
                            child.attributes.get("name") == el_name):
                        existing = child
                        break

            if existing is not None:
                # Merge: override attributes
                for attr_name, attr_value in lxml_el.attrib.items():
                    existing.attributes[attr_name] = attr_value
            else:
                # Insert new element
                schema_el = schema.find_element(el_type)
                if schema_el is None:
                    continue
                from geos_tui.xml.state import ElementState
                new_el = ElementState(
                    schema_element=schema_el,
                    attributes=dict(lxml_el.attrib),
                )
                target_section.children.append(new_el)
                count += 1

    return count
```

- [ ] **Step 3: Run tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/tools/preproc_tools.py tests/test_preproc_tools.py
git commit -m "feat: add resolve_includes MCP tool

Merges <Included> file blocks into documents. Replaces Included
section with provenance comment listing merged files."
```

---

### Task 4: Add `format_xml` tool

**Goal:** Add XML formatting tool to `preproc_tools.py`.

**Files:**
- Modify: `src/agents4geosx/tools/preproc_tools.py`
- Modify: `tests/test_preproc_tools.py`

**Acceptance Criteria:**
- [ ] Formats XML with 2-space indent
- [ ] Normalizes attribute values (comma spacing, brace spacing)
- [ ] Preserves SymbolicFunction/CompositeFunction expressions
- [ ] Overwrites input when output_path is empty
- [ ] Writes to output_path when provided
- [ ] Tests pass

**Verify:** `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

Add to `tests/test_preproc_tools.py`:

```python
from agents4geosx.tools.preproc_tools import (
    convert_units, expand_parameters, resolve_includes, format_xml,
)


class TestFormatXml:
    def test_basic_formatting(self, tmp_output):
        input_path = tmp_output / "messy.xml"
        output_path = tmp_output / "clean.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Solvers>'
            '<SinglePhaseFVM name="flow" targetRegions="{Domain}"/>'
            '</Solvers></Problem>\n'
        )
        result = format_xml(str(input_path), str(output_path))
        assert result["output"] == str(output_path)
        content = output_path.read_text()
        # Should have indentation
        assert "  <Solvers>" in content or "  <Solvers" in content
        # Should normalize braces
        assert "{ Domain }" in content

    def test_overwrite_input(self, tmp_output):
        input_path = tmp_output / "sim.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Mesh/></Problem>\n'
        )
        result = format_xml(str(input_path))
        assert result["output"] == str(input_path)

    def test_comma_spacing(self, tmp_output):
        input_path = tmp_output / "commas.xml"
        output_path = tmp_output / "commas_out.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Geometry>'
            '<Box name="all" xMin="{-1,-1,-1}" xMax="{101,101,101}"/>'
            '</Geometry></Problem>\n'
        )
        result = format_xml(str(input_path), str(output_path))
        content = output_path.read_text()
        assert "{ -1, -1, -1 }" in content
        assert "{ 101, 101, 101 }" in content

    def test_protected_expression_preserved(self, tmp_output):
        input_path = tmp_output / "symbolic.xml"
        output_path = tmp_output / "symbolic_out.xml"
        input_path.write_text(
            '<?xml version="1.0"?>\n'
            '<Problem><Functions>'
            '<SymbolicFunction name="f1" expression="x^2 + y^2"/>'
            '</Functions></Problem>\n'
        )
        result = format_xml(str(input_path), str(output_path))
        content = output_path.read_text()
        assert 'expression="x^2 + y^2"' in content
        assert result["protected_expressions_preserved"] >= 1

    def test_nonexistent_file(self):
        result = format_xml("/nonexistent/path.xml")
        assert "error" in result
```

- [ ] **Step 2: Write implementation**

Add to `src/agents4geosx/tools/preproc_tools.py`:

```python
from pathlib import Path
from agents4geosx.knowledge.formatting_conventions import (
    DEFAULT_FORMAT,
    ATTRIBUTE_FORMATTING,
    PROTECTED_EXPRESSIONS,
)


@mcp.tool
def format_xml(input_path: str, output_path: str = "") -> dict:
    """Format a GEOS XML file to match canonical geos-xml-tools style.

    Applies 2-space indentation, attribute value normalization (comma and
    brace spacing), and preserves protected expressions (SymbolicFunction,
    CompositeFunction).

    Args:
        input_path: Path to the XML file to format
        output_path: Path to write formatted output (empty = overwrite input)
    """
    if not Path(input_path).exists():
        return {"error": f"File not found: {input_path}"}

    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(input_path, parser)
        root = tree.getroot()
    except Exception as exc:
        return {"error": f"Failed to parse XML: {exc}"}

    protected_count = _normalize_attributes(root)

    out = output_path if output_path else input_path
    indent = DEFAULT_FORMAT["indent"]
    _indent_tree(root, level=0, indent_str=" " * indent)

    tree.write(
        out,
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=False,  # We handle indentation ourselves
    )
    # lxml writes bytes — re-read and write as clean text
    content = Path(out).read_bytes().decode("utf-8")
    Path(out).write_text(content)

    return {
        "input": input_path,
        "output": out,
        "format_applied": DEFAULT_FORMAT,
        "protected_expressions_preserved": protected_count,
    }


def _normalize_attributes(el, depth: int = 0) -> int:
    """Normalize attribute values and protect special expressions."""
    protected_set = {
        (p["element"], p["attribute"]) for p in PROTECTED_EXPRESSIONS
    }
    protected_count = 0

    tag = el.tag if isinstance(el.tag, str) else ""

    for attr_name in list(el.attrib.keys()):
        if (tag, attr_name) in protected_set:
            protected_count += 1
            continue
        value = el.get(attr_name)
        for rule_name in ("comma_spacing", "brace_opening", "brace_closing",
                          "whitespace_consolidation"):
            rule = ATTRIBUTE_FORMATTING[rule_name]
            value = re.sub(rule["pattern"], rule["replacement"], value)
        el.set(attr_name, value)

    for child in el:
        protected_count += _normalize_attributes(child, depth + 1)
    return protected_count


def _indent_tree(elem, level: int = 0, indent_str: str = "  ") -> None:
    """Add indentation whitespace to an lxml element tree."""
    indent = "\n" + indent_str * level
    child_indent = "\n" + indent_str * (level + 1)

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_indent
        for i, child in enumerate(elem):
            _indent_tree(child, level + 1, indent_str)
            if not child.tail or not child.tail.strip():
                child.tail = child_indent if i < len(elem) - 1 else indent
    if not elem.tail or not elem.tail.strip():
        elem.tail = indent if level > 0 else "\n"
```

- [ ] **Step 3: Run tests**

Run: `cd ~/codes/agents4geosx && uv run pytest tests/test_preproc_tools.py -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
cd ~/codes/agents4geosx
git add src/agents4geosx/tools/preproc_tools.py tests/test_preproc_tools.py
git commit -m "feat: add format_xml MCP tool

Formats XML with 2-space indent, normalizes attribute values (comma
and brace spacing), preserves SymbolicFunction/CompositeFunction
expression attributes."
```

---

### Task 5: Update AGENTS.md and README.md with new tools

**Goal:** Add the 4 new tools to the tool inventory and update counts.

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`

**Acceptance Criteria:**
- [ ] AGENTS.md Section 4 has new "Preprocessing" group with 4 tools
- [ ] AGENTS.md tool count updated (48 → 52)
- [ ] README.md tool count updated (48 → 52)
- [ ] README.md tool groups table updated with Preprocessing row

**Verify:** `grep -c "52" AGENTS.md README.md`

**Steps:**

- [ ] **Step 1: Add Preprocessing group to AGENTS.md Section 4**

After the "Utility" group, add:

```markdown
### Preprocessing (4 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `convert_units` | Parse GEOS bracket notation, convert to SI | fluids, geos, edit |
| `expand_parameters` | Resolve $Name$ patterns from Parameters section | edit, inspect, geos |
| `resolve_includes` | Merge <Included> file blocks into document | edit, inspect, validate |
| `format_xml` | Format XML to canonical geos-xml-tools style | edit, geos |
```

Update the header from "47 MCP tools + `health_check`" to "51 MCP tools + `health_check`".

- [ ] **Step 2: Update README.md**

Update architecture diagram tool count from 48 to 52. Add Preprocessing row to tool groups table:

```markdown
| **Preprocessing** | 4 | Knowledge modules | Unit conversion, parameter expansion, include resolution, XML formatting |
```

- [ ] **Step 3: Commit**

```bash
cd ~/codes/agents4geosx
git add AGENTS.md README.md
git commit -m "docs: add preprocessing tools to AGENTS.md and README.md (48→52 tools)"
```
