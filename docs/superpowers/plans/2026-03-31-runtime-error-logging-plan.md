# Runtime Error Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture GEOS runtime errors with full context (solver, constitutive, error, fix) into a structured log, and provide curated lessons that agents read before making decisions.

**Architecture:** An MCP tool (`log_runtime_error`) extracts solver/constitutive context from the in-memory document and appends to a JSONL log. A curated `lessons_learned.md` file is the agent's primary reference. The `geos:run` skill enforces logging after failures.

**Tech Stack:** Python (MCP tool), JSONL (raw log), Markdown (curated lessons), skill files (agent instructions)

**User Verification:** NO — no user verification required (manual testing by user is separate from plan execution)

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `knowledge/lessons_learned.md` | Create | Curated lessons — agent reads before decisions |
| `src/agents4geosx/tools/xml_tools.py` | Modify | Add `log_runtime_error` MCP tool |
| `tests/test_xml_tools.py` | Modify | Add tests for `log_runtime_error` |
| `skills/geos:run.md` | Modify | Replace hardcoded tips with lessons_learned + logging rules |
| `skills/geos:curate-errors.md` | Create | Slash command for curating raw logs into lessons |
| `.gitignore` | Modify | Add `knowledge/runtime_errors.jsonl` |

---

### Task 0: Create `knowledge/lessons_learned.md` with seed content

**Goal:** Create the curated lessons file with the 5 seed lessons migrated from the current `geos:run` skill and today's session.

**Files:**
- Create: `knowledge/lessons_learned.md`

**Acceptance Criteria:**
- [ ] File exists with all 5 seed lessons
- [ ] Each lesson follows the template: title, Wrong, Right, Pattern (XML), Source
- [ ] Sections: Solver-Constitutive Compatibility, FieldSpecification Rules, NumericalMethods Rules, Mesh and Geometry Rules

**Verify:** `cat knowledge/lessons_learned.md | head -20` → shows header and first lesson

**Steps:**

- [ ] **Step 1: Create the file**

```markdown
# GEOS Runtime Lessons Learned

Read this file BEFORE choosing solver/constitutive combinations or setting up
FieldSpecifications. Each lesson documents a real runtime failure and the
correct pattern to avoid it.

---

## Solver-Constitutive Compatibility

### ImmiscibleMultiphaseFlow requires TwoPhaseImmiscibleFluid
- **Wrong:** Using `InvariantImmiscibleFluid` — different C++ class, not found by `dynamic_cast`
- **Right:** `TwoPhaseImmiscibleFluid` with `TableFunction` references for density/viscosity per phase
- **Pattern:**
  ```xml
  <TwoPhaseImmiscibleFluid name="fluid"
    phaseNames="{ gas, water }"
    densityTableNames="{ gasDensityTable, waterDensityTable }"
    viscosityTableNames="{ gasViscosityTable, waterViscosityTable }"/>
  ```
- **Source:** Runtime error — `constitutive model not found` in `ImmiscibleMultiphaseFlow`

### Every CellElementRegion materialList must include a coupled solid
- **Wrong:** `materialList="{ fluid, relperm }"` — missing coupled solid
- **Right:** Always include a `CompressibleSolidConstantPermeability` (or similar) in `materialList`
- **Pattern:**
  ```xml
  <CellElementRegion name="Domain"
    cellBlocks="{ cb1 }"
    materialList="{ fluid, rock, relperm }"/>

  <CompressibleSolidConstantPermeability name="rock"
    solidModelName="nullSolid"
    porosityModelName="rockPorosity"
    permeabilityModelName="rockPerm"/>
  ```
- **Source:** Runtime error — `coupled solid constitutive model not found`

## FieldSpecification Rules

### ImmiscibleMultiphaseFlow uses phaseVolumeFraction, not globalCompFraction
- **Wrong:** Setting `fieldName="globalCompFraction"` with `ImmiscibleMultiphaseFlow`
- **Right:** Use `fieldName="phaseVolumeFraction"` — immiscible solver tracks phase volumes, not component moles
- **Pattern:**
  ```xml
  <FieldSpecification name="initialGasSaturation"
    fieldName="phaseVolumeFraction"
    component="0"
    initialCondition="1"
    setNames="{ all }"
    scale="0.5"/>
  ```
- **Source:** Runtime error — field `globalCompFraction` not found on `ImmiscibleMultiphaseFlow`

### Component fractions must sum to 1.0 per region
- **Wrong:** Setting `globalCompFraction` for only one component, or fractions that don't sum to 1
- **Right:** One `FieldSpecification` per component, with `scale` values summing to 1.0 on each `setNames` group
- **Pattern:**
  ```xml
  <FieldSpecification name="initComp_co2" fieldName="globalCompFraction"
    component="0" initialCondition="1" setNames="{ all }" scale="0.1"/>
  <FieldSpecification name="initComp_water" fieldName="globalCompFraction"
    component="1" initialCondition="1" setNames="{ all }" scale="0.9"/>
  ```
- **Source:** Runtime error — `component fractions do not sum to 1`

## Mesh and Geometry Rules

### Geometry box must enclose cell centers, not just boundaries
- **Wrong:** A `Box` geometry with `xMax` exactly at the mesh boundary — misses cell centers
- **Right:** Extend the box by half a cell width past the boundary to capture cell centers
- **Pattern:**
  ```xml
  <!-- For a mesh with dx=10m and xMax=100m, use xMax=105 to capture the last column -->
  <Box name="rightFace" xMin="{ 95, -1, -1 }" xMax="{ 105, 1001, 1001 }"/>
  ```
- **Source:** Runtime error — `targets empty set` (geometry box doesn't enclose cell centers)

## NumericalMethods Rules

(No runtime lessons yet — add here as discovered.)
```

Write this to `knowledge/lessons_learned.md`.

- [ ] **Step 2: Commit**

```bash
git add knowledge/lessons_learned.md
git commit -m "feat: add lessons_learned.md with 5 seed lessons from runtime errors"
```

---

### Task 1: Implement `log_runtime_error` MCP tool

**Goal:** Add the MCP tool that extracts solver/constitutive context from a document and appends a structured JSONL entry.

**Files:**
- Modify: `src/agents4geosx/tools/xml_tools.py` (add tool at end of file)
- Modify: `tests/test_xml_tools.py` (add tests)

**Acceptance Criteria:**
- [ ] Tool extracts solvers and constitutive types from document
- [ ] Tool appends valid JSONL to `knowledge/runtime_errors.jsonl`
- [ ] Tool creates the log file if it doesn't exist
- [ ] Tool returns the logged entry for confirmation
- [ ] Tests pass

**Verify:** `cd /home/adriano/codes/agents4geosx && uv run pytest tests/test_xml_tools.py -v -k log_runtime` → PASS

**Steps:**

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_xml_tools.py`:

```python
import json
import tempfile
import os

def test_log_runtime_error(tmp_path, monkeypatch):
    """log_runtime_error extracts solver/constitutive from doc and appends JSONL."""
    from agents4geosx.tools.xml_tools import create_document, add_element, log_runtime_error

    # Point the log to a temp dir
    log_file = tmp_path / "runtime_errors.jsonl"
    monkeypatch.setenv("AGENTS4GEOSX_ERROR_LOG", str(log_file))

    doc = create_document(template="single_phase_flow")
    doc_id = doc["doc_id"]

    result = log_runtime_error(
        doc_id=doc_id,
        geos_error="***** ABORT: constitutive model not found",
        error_summary="SinglePhaseFVM requires CompressibleSinglePhaseFluid",
        fix_applied="Added CompressibleSinglePhaseFluid to Constitutive section",
    )
    assert result["logged"] is True
    entry = result["entry"]
    assert "SinglePhaseFVM" in entry["solvers"]
    assert "CompressibleSinglePhaseFluid" in entry["constitutive_types"]
    assert entry["error_summary"] == "SinglePhaseFVM requires CompressibleSinglePhaseFluid"
    assert entry["fix_applied"] == "Added CompressibleSinglePhaseFluid to Constitutive section"
    assert "timestamp" in entry

    # Verify JSONL was written
    assert log_file.exists()
    with open(log_file) as f:
        line = f.readline()
        parsed = json.loads(line)
        assert parsed["error_summary"] == entry["error_summary"]


def test_log_runtime_error_appends(tmp_path, monkeypatch):
    """Multiple calls append separate lines."""
    from agents4geosx.tools.xml_tools import create_document, log_runtime_error

    log_file = tmp_path / "runtime_errors.jsonl"
    monkeypatch.setenv("AGENTS4GEOSX_ERROR_LOG", str(log_file))

    doc = create_document(template="single_phase_flow")
    doc_id = doc["doc_id"]

    log_runtime_error(doc_id=doc_id, geos_error="error1",
                      error_summary="first", fix_applied="fix1")
    log_runtime_error(doc_id=doc_id, geos_error="error2",
                      error_summary="second", fix_applied="fix2")

    with open(log_file) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["error_summary"] == "first"
    assert json.loads(lines[1])["error_summary"] == "second"


def test_log_runtime_error_invalid_doc():
    """Returns error for invalid doc_id."""
    from agents4geosx.tools.xml_tools import log_runtime_error

    result = log_runtime_error(
        doc_id="nonexistent",
        geos_error="some error",
        error_summary="summary",
        fix_applied="fix",
    )
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/adriano/codes/agents4geosx && uv run pytest tests/test_xml_tools.py -v -k log_runtime`
Expected: FAIL with `ImportError` (log_runtime_error not defined)

- [ ] **Step 3: Implement the tool**

Add to the end of `src/agents4geosx/tools/xml_tools.py`:

```python
import json
import os
from datetime import datetime, timezone


@mcp.tool
def log_runtime_error(
    doc_id: str,
    geos_error: str,
    error_summary: str,
    fix_applied: str,
) -> dict:
    """Log a GEOS runtime error with full context for future learning.

    Call this AFTER diagnosing and fixing (or failing to fix) a GEOS runtime error.
    Extracts solver and constitutive types from the document automatically.

    Args:
        doc_id: Document ID of the XML that caused the error.
        geos_error: Raw GEOS error text (copy the relevant lines).
        error_summary: Your one-line diagnosis of what went wrong.
        fix_applied: What resolved the issue, or "UNRESOLVED" if unfixed after 3 attempts.
    """
    doc = _store.get(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found"}

    # Extract context from document
    xml_file = doc.source_path.name if doc.source_path else "unknown"
    solvers = []
    constitutive_types = []
    for section in doc.root.children:
        sec_name = section.schema_element.name
        if sec_name == "Solvers":
            for child in section.children:
                solvers.append(child.schema_element.name)
        elif sec_name == "Constitutive":
            for child in section.children:
                constitutive_types.append(child.schema_element.name)

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "xml_file": xml_file,
        "solvers": solvers,
        "constitutive_types": constitutive_types,
        "geos_error": geos_error,
        "error_summary": error_summary,
        "fix_applied": fix_applied,
    }

    # Append to JSONL log
    log_path = os.environ.get(
        "AGENTS4GEOSX_ERROR_LOG",
        str(Path(__file__).resolve().parent.parent.parent.parent / "knowledge" / "runtime_errors.jsonl"),
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"logged": True, "entry": entry, "log_file": log_path}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/adriano/codes/agents4geosx && uv run pytest tests/test_xml_tools.py -v -k log_runtime`
Expected: 3 PASSED

- [ ] **Step 5: Run full xml_tools test suite**

Run: `cd /home/adriano/codes/agents4geosx && uv run pytest tests/test_xml_tools.py tests/test_integration.py -v`
Expected: All pass (no regressions)

- [ ] **Step 6: Commit**

```bash
git add src/agents4geosx/tools/xml_tools.py tests/test_xml_tools.py
git commit -m "feat: add log_runtime_error MCP tool for capturing GEOS runtime failures"
```

---

### Task 2: Update `geos:run` skill and create `geos:curate-errors` skill

**Goal:** Update agent instructions so failures are logged and lessons are consulted.

**Files:**
- Modify: `skills/geos:run.md`
- Create: `skills/geos:curate-errors.md`

**Acceptance Criteria:**
- [ ] `geos:run` no longer has hardcoded "common issues" list
- [ ] `geos:run` instructs agent to read `lessons_learned.md` before running
- [ ] `geos:run` instructs agent to call `log_runtime_error` after failed runs
- [ ] `geos:curate-errors` skill exists with complete curation workflow

**Verify:** `grep -c "lessons_learned" skills/geos:run.md` → at least 1; `test -f skills/geos:curate-errors.md` → success

**Steps:**

- [ ] **Step 1: Rewrite `skills/geos:run.md`**

Replace the full file with:

```markdown
---
name: geos:run
description: Run a GEOS simulation and analyze the output.
---

CRITICAL: Use ONLY the `agents4geosx` MCP tools for post-processing. Use Bash ONLY for the GEOS run itself.

## Before Running

1. **Read lessons learned** — check `knowledge/lessons_learned.md` for known
   solver/constitutive compatibility rules that apply to your XML. This avoids
   repeat failures that previous runs have already diagnosed.

2. **Verify the XML** before running:
   ```
   /geos:validate <file.xml>
   ```

## Running GEOS

Run via Bash (this is the one place Bash is appropriate):
```bash
cd <run_directory>
geos/build/bin/geosx -i <file.xml>
```

## After a Failed Run

If `geosx -i` exits with a non-zero code:
1. Diagnose and fix the issue
2. Re-run to confirm the fix works
3. Call `log_runtime_error` with the full context: the GEOS error text,
   your one-line diagnosis, and what fix resolved it

If the fix fails after 3 attempts, call `log_runtime_error` anyway with
fix_applied="UNRESOLVED" so the error is captured for future curation.

This logging step is NOT optional. It captures your understanding of what
went wrong while the context is fresh.

## After a Successful Run

1. **Locate the VTK output** (usually in `vtkOutput/` subdirectory):
   ```bash
   find . -name "*.vtu" | head -5
   ```

2. **Analyze with MCP tools** (use ABSOLUTE paths):
   - `read_vtk_output(path)` → list available fields
   - `extract_field(path, field_name)` → statistics
   - `screenshot_field(path, field_name, title="...", output_path="...")` → publication-quality figure
   - `compute_darcy_velocity(path, permeability_m2, viscosity_Pa_s)` → derive velocity from pressure
   - `compare_timesteps(file_paths, field_name)` → time evolution

## Tips
- GEOS VTK output structure: `vtkOutput/<timestep>/mesh/Level0/<region>/rank_0.vtu`
- Use `ls vtkOutput/` to see timestep directories (000000, 000001, etc.)
- The last timestep directory has the final state
- Always provide a descriptive `title` for screenshots (e.g., "Pressure at t=1yr [Pa]")
```

- [ ] **Step 2: Create `skills/geos:curate-errors.md`**

```markdown
---
name: geos:curate-errors
description: Curate raw runtime error logs into lessons_learned.md entries.
---

## Workflow

1. **Read the raw log:**
   Read `knowledge/runtime_errors.jsonl`. If the file doesn't exist or is empty,
   report "No runtime errors logged yet" and stop.

2. **Group and deduplicate:**
   Group entries by `error_summary`. Count occurrences of each unique error.
   Sort by frequency (most common first).

3. **Check against existing lessons:**
   Read `knowledge/lessons_learned.md`. For each unique error, check if a lesson
   already covers it (search for key phrases from the error_summary).

4. **Propose new lessons:**
   For each unique error NOT already in lessons_learned.md, draft a new lesson
   using this template:

   ```markdown
   ### <Short rule title derived from error_summary>
   - **Wrong:** <what caused the failure, from the log context>
   - **Right:** <what GEOS actually needs, from fix_applied>
   - **Pattern:**
     ```xml
     <correct XML snippet based on the fix>
     ```
   - **Source:** <the geos_error text>
   ```

5. **Present to user:**
   Show each proposed lesson and ask the user to approve, edit, or skip it.

6. **On approval:**
   Append approved lessons to the appropriate section in `knowledge/lessons_learned.md`.
   Commit the updated file.

7. **Optionally truncate:**
   After curation, ask the user if they want to clear the processed entries
   from `runtime_errors.jsonl`.
```

- [ ] **Step 3: Commit**

```bash
git add skills/geos:run.md skills/geos:curate-errors.md
git commit -m "feat: update geos:run with lessons_learned integration and add curate-errors skill"
```

---

### Task 3: Update `.gitignore` and verify end-to-end

**Goal:** Ensure the raw JSONL is gitignored and the full flow works.

**Files:**
- Modify: `.gitignore`

**Acceptance Criteria:**
- [ ] `knowledge/runtime_errors.jsonl` is in `.gitignore`
- [ ] `knowledge/lessons_learned.md` is NOT in `.gitignore` (it's shared)
- [ ] Full test suite passes

**Verify:** `cd /home/adriano/codes/agents4geosx && uv run pytest tests/ -v` → all pass

**Steps:**

- [ ] **Step 1: Add to `.gitignore`**

Append to `.gitignore`:

```
knowledge/runtime_errors.jsonl
```

- [ ] **Step 2: Run full test suite**

Run: `cd /home/adriano/codes/agents4geosx && uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore runtime_errors.jsonl (per-user raw log)"
```
