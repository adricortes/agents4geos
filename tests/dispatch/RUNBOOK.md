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
