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

### 2026-06-09 — baseline: PASS (live, MCP-registered workspace session)
Run from `~/codes/agents4geos-workspace` with the `agents4geos` MCP server
registered and the subagents deployed into `.claude/agents/`.

**Parallel fan-out gate — PASS.** `geos-fluids` (category "CO₂-brine", conditions
"CO2 + brine at 50 °C, 15 MPa, 100 g/L NaCl") and `geos-mesh` ("100 m cube,
10×10×10 cells") were dispatched in a SINGLE turn and **both completed
concurrently** (the orchestrator showed "2 agents finished"). This proves the
parallel fan-out the pilot exists to deliver.

**Per-fixture results:**
| fixture | result |
|---------|--------|
| `geos-fluids` CO₂-brine | PASS — contract-valid `FluidResult` (`parse_fluid_result` accepts). Returned `CO2BrineEzrokhiFluid`: it `Read` `examples/co2_brine.md` and applied the stage-2 decision rule to pick **Ezrokhi over Phillips** from the high salinity (≈9.1 wt%). Boundary respected — only the fluid model in `constitutive`; recommended coupled solid named in `notes`. Computed via `compute_gas_properties`/`compute_brine_properties`/`generate_pvt_table`/`recommend_fluid_model`. |
| `geos-mesh` 100 m cube | PASS — contract-valid `MeshResult` (`parse_mesh_result` accepts). `mesh_kind: internal`, all 7 `internal_mesh` keys present, 1000 cells, bounds correct. |

**Model routing:** both subagents pin `model: sonnet` in frontmatter and ran with
no override → Sonnet. (The Agent tool result does not echo the model — confirmed via
the frontmatter, same as `geos-reviewer`'s `model: opus`.)

**Optional remaining coverage:** the `geos-fluids` "single-phase flow" / "water"
fixture (expected: a `CompressibleSinglePhaseFluid`-family `FluidResult`) — not
required for the gate, which is already PASS.

---

# geos-postprocess live gate (tnt)

Agent-run eval — not a pytest. Verifies the `geos-postprocess` subagent returns a
contract-valid `PostprocessResult` when dispatched against a real GEOS VTK output.

## Prerequisite
Run from a session with the `agents4geos` MCP server registered AND the subagent
deployed (`.claude/agents/geos-postprocess.md`). Without the server the subagent
cannot reach its MCP tools.

## Goal
Dispatch `geos-postprocess` against a real GEOS VTK output in an MCP-registered
`/geos` session and confirm a contract-valid `PostprocessResult`.

## Fixture specs
- A completed GEOS deck run via `/geos:run` that produced at least one `.vtu`
  output file (final timestep).

## Procedure
1. Run a small deck through `/geos:run`; locate the final-timestep `.vtu`.
2. From the orchestrator, dispatch `geos-postprocess` with the absolute VTK path.
3. Parse its JSON with `parse_postprocess_result` — must succeed.
4. Assert each figure's `colormap` is a `cmc.*` map (NOT jet/rainbow/coolwarm) and
   its `title` ends in a bracketed SI unit; assert each figure `path` exists.

## Pass bar
- `parse_postprocess_result` accepts the returned JSON without error.
- Every figure entry has a `colormap` matching `cmc.*`, a `title` ending in `[<unit>]`,
  and a `path` that exists on disk.

## Results log
Append a dated block each run (per-fixture pass/fail).

### Status: PENDING — not yet run live (tnt)
Record PASS once run live with the MCP server registered (headless build sessions
lack it; cw7 RUNBOOK pattern).
