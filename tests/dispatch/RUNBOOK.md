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

### 2026-06-09 — baseline: PENDING (no MCP server in build session)
The implementing session was a headless background job WITHOUT the `agents4geos`
MCP server registered, so the live fan-out gate (Task 7) could not be executed: the
`geos-mesh`/`geos-fluids` subagents cannot reach their `mcp__agents4geos__*` tools
without the server. The deterministic substrate IS verified — the `MeshResult`/
`FluidResult` contracts pass their 12 unit tests (`tests/dispatch/test_results.py`),
and both subagent files' documented JSON was cross-checked against the validators.
The remaining unknown is purely the live behavior: that a dispatched subagent
returns a contract-valid result and that two can be fanned out in one turn.

**To close this baseline:** deploy the subagents into a `/geos`-capable workspace
(`cp .claude/agents/geos-mesh.md .claude/agents/geos-fluids.md <workspace>/.claude/agents/`)
with the MCP server registered, run the Procedure above, and replace this block with
per-fixture caught/missed results. Tracked in `agents4geos-cw7`.
