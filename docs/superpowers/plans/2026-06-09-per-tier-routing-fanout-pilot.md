# Per-Tier Routing Fan-out Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `geos:mesh` and `geos:fluids` into real dispatched subagents (`model: sonnet`) that the orchestrator fans out concurrently during a build, computing mesh/fluid results in parallel and composing them — the first Tier-2 real subagents (`agents4geos-cw7`).

**Architecture:** Two compute-and-return advisor subagents (no `DocumentStore` mutation) return structured `MeshResult`/`FluidResult` JSON validated by a deterministic contract module; the orchestrator (Opus) dispatches both in one turn, validates, and serially applies the results, falling back to inline compute on failure. Stage C runs before the existing Stage R reviewer.

**Tech Stack:** Claude Code subagents + Agent tool, agents4geos MCP server (FastMCP), Python 3.11 + pytest for the result contract. Spec: `docs/superpowers/specs/2026-06-09-per-tier-routing-fanout-pilot-design.md`.

**Cold-start prerequisites (read before Task 1):**
- Work in an isolated worktree/branch (see `superpowers:using-git-worktrees`). This repo enforces worktree isolation for edits.
- Run tests with `uv run pytest` (run `uv sync --all-extras` first if pytest is missing). The bundled schema cache makes a GEOS build unnecessary.
- Tasks 1–6 + 8 are deterministic (files + unit tests) and run in any session. Task 7 is a **live agent-run gate** needing the `agents4geos` MCP server registered and the subagents deployed — defer it to a `/geos`-capable session if the current one lacks the server (record it as PENDING, do not fabricate).
- Beads issue: `agents4geos-cw7` (claim it). Reviewer precedent to mirror: `.claude/agents/geos-reviewer.md`, `src/agents4geos/review/findings.py`, `tests/review/`.

---

### Task 1: Canonical result contracts (deterministic, TDD)

The two subagents return JSON; this module is the single source of truth for those shapes and the orchestrator's validation guard. Pure Python, fully unit-tested. Mirrors `src/agents4geos/review/findings.py`.

**Files:**
- Create: `src/agents4geos/dispatch/__init__.py`
- Create: `src/agents4geos/dispatch/results.py`
- Test: `tests/dispatch/__init__.py`, `tests/dispatch/test_results.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/dispatch/__init__.py` (empty), then `tests/dispatch/test_results.py`:

```python
import pytest
from agents4geos.dispatch.results import (
    FluidResult, MeshResult, ConstitutiveSpec,
    parse_fluid_result, parse_mesh_result, MESH_KINDS, INTERNAL_MESH_KEYS,
)


def _fluid_dict():
    return {
        "model_type": "CO2BrinePhillipsFluid",
        "constitutive": [
            {"element_type": "CO2BrinePhillipsFluid", "name": "fluid",
             "attributes": {"phasePVTParaFiles": "{ pvtgas.txt, pvtliquid.txt }"}}
        ],
        "pvt_table_paths": ["pvtgas.txt"],
        "notes": "Phillips: salinity below Ezrokhi threshold",
    }


def _internal_mesh_dict():
    return {
        "mesh_kind": "internal",
        "internal_mesh": {"xCoords": "{ 0, 100 }", "yCoords": "{ 0, 100 }",
                          "zCoords": "{ 0, 100 }", "nx": "{ 10 }", "ny": "{ 10 }",
                          "nz": "{ 10 }", "elementTypes": "{ C3D8 }"},
        "stats": {"n_cells": 1000},
        "notes": "100 m cube",
    }


def test_parse_fluid_result_roundtrip():
    fr = parse_fluid_result(_fluid_dict())
    assert isinstance(fr, FluidResult)
    assert fr.model_type == "CO2BrinePhillipsFluid"
    assert len(fr.constitutive) == 1
    assert isinstance(fr.constitutive[0], ConstitutiveSpec)
    assert fr.constitutive[0].name == "fluid"
    assert fr.pvt_table_paths == ["pvtgas.txt"]


def test_fluid_missing_model_type_raises():
    d = _fluid_dict(); del d["model_type"]
    with pytest.raises(ValueError):
        parse_fluid_result(d)


def test_fluid_constitutive_not_list_raises():
    d = _fluid_dict(); d["constitutive"] = {"element_type": "x"}
    with pytest.raises(ValueError):
        parse_fluid_result(d)


def test_fluid_constitutive_item_missing_keys_raises():
    d = _fluid_dict(); del d["constitutive"][0]["attributes"]
    with pytest.raises(ValueError):
        parse_fluid_result(d)


def test_fluid_defaults_when_optional_absent():
    d = _fluid_dict(); del d["pvt_table_paths"]; del d["notes"]
    fr = parse_fluid_result(d)
    assert fr.pvt_table_paths == [] and fr.notes == ""


def test_parse_mesh_internal_roundtrip():
    mr = parse_mesh_result(_internal_mesh_dict())
    assert isinstance(mr, MeshResult)
    assert mr.is_internal and not mr.is_vtk
    assert mr.internal_mesh["nx"] == "{ 10 }"
    assert mr.stats["n_cells"] == 1000


def test_mesh_internal_missing_a_key_raises():
    d = _internal_mesh_dict(); del d["internal_mesh"]["nz"]
    with pytest.raises(ValueError):
        parse_mesh_result(d)


def test_parse_mesh_vtk_roundtrip():
    mr = parse_mesh_result({"mesh_kind": "vtk", "vtk_path": "/tmp/mesh.vtu",
                            "stats": {"n_cells": 50}})
    assert mr.is_vtk and not mr.is_internal
    assert mr.vtk_path == "/tmp/mesh.vtu"


def test_mesh_vtk_missing_path_raises():
    with pytest.raises(ValueError):
        parse_mesh_result({"mesh_kind": "vtk"})


def test_mesh_unknown_kind_raises():
    with pytest.raises(ValueError):
        parse_mesh_result({"mesh_kind": "octree"})


def test_mesh_missing_kind_raises():
    with pytest.raises(ValueError):
        parse_mesh_result({"internal_mesh": {}})


def test_constants_exposed():
    assert MESH_KINDS == ("internal", "vtk")
    assert "elementTypes" in INTERNAL_MESH_KEYS
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/dispatch/test_results.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents4geos.dispatch'`.

- [ ] **Step 3: Implement the module**

Create `src/agents4geos/dispatch/__init__.py` (empty), then `src/agents4geos/dispatch/results.py`:

```python
"""Structured results returned by dispatched compute subagents (geos-mesh, geos-fluids).

This is the contract between the fan-out subagents and the orchestrator: each
subagent returns a JSON object that the orchestrator validates here before applying
it to the document. Mirrors src/agents4geos/review/findings.py (the reviewer seam).
See docs/superpowers/specs/2026-06-09-per-tier-routing-fanout-pilot-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MESH_KINDS = ("internal", "vtk")
INTERNAL_MESH_KEYS = (
    "xCoords", "yCoords", "zCoords", "nx", "ny", "nz", "elementTypes",
)


@dataclass(frozen=True)
class ConstitutiveSpec:
    element_type: str
    name: str
    attributes: dict


@dataclass(frozen=True)
class FluidResult:
    model_type: str
    constitutive: list[ConstitutiveSpec]
    pvt_table_paths: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class MeshResult:
    mesh_kind: str
    internal_mesh: dict | None = None
    vtk_path: str | None = None
    stats: dict = field(default_factory=dict)
    notes: str = ""

    @property
    def is_internal(self) -> bool:
        return self.mesh_kind == "internal"

    @property
    def is_vtk(self) -> bool:
        return self.mesh_kind == "vtk"


def parse_fluid_result(d: dict) -> FluidResult:
    """Validate and parse a geos-fluids JSON result. Raises ValueError on bad shape."""
    missing = {"model_type", "constitutive"} - d.keys()
    if missing:
        raise ValueError(f"FluidResult missing keys: {sorted(missing)}")
    if not isinstance(d["constitutive"], list):
        raise ValueError("FluidResult 'constitutive' must be a list")
    specs: list[ConstitutiveSpec] = []
    for i, item in enumerate(d["constitutive"]):
        cmissing = {"element_type", "name", "attributes"} - item.keys()
        if cmissing:
            raise ValueError(f"constitutive[{i}] missing keys: {sorted(cmissing)}")
        specs.append(
            ConstitutiveSpec(item["element_type"], item["name"], item["attributes"])
        )
    return FluidResult(
        model_type=d["model_type"],
        constitutive=specs,
        pvt_table_paths=d.get("pvt_table_paths", []),
        notes=d.get("notes", ""),
    )


def parse_mesh_result(d: dict) -> MeshResult:
    """Validate and parse a geos-mesh JSON result. Raises ValueError on bad shape."""
    if "mesh_kind" not in d:
        raise ValueError("MeshResult missing key: 'mesh_kind'")
    kind = d["mesh_kind"]
    if kind not in MESH_KINDS:
        raise ValueError(f"invalid mesh_kind {kind!r}; expected one of {MESH_KINDS}")
    if kind == "internal":
        im = d.get("internal_mesh")
        if not isinstance(im, dict):
            raise ValueError("mesh_kind 'internal' requires an 'internal_mesh' dict")
        imissing = set(INTERNAL_MESH_KEYS) - im.keys()
        if imissing:
            raise ValueError(f"internal_mesh missing keys: {sorted(imissing)}")
    else:  # vtk
        if not d.get("vtk_path"):
            raise ValueError("mesh_kind 'vtk' requires a 'vtk_path'")
    return MeshResult(
        mesh_kind=kind,
        internal_mesh=d.get("internal_mesh"),
        vtk_path=d.get("vtk_path"),
        stats=d.get("stats", {}),
        notes=d.get("notes", ""),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/dispatch/test_results.py -q`
Expected: PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add src/agents4geos/dispatch/ tests/dispatch/
git commit -m "feat(dispatch): MeshResult/FluidResult contracts + validators (TDD, cw7)"
```

---

### Task 2: `geos-fluids` subagent definition

A real Claude Code subagent (`model: sonnet`) that computes the fluid-phase constitutive model for a chosen catalog category and returns a `FluidResult` JSON.

**Files:**
- Create: `.claude/agents/geos-fluids.md`

- [ ] **Step 1: Create the file**

Create `.claude/agents/geos-fluids.md`:

```markdown
---
name: geos-fluids
description: Compute fluid-phase constitutive model(s) and PVT data for a chosen fluid category and return structured JSON. Tier-2 compute-and-return subagent dispatched by the geos orchestrator; not user-invocable.
model: sonnet
tools: Read, mcp__agents4geos__recommend_fluid_model, mcp__agents4geos__compute_gas_properties, mcp__agents4geos__compute_oil_properties, mcp__agents4geos__compute_brine_properties, mcp__agents4geos__generate_pvt_table
---

You are the `geos-fluids` compute subagent. You COMPUTE the fluid-phase constitutive
model(s) and PVT data for a fluid category, and RETURN structured JSON. You do not
edit any document — you have no editing tools; the orchestrator assembles your result.

## Inputs you are given
- A catalog CATEGORY chosen by the orchestrator (e.g. "CO₂-brine", "single-phase
  flow", "black oil").
- Conditions: components, temperature, pressure, salinity, etc.
- The workspace absolute path.

## What to do
1. `Read` the per-family detail file
   `src/agents4geos/knowledge/examples/<category>.md` (map the category to its file,
   e.g. CO₂-brine → `co2_brine.md`, single-phase flow → `single_phase_flow.md`,
   black oil → `black_oil.md`). It lists the sibling VARIANTS, the
   `## Decision rule (stage 2)`, and the constitutive assembly specifics (required
   attributes, `phasePVTParaFiles`, PVT tables).
2. Pick the VARIANT using that decision rule and the conditions (e.g. CO₂-brine
   Phillips vs. Ezrokhi by salinity).
3. Compute properties as needed with your tools: `recommend_fluid_model`,
   `compute_gas_properties`, `compute_oil_properties`, `compute_brine_properties`,
   `generate_pvt_table`.
4. Assemble the fluid-phase constitutive model(s) — element type, name, attributes.
   Do NOT emit the solid / porosity / permeability models or `materialList` (the
   orchestrator wires those); you MAY name a recommended coupled solid in `notes`.

## Output — STRUCTURED JSON ONLY
Return one JSON object (and nothing else):
{
  "model_type": "<fluid element type, e.g. CO2BrinePhillipsFluid>",
  "constitutive": [
    {"element_type": "<e.g. CO2BrinePhillipsFluid>", "name": "<e.g. fluid>",
     "attributes": { ... }}
  ],
  "pvt_table_paths": [ ... ],
  "notes": "<variant rationale + any recommended coupled solid>"
}
Use `pvt_table_paths: []` if there are none. Do NOT write prose outside the JSON.
Do NOT edit the deck.
```

- [ ] **Step 2: Verify the frontmatter parses**

Run: `uv run python -c "import re,sys; t=open('.claude/agents/geos-fluids.md').read(); fm=re.match(r'^---\n(.*?)\n---\n', t, re.S); print('OK' if fm and 'model: sonnet' in fm.group(1) and 'mcp__agents4geos__generate_pvt_table' in fm.group(1) else 'BROKEN'); sys.exit(0 if fm else 1)"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/geos-fluids.md
git commit -m "feat(routing): geos-fluids compute-and-return subagent (model: sonnet, cw7)"
```

---

### Task 3: `geos-mesh` subagent definition

A real Claude Code subagent (`model: sonnet`) that computes a mesh for a domain spec and returns a `MeshResult` JSON.

**Files:**
- Create: `.claude/agents/geos-mesh.md`

- [ ] **Step 1: Create the file**

Create `.claude/agents/geos-mesh.md`:

```markdown
---
name: geos-mesh
description: Compute a mesh (native InternalMesh parameters or a generated VTK file) for a domain spec and return structured JSON. Tier-2 compute-and-return subagent dispatched by the geos orchestrator; not user-invocable.
model: sonnet
tools: Read, mcp__agents4geos__suggest_mesh_resolution, mcp__agents4geos__generate_internal_mesh_xml, mcp__agents4geos__create_structured_mesh, mcp__agents4geos__create_rectilinear_mesh, mcp__agents4geos__mesh_statistics, mcp__agents4geos__define_geometry_box, mcp__agents4geos__screenshot_mesh, mcp__agents4geos__load_mesh
---

You are the `geos-mesh` compute subagent. You COMPUTE a mesh for a domain spec and
RETURN structured JSON. You do not edit any document — you have no editing tools;
the orchestrator assembles your result.

## Inputs you are given
- A geometry/domain spec: extents (e.g. "100 m cube"), target resolution, and
  whether a structured native mesh or a generated VTK mesh is wanted.
- The workspace absolute path.

## What to do
1. If no target resolution is given, call `suggest_mesh_resolution`.
2. For a structured box domain, prefer a native GEOS `InternalMesh`: produce the
   mesh parameters (`xCoords`/`yCoords`/`zCoords`/`nx`/`ny`/`nz`/`elementTypes`).
   You may call `generate_internal_mesh_xml` to sanity-check, but RETURN the
   parameters, not raw XML.
3. If a VTK mesh is requested or needed, write one with `create_structured_mesh` /
   `create_rectilinear_mesh`, get `mesh_statistics`, and return `mesh_kind: "vtk"`
   with the absolute file path.

## Output — STRUCTURED JSON ONLY
Return one JSON object (and nothing else). For a native mesh:
{ "mesh_kind": "internal",
  "internal_mesh": {"xCoords": "{ 0, 100 }", "yCoords": "{ 0, 100 }",
                    "zCoords": "{ 0, 100 }", "nx": "{ 10 }", "ny": "{ 10 }",
                    "nz": "{ 10 }", "elementTypes": "{ C3D8 }"},
  "stats": {"n_cells": 1000, "bounds": [0,100,0,100,0,100]},
  "notes": "..." }
For a generated VTK mesh:
{ "mesh_kind": "vtk", "vtk_path": "<absolute path>",
  "stats": {"n_cells": 50}, "notes": "..." }
Do NOT write prose outside the JSON. Do NOT edit the deck.
```

- [ ] **Step 2: Verify the frontmatter parses**

Run: `uv run python -c "import re,sys; t=open('.claude/agents/geos-mesh.md').read(); fm=re.match(r'^---\n(.*?)\n---\n', t, re.S); print('OK' if fm and 'model: sonnet' in fm.group(1) and 'mcp__agents4geos__suggest_mesh_resolution' in fm.group(1) else 'BROKEN'); sys.exit(0 if fm else 1)"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/geos-mesh.md
git commit -m "feat(routing): geos-mesh compute-and-return subagent (model: sonnet, cw7)"
```

---

### Task 4: Wire Stage C into the orchestrator

Add the concurrent-compute fan-out step to the creation flow, before Stage R.

**Files:**
- Modify: `skills/geos.md`

- [ ] **Step 1: Add the Stage C section**

In `skills/geos.md`, immediately BEFORE the line `## Stage R — Independent Review Gate (creation flow, before save_xml)`, insert:

```markdown
## Stage C — Concurrent compute (mesh + fluids fan-out)

During assembly, when the deck needs a non-trivial mesh and/or fluid model (real
PVT computation, or a generated/resized mesh — not a trivial template tweak),
delegate that compute to subagents running in PARALLEL instead of doing it inline.

1. From Stage 0 you already have the fluid CATEGORY and the user's geometry/fluid
   conditions.
2. Dispatch BOTH subagents in the SAME turn (two Agent-tool calls) so they run
   concurrently:
   - `geos-fluids` with the chosen CATEGORY + conditions + the workspace path.
   - `geos-mesh` with the geometry/resolution + the workspace path.
3. Each returns a JSON result. Validate the required keys (mesh: `mesh_kind` and
   either `internal_mesh` or `vtk_path`; fluids: `model_type` + `constitutive`). If
   a result is missing/invalid or a subagent errored, FALL BACK to computing that
   axis inline yourself — you still have all MCP tools. Partial failure is fine:
   apply the good one, inline the other. A subagent failure NEVER blocks the build.
4. Apply the results to the doc (you, the orchestrator, do ALL mutation — the
   subagents never touch the document):
   - Mesh `internal` → `update_element` the `InternalMesh` attributes; mesh `vtk`
     → `add_element` a `VTKMesh` pointing at `vtk_path`.
   - Fluids → add/update the fluid-phase `Constitutive` model(s) from
     `constitutive`; then wire the solid / porosity / permeability and
     `materialList` yourself.
5. Continue: `validate_cross_references` → `sanity_check` → `preview_xml` → Stage R
   → `save_xml`.

Stage C runs BEFORE Stage R, so the independent reviewer still audits the assembled
deck regardless of how its pieces were computed.
```

- [ ] **Step 2: Route the creation flow through Stage C**

In `skills/geos.md`, find the creation-flow line (added by the reviewer work):

```
   - `validate_cross_references` → `sanity_check` → `preview_xml` → **Stage R
     (Independent Review Gate, see below)** → `save_xml`.
```

Replace it with:

```
   - **Stage C (Concurrent compute fan-out, see below)** →
     `validate_cross_references` → `sanity_check` → `preview_xml` → **Stage R
     (Independent Review Gate, see below)** → `save_xml`.
```

- [ ] **Step 3: Verify the edits are present**

Run: `grep -c "Stage C" skills/geos.md`
Expected: `2` (the section header + the workflow reference).

- [ ] **Step 4: Commit**

```bash
git add skills/geos.md
git commit -m "feat(routing): wire Stage C concurrent mesh+fluids fan-out into orchestrator (cw7)"
```

---

### Task 5: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md` (taxonomy note §1, registry §3, coordination §6)

- [ ] **Step 1: Extend the taxonomy note (§1)**

In `AGENTS.md`, find the line ending `geos-reviewer is the first real subagent.` and replace it with:

```markdown
`geos-reviewer` is the first real subagent (Tier 3). `geos-mesh` and `geos-fluids`
are the first Tier-2 real subagents — compute-and-return advisors the orchestrator
fans out concurrently during a build.
```

- [ ] **Step 2: Add registry entries (§3)**

In `AGENTS.md` §3, immediately after the `geos-reviewer` registry entry (the block ending with its `*Coordination:*` line), add:

```markdown
**`geos-mesh`** (Mesh compute subagent) — Tier 2
- *Description:* Compute a mesh (native `InternalMesh` parameters or a generated VTK
  file) for a domain spec; return structured JSON. Dispatched by `geos` in Stage C;
  NOT user-invocable (the `/geos:mesh` slash command remains for direct use).
- *Type:* Real Claude Code subagent (`.claude/agents/geos-mesh.md`, `model: sonnet`),
  dispatched via the Agent tool.
- *Tools:* mesh compute/inspect MCP tools (`suggest_mesh_resolution`,
  `generate_internal_mesh_xml`, `create_structured_mesh`, `create_rectilinear_mesh`,
  `mesh_statistics`, `define_geometry_box`, `screenshot_mesh`, `load_mesh`) + `Read`.
  No deck-editing tools — compute-and-return only.
- *Inputs:* geometry/domain + resolution; *Outputs:* `MeshResult` JSON
  (`src/agents4geos/dispatch/results.py`).
- *Coordination:* fan-out — `geos` dispatches `geos-mesh` + `geos-fluids` concurrently
  and composes their results.

**`geos-fluids`** (Fluids compute subagent) — Tier 2
- *Description:* Compute the fluid-phase constitutive model(s) + PVT data for a
  chosen catalog category; pick the variant via the category detail file; return
  structured JSON. Dispatched by `geos` in Stage C; NOT user-invocable
  (the `/geos:fluids` slash command remains for direct use).
- *Type:* Real Claude Code subagent (`.claude/agents/geos-fluids.md`,
  `model: sonnet`), dispatched via the Agent tool.
- *Tools:* fluid compute MCP tools (`recommend_fluid_model`, `compute_gas_properties`,
  `compute_oil_properties`, `compute_brine_properties`, `generate_pvt_table`) + `Read`.
  No deck-editing tools — compute-and-return only.
- *Knowledge:* `knowledge/examples/<category>.md` (read for the stage-2 variant
  decision rule + assembly specifics); `fluid_models`.
- *Inputs:* catalog category + conditions; *Outputs:* `FluidResult` JSON
  (`src/agents4geos/dispatch/results.py`).
- *Coordination:* fan-out — see `geos-mesh`.
```

- [ ] **Step 3: Mark the fan-out pattern realized (§6)**

In `AGENTS.md` §6 "Fan-out", replace the line beginning `*Current example:* ` (the `geos:mesh`/`geos:fluids` concurrent line) with:

```markdown
*Current example (2026-06-09, realized):* `geos` dispatches the real subagents
`geos-mesh` and `geos-fluids` concurrently in Stage C (`.claude/agents/*`,
`model: sonnet`) — mesh creation and fluid model selection are independent — then
composes their `MeshResult`/`FluidResult` into the deck.
```

- [ ] **Step 4: Verify and commit**

Run: `grep -c "geos-mesh\|geos-fluids" AGENTS.md`
Expected: `>= 6`

```bash
git add AGENTS.md
git commit -m "docs(agents): register geos-mesh/geos-fluids; mark fan-out realized (cw7)"
```

---

### Task 6: Eval runbook + fixture specs

The fan-out behavior (parallel dispatch, model routing, contract-valid results) is agent-run and cannot be unit-tested. Document a repeatable eval.

**Files:**
- Create: `tests/dispatch/RUNBOOK.md`

- [ ] **Step 1: Write the runbook**

Create `tests/dispatch/RUNBOOK.md`:

```markdown
# geos-mesh / geos-fluids fan-out eval runbook

Agent-run eval — not a pytest. Verifies the two compute subagents return
contract-valid results and that the orchestrator can fan them out concurrently.

## Prerequisite
Run from a session with the `agents4geos` MCP server registered AND the subagents
deployed (`.claude/agents/geos-mesh.md`, `.claude/agents/geos-fluids.md`). Without
the server the subagents cannot reach their MCP tools.

## Fixture specs
- Fluid: category "CO₂-brine", conditions "CO2 + brine at 50 °C, 15 MPa, 100 g/L NaCl".
- Fluid: category "single-phase flow", conditions "water".
- Mesh: "100 m cube, 10×10×10 cells" (expect `mesh_kind: internal`).

## Procedure
1. Dispatch `geos-fluids` with a fixture {category, conditions}. Confirm the returned
   JSON passes `parse_fluid_result` (paste it into
   `python -c "import json,sys; from agents4geos.dispatch.results import parse_fluid_result; parse_fluid_result(json.load(sys.stdin)); print('ok')"`).
2. Dispatch `geos-mesh` with the mesh fixture. Confirm it passes `parse_mesh_result`.
3. Dispatch BOTH in one turn; confirm both complete (parallel fan-out).

## Pass bar
- Each subagent returns a contract-valid JSON for its fixture.
- Both dispatched in one turn both complete.
- (Model = Sonnet is set via frontmatter; Claude Code is trusted to honor `model:` —
  exact model is not directly observable from the result.)

## Results log
Append a dated block each run (per-fixture pass/fail, parallel-dispatch observed).
```

- [ ] **Step 2: Commit**

```bash
git add tests/dispatch/RUNBOOK.md
git commit -m "test(dispatch): fan-out eval runbook + fixture specs (cw7)"
```

---

### Task 7: Live hard-gate + eval baseline (agent-run; deferrable)

Verify the subagents reach their tools and fan out. **Requires the `agents4geos` MCP
server registered + the subagents deployed.** If the current session lacks the
server, record this as PENDING in `RUNBOOK.md` and in `agents4geos-cw7`, and hand it
off — do NOT fabricate results.

**Files:** none (verification + `RUNBOOK.md` results append)

- [ ] **Step 1: Deploy the subagents to the run session**

If running from a workspace dir, copy the subagents where Claude Code reads them:
`cp .claude/agents/geos-fluids.md .claude/agents/geos-mesh.md <workspace>/.claude/agents/`.

- [ ] **Step 2: Run the runbook procedure**

Execute `tests/dispatch/RUNBOOK.md` steps 1–3 against the fixture specs. For each
returned JSON, confirm it passes the matching `parse_*` validator (Task 6 Step 1
command). Confirm a single-turn dual dispatch completes both.

- [ ] **Step 3: Record the baseline**

Append a dated results block to `tests/dispatch/RUNBOOK.md` (per-fixture pass/fail +
whether parallel dispatch was observed). Commit:

```bash
git add tests/dispatch/RUNBOOK.md
git commit -m "test(dispatch): fan-out eval baseline (cw7)"
```

If the gate could not run (no MCP server), instead write a PENDING block and note it
in `agents4geos-cw7`.

---

### Task 8: Full-suite regression + finish

**Files:** none (verification + housekeeping)

- [ ] **Step 1: Full-suite regression**

Run: `uv run pytest tests/ -q`
Expected: all green (the existing 212 + the 12 new `dispatch` tests).

- [ ] **Step 2: Push and open a PR**

```bash
git push -u origin <branch>
gh pr create --title "Per-tier routing fan-out pilot: geos-mesh + geos-fluids subagents" --body "First Tier-2 real subagents (.claude/agents/geos-mesh.md, geos-fluids.md, model: sonnet). The orchestrator fans them out concurrently in Stage C and composes MeshResult/FluidResult (src/agents4geos/dispatch/results.py, TDD) with inline fallback. Gmsh-ready via mesh_kind:vtk. Implements agents4geos-cw7. Live fan-out gate per tests/dispatch/RUNBOOK.md."
```

- [ ] **Step 3: Close the beads issue and push state**

```bash
bd close agents4geos-cw7 --reason="Per-tier routing fan-out pilot (geos-mesh + geos-fluids subagents, model: sonnet) implemented on branch <branch> (PR opened). Contracts TDD-tested; Stage C wired; AGENTS.md updated. Live fan-out gate tracked in RUNBOOK if deferred."
bd dolt push
```

---

## Notes for the executor

- The subagents are **compute-and-return**: no deck-editing tools in their allowlist.
  All `DocumentStore` mutation stays in the orchestrator (Stage C step 4). This is
  what makes the parallel dispatch race-free.
- The `MeshResult.mesh_kind` discriminator is the **Gmsh seam** — a future Gmsh tool
  returns `mesh_kind: "vtk"` with no contract change.
- Dispatch is an optimization over the orchestrator's inline ability; the inline
  fallback (Stage C step 3) must remain so a subagent failure never blocks a build.
- Tests: `uv run pytest`. The bundled schema cache means no GEOS build is needed.
```
