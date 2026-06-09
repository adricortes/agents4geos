# Per-Tier Model Routing — Fan-out Pilot (geos-mesh + geos-fluids)

**Issue:** `agents4geos-cw7` (part of epic `agents4geos-gy9`). Builds on `w9k`,
which proved the first real subagent (`geos-reviewer`, Tier 3).

## Goal

Make the `AGENTS.md` Tier-1/2/3 → Haiku/Sonnet/Opus routing *real* for two Tier-2
agents by converting `geos:mesh` and `geos:fluids` from inline prompt-overlay
skills into **real dispatched subagents** (`model: sonnet`) that the orchestrator
**fans out concurrently** during a build. This is a pilot — the canonical
`AGENTS.md` fan-out example — establishing the conversion recipe for the rest of
the Tier-1/2 agents in later work.

### Drivers (chosen with the user)
1. **Cost routing** — run mesh/fluid compute on Sonnet instead of the
   orchestrator's Opus.
2. **Autonomy / parallelism** — the orchestrator fans out independent work
   concurrently and composes the results.

Context-hygiene and architectural-consistency are welcome side effects but were not
the primary drivers, so the design optimizes for cost + parallel-safety.

## Background (current state, verified 2026-06-09)

- `geos:mesh` and `geos:fluids` exist as standalone slash-command skills
  (`skills/geos:mesh.md`, `skills/geos:fluids.md`) — prompt overlays loaded into the
  main conversation, same context/model as the orchestrator.
- The orchestrator (`skills/geos.md`) does **not** dispatch them; it performs
  mesh/fluid work inline with MCP tools.
- The underlying tools are **stateless compute**: `fluid_tools` (PVT, model
  recommendation) and `mesh_tools` (pyvista VTK generation, `InternalMesh` XML
  snippet, stats). None mutate the shared in-memory `DocumentStore`.
- Only `geos-reviewer` (Tier 3, `.claude/agents/geos-reviewer.md`, `model: opus`)
  is currently a real dispatched subagent.

## Architecture

`geos-mesh` and `geos-fluids` become **compute-and-return advisors**: real Claude
Code subagents (`model: sonnet`) dispatched via the Agent tool. Each reads a spec,
runs its stateless tools, and returns a **structured result**. They never touch the
`DocumentStore`. The orchestrator (Opus) validates each result and serially applies
it to the doc.

Why compute-and-return (not direct doc mutation): two subagents mutating one
`DocumentStore` concurrently would race. Keeping all mutation in the orchestrator
serializes writes while the *expensive compute* runs in parallel — delivering the
parallelism driver safely. (Rejected alternative: subagents call
`update_element` on the shared doc — kills safe parallelism.)

Dispatch is an **optimization layered over** the orchestrator's existing inline
ability. If a subagent errors or returns an invalid result, the orchestrator falls
back to computing that axis inline (it still has all MCP tools). The build is never
blocked by a subagent failure.

## Components

### 1. `.claude/agents/geos-fluids.md` (real subagent, `model: sonnet`, Tier 2)
- **Frontmatter `tools:`** — read/compute only, no doc-editing tools:
  `Read`, `mcp__agents4geos__recommend_fluid_model`,
  `mcp__agents4geos__compute_gas_properties`,
  `mcp__agents4geos__compute_oil_properties`,
  `mcp__agents4geos__compute_brine_properties`,
  `mcp__agents4geos__generate_pvt_table`.
- **Input:** a fluid spec — type/components, temperature, pressure, salinity (e.g.
  "CO2 + brine at 50 °C, 15 MPa, 100 g/L NaCl"; or "single-phase water").
- **Output:** a `FluidResult` JSON object (contract below). No prose.
- **Boundary:** `FluidResult` covers the **fluid-phase constitutive model(s)** and
  any PVT tables — the part `geos:fluids` is responsible for. The non-fluid solid
  side (coupled solid / porosity / permeability), relative-permeability (handled by
  `geos:relperm`), and `materialList` wiring stay with the orchestrator. The
  subagent *may* name the recommended coupled-solid model in `notes`, but does not
  emit it as `constitutive`.

### 2. `.claude/agents/geos-mesh.md` (real subagent, `model: sonnet`, Tier 2)
- **Frontmatter `tools:`** — compute/inspect only, no doc-editing tools:
  `Read`, `mcp__agents4geos__suggest_mesh_resolution`,
  `mcp__agents4geos__generate_internal_mesh_xml`,
  `mcp__agents4geos__create_structured_mesh`,
  `mcp__agents4geos__create_rectilinear_mesh`,
  `mcp__agents4geos__mesh_statistics`,
  `mcp__agents4geos__define_geometry_box`,
  `mcp__agents4geos__screenshot_mesh`, `mcp__agents4geos__load_mesh`.
- **Input:** a geometry/domain spec — extents, target resolution, structured vs.
  generated VTK.
- **Output:** a `MeshResult` JSON object (contract below). No prose.

### 3. Result contracts — `src/agents4geos/dispatch/results.py`

The deterministic, fully unit-tested core (mirrors `src/agents4geos/review/findings.py`).
Package name `dispatch` is provisional; it holds "results from dispatched
subagents". Defines two frozen dataclasses + validating parsers:

```
FluidResult:
  model_type: str                         # e.g. "CompressibleSinglePhaseFluid", "CO2BrinePhillips"
  constitutive: list[ConstitutiveSpec]    # each: {element_type, name, attributes: dict}
  pvt_table_paths: list[str] = []         # optional, for table-based models
  notes: str = ""                         # human-readable rationale

MeshResult:
  mesh_kind: "internal" | "vtk"           # discriminator
  internal_mesh: dict | None              # present when kind == "internal":
                                          #   {xCoords,yCoords,zCoords,nx,ny,nz,elementTypes}
  vtk_path: str | None                    # present when kind == "vtk"
  stats: dict = {}                        # {n_cells, bounds, ...}
  notes: str = ""

parse_fluid_result(d: dict) -> FluidResult   # raises ValueError on missing keys / bad constitutive
parse_mesh_result(d: dict) -> MeshResult     # raises ValueError on missing keys, or on
                                             #   kind=="internal" without internal_mesh /
                                             #   kind=="vtk" without vtk_path / unknown kind
```

`MeshResult.mesh_kind` is the **Gmsh-ready seam**: a future Gmsh tool returns
`mesh_kind:"vtk"` with its generated path; no contract change required.

Required-key sets (validation):
- `FluidResult`: `model_type`, `constitutive` (list; each item needs
  `element_type`, `name`, `attributes`).
- `MeshResult`: `mesh_kind`; then `internal_mesh` (dict with the 7 mesh keys) when
  `internal`, or `vtk_path` when `vtk`. Unknown `mesh_kind` → `ValueError`.

## Data flow / orchestrator wiring (`skills/geos.md`)

Add **Stage C — Concurrent compute (mesh + fluids)** to the creation flow, after
intent parsing / catalog routing and before validation:

1. **Decide.** If the deck needs a non-trivial mesh and/or fluid model — real PVT
   computation or a generated/resized mesh, not a trivial template tweak — enter
   Stage C. Otherwise stay inline (the C-tuning: don't fan out for nothing).
2. **Fan out.** Dispatch `geos-mesh` and `geos-fluids` **in the same turn** (two
   Agent-tool calls) so they run concurrently. Pass each its spec, verbatim from
   the user's intent.
3. **Validate.** Parse each returned JSON via `parse_mesh_result` /
   `parse_fluid_result`. On parse failure or subagent error for an axis, **fall
   back to inline** computation for that axis (partial failure is fine — apply the
   good one, inline the other).
4. **Apply (serial, orchestrator only).** Mesh: set `InternalMesh` attributes from
   `internal_mesh`, or add a `VTKMesh` element pointing at `vtk_path`. Fluids: add
   or update the `Constitutive` models from `constitutive`.
5. **Continue.** `validate_cross_references` → `sanity_check` → `preview_xml` →
   **Stage R** (independent reviewer) → `save_xml`.

Stage C precedes Stage R, so the reviewer still independently audits the assembled
deck regardless of how its pieces were computed.

## Error handling

Subagent dispatch never blocks the build:
- Invalid/unparseable result or subagent error → orchestrator computes that axis
  inline.
- One-of-two fails → apply the successful result, inline the other.
- Contract validation (`parse_*`) is the guard that triggers fallback.

## Testing

- **TDD unit core** — `tests/dispatch/test_results.py`: parse/validate both result
  types, `mesh_kind` discrimination, missing-key and bad-kind rejection. Pure
  Python, deterministic (like `tests/review/test_findings.py`). Written first.
- **Hard gate (live, mirrors w9k Task 1)** — in a session with the `agents4geos`
  MCP server registered and the subagents deployed:
  1. Dispatch `geos-fluids` on a sample spec → returns a JSON that
     `parse_fluid_result` accepts.
  2. Dispatch `geos-mesh` on a sample spec → returns a JSON that
     `parse_mesh_result` accepts.
  3. Dispatch **both in one turn** → both complete (parallel fan-out works).
  If a subagent cannot reach its MCP tools, stop and record it (same gate
  discipline as the reviewer).
- **Runbook** — `tests/dispatch/RUNBOOK.md`: the fan-out eval procedure, a couple
  of fixture specs (e.g. "CO2 + brine, 50 °C, 15 MPa" fluid; "100 m cube, 10×10×10
  cells" mesh), expected result shapes, and a dated baseline recorded live.
  Model = Sonnet is set via frontmatter; we trust Claude Code honors `model:`
  (note in the runbook that exact model is not directly observable).

## AGENTS.md updates

- §3 registry: add `geos-mesh` and `geos-fluids` as **real subagents** (Tier 2,
  `model: sonnet`, dispatched, compute-and-return), tools as above, outputs =
  `MeshResult`/`FluidResult` JSON. Note they coexist with the standalone
  `skills/geos:mesh.md` / `skills/geos:fluids.md` overlays (kept for direct
  `/geos:mesh` use).
- §6 coordination: mark the **fan-out** pattern *realized* — the current
  "anticipated/Current example" line (`geos` dispatching `geos:mesh` and
  `geos:fluids` concurrently) becomes a realized example pointing at the
  `.claude/agents/*` subagents and Stage C.
- §1 taxonomy note: `geos-mesh`/`geos-fluids` are the first Tier-2 real subagents
  (after `geos-reviewer` at Tier 3).

## Out of scope (filed separately)

- **Gmsh unstructured meshing** — new dependency (`gmsh`/`meshio`) + geometry →
  `.msh` → VTK → GEOS `VTKMesh` tooling, with region/surface mapping. Its own
  ticket; this design leaves `MeshResult.mesh_kind: "vtk"` ready for it.
- Converting the remaining Tier-1/2 agents (`geos:schema`, `geos:inspect`,
  `geos:relperm`, `geos:validate`, `geos:postprocess`) — follow-ups once this pilot
  establishes the recipe.
- Removing the inline path from the orchestrator — kept deliberately as the
  fallback.

## References

- Reviewer precedent: `docs/superpowers/specs/2026-06-09-independent-reviewer-subagent-design.md`,
  `.claude/agents/geos-reviewer.md`, `src/agents4geos/review/findings.py`.
- Tier taxonomy & fan-out pattern: `AGENTS.md` §2, §6.
